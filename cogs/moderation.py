import asyncio
import re
import sqlite3
from datetime import timedelta
from threading import Lock
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from config import (
    COLOR_WARNING,
    DATABASE_FOLDER,
    MODERATION_DATABASE_FILE,
    MODERATION_MAX_PURGE_MESSAGES,
    MODERATION_MAX_TIMEOUT_DAYS,
    MODERATION_MAX_WARNING_RESULTS,
)

_database_lock = Lock()


def initialize_database():
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

    with _database_lock:
        with sqlite3.connect(
            MODERATION_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.commit()


def add_warning(
    guild_id,
    user_id,
    moderator_id,
    reason
):
    with _database_lock:
        with sqlite3.connect(
            MODERATION_DATABASE_FILE,
            timeout=10
        ) as connection:
            cursor = connection.execute(
                """
                INSERT INTO warnings (
                    guild_id,
                    user_id,
                    moderator_id,
                    reason
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    guild_id,
                    user_id,
                    moderator_id,
                    reason
                )
            )

            connection.commit()

            return cursor.lastrowid


def get_warnings(guild_id, user_id):
    with _database_lock:
        with sqlite3.connect(
            MODERATION_DATABASE_FILE,
            timeout=10
        ) as connection:
            return connection.execute(
                """
                SELECT
                    id,
                    moderator_id,
                    reason,
                    created_at
                FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    guild_id,
                    user_id,
                    MODERATION_MAX_WARNING_RESULTS
                )
            ).fetchall()


def clear_user_warnings(guild_id, user_id):
    with _database_lock:
        with sqlite3.connect(
            MODERATION_DATABASE_FILE,
            timeout=10
        ) as connection:
            cursor = connection.execute(
                """
                DELETE FROM warnings
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id)
            )

            connection.commit()

            return cursor.rowcount


def parse_duration(value):
    match = re.fullmatch(
        r"(\d+)([smhd])",
        value.strip().lower()
    )

    if match is None:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if amount <= 0:
        return None

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    total_seconds = amount * multipliers[unit]

    if total_seconds < 10:
        return None

    if (
        total_seconds
        > MODERATION_MAX_TIMEOUT_DAYS * 86400
    ):
        return None

    return timedelta(seconds=total_seconds)


def clean_reason(reason):
    if reason is None:
        return "No reason provided."

    reason = reason.strip()

    if not reason:
        return "No reason provided."

    return reason[:500]


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        initialize_database()

    def target_error(
        self,
        interaction,
        target
    ):
        guild = interaction.guild
        moderator = interaction.user

        if guild is None:
            return "This command only works inside a server."

        if not isinstance(moderator, discord.Member):
            return "Could not verify your server permissions."

        if target.id == moderator.id:
            return "You cannot moderate yourself."

        if self.bot.user and target.id == self.bot.user.id:
            return "You cannot use that command on Judy."

        if target.id == guild.owner_id:
            return "The server owner cannot be moderated."

        if (
            moderator.id != guild.owner_id
            and moderator.top_role <= target.top_role
        ):
            return (
                "That member has an equal or higher role "
                "than you."
            )

        bot_member = guild.me

        if bot_member is None:
            return "Could not verify Judy's server role."

        if bot_member.top_role <= target.top_role:
            return (
                "Judy's role must be above that member's "
                "highest role."
            )

        return None

    @app_commands.command(
        name="warn",
        description="Record a warning against a server member."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        moderate_members=True
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    @app_commands.describe(
        user="The member to warn",
        reason="Why the member is being warned"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        error = self.target_error(
            interaction,
            user
        )

        if error:
            await interaction.response.send_message(
                error,
                ephemeral=True
            )
            return

        reason = clean_reason(reason)

        warning_id = await asyncio.to_thread(
            add_warning,
            interaction.guild.id,
            user.id,
            interaction.user.id,
            reason
        )

        embed = discord.Embed(
            title="Member Warned",
            color=COLOR_WARNING
        )

        embed.add_field(
            name="Member",
            value=user.mention,
            inline=True
        )

        embed.add_field(
            name="Moderator",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Warning ID",
            value=str(warning_id),
            inline=True
        )

        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="warnings",
        description="View a member's recorded warnings."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        moderate_members=True
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    @app_commands.describe(
        user="The member whose warnings you want to view"
    )
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        records = await asyncio.to_thread(
            get_warnings,
            interaction.guild.id,
            user.id
        )

        if not records:
            await interaction.response.send_message(
                f"{user.mention} has no recorded warnings.",
                ephemeral=True
            )
            return

        lines = []

        for (
            warning_id,
            moderator_id,
            reason,
            created_at
        ) in records:
            lines.append(
                f"**#{warning_id}** — {reason}\n"
                f"Moderator: <@{moderator_id}> • "
                f"{created_at}"
            )

        description = "\n\n".join(lines)

        if len(description) > 3900:
            description = description[:3897] + "..."

        embed = discord.Embed(
            title=f"Warnings for {user.display_name}",
            description=description,
            color=COLOR_WARNING
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="clear_warnings",
        description="Delete all warnings recorded for a member."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        moderate_members=True
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    @app_commands.describe(
        user="The member whose warnings should be cleared"
    )
    async def clear_warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        removed = await asyncio.to_thread(
            clear_user_warnings,
            interaction.guild.id,
            user.id
        )

        await interaction.response.send_message(
            f"Removed **{removed}** warning(s) "
            f"from {user.mention}.",
            ephemeral=True
        )

    @app_commands.command(
        name="timeout",
        description="Temporarily prevent a member from interacting."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        moderate_members=True
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    @app_commands.describe(
        user="The member to timeout",
        duration="Duration such as 10m, 2h or 1d",
        reason="Why the member is being timed out"
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: Optional[str] = None
    ):
        error = self.target_error(
            interaction,
            user
        )

        if error:
            await interaction.response.send_message(
                error,
                ephemeral=True
            )
            return

        parsed_duration = parse_duration(
            duration
        )

        if parsed_duration is None:
            await interaction.response.send_message(
                "Invalid duration. Use formats such as "
                "`10m`, `2h` or `1d`. Maximum: "
                f"{MODERATION_MAX_TIMEOUT_DAYS} days.",
                ephemeral=True
            )
            return

        reason = clean_reason(reason)

        audit_reason = (
            f"{reason} | Moderator: "
            f"{interaction.user}"
        )

        try:
            timeout_until = (
                discord.utils.utcnow()
                + parsed_duration
            )

            await user.timeout(
                timeout_until,
                reason=audit_reason
            )

            embed = discord.Embed(
                title="Member Timed Out",
                color=COLOR_WARNING
            )

            embed.add_field(
                name="Member",
                value=user.mention,
                inline=True
            )

            embed.add_field(
                name="Duration",
                value=duration,
                inline=True
            )

            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )

            await interaction.response.send_message(
                embed=embed
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Judy does not have permission to timeout "
                "that member.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"Discord rejected the timeout: {error}",
                ephemeral=True
            )

    @app_commands.command(
        name="untimeout",
        description="Remove a member's active timeout."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        moderate_members=True
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    @app_commands.describe(
        user="The member whose timeout should be removed"
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        error = self.target_error(
            interaction,
            user
        )

        if error:
            await interaction.response.send_message(
                error,
                ephemeral=True
            )
            return

        try:
            await user.timeout(
                None,
                reason=(
                    "Timeout removed by "
                    f"{interaction.user}"
                )
            )

            await interaction.response.send_message(
                f"Removed the timeout from {user.mention}."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Judy does not have permission to remove "
                "that timeout.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"Discord rejected the request: {error}",
                ephemeral=True
            )

    @app_commands.command(
        name="kick",
        description="Remove a member from the server."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        kick_members=True
    )
    @app_commands.checks.has_permissions(
        kick_members=True
    )
    @app_commands.describe(
        user="The member to kick",
        reason="Why the member is being kicked"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        error = self.target_error(
            interaction,
            user
        )

        if error:
            await interaction.response.send_message(
                error,
                ephemeral=True
            )
            return

        reason = clean_reason(reason)

        try:
            await user.kick(
                reason=(
                    f"{reason} | Moderator: "
                    f"{interaction.user}"
                )
            )

            await interaction.response.send_message(
                f"Kicked **{user}**.\nReason: {reason}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Judy does not have permission to kick "
                "that member.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"Discord rejected the kick: {error}",
                ephemeral=True
            )

    @app_commands.command(
        name="ban",
        description="Ban a member from the server."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        ban_members=True
    )
    @app_commands.checks.has_permissions(
        ban_members=True
    )
    @app_commands.describe(
        user="The member to ban",
        reason="Why the member is being banned",
        delete_message_days=(
            "How many days of messages to delete, from 0 to 7"
        )
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None,
        delete_message_days: app_commands.Range[
            int,
            0,
            7
        ] = 0
    ):
        error = self.target_error(
            interaction,
            user
        )

        if error:
            await interaction.response.send_message(
                error,
                ephemeral=True
            )
            return

        reason = clean_reason(reason)

        try:
            await user.ban(
                reason=(
                    f"{reason} | Moderator: "
                    f"{interaction.user}"
                ),
                delete_message_seconds=(
                    delete_message_days * 86400
                )
            )

            await interaction.response.send_message(
                f"Banned **{user}**.\nReason: {reason}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Judy does not have permission to ban "
                "that member.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"Discord rejected the ban: {error}",
                ephemeral=True
            )

    @app_commands.command(
        name="unban",
        description="Remove a ban using the user's Discord ID."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        ban_members=True
    )
    @app_commands.checks.has_permissions(
        ban_members=True
    )
    @app_commands.describe(
        user_id="The banned user's Discord ID",
        reason="Why the ban is being removed"
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: Optional[str] = None
    ):
        try:
            resolved_user_id = int(
                user_id.strip()
            )

        except ValueError:
            await interaction.response.send_message(
                "That is not a valid Discord user ID.",
                ephemeral=True
            )
            return

        reason = clean_reason(reason)

        try:
            user_object = discord.Object(
                id=resolved_user_id
            )

            await interaction.guild.unban(
                user_object,
                reason=(
                    f"{reason} | Moderator: "
                    f"{interaction.user}"
                )
            )

            await interaction.response.send_message(
                f"Unbanned user `{resolved_user_id}`."
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "That user is not currently banned.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Judy does not have permission to remove "
                "that ban.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"Discord rejected the unban: {error}",
                ephemeral=True
            )

    @app_commands.command(
        name="purge",
        description="Delete multiple recent messages."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_messages=True
    )
    @app_commands.checks.has_permissions(
        manage_messages=True
    )
    @app_commands.describe(
        amount="Number of messages to delete"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[
            int,
            1,
            MODERATION_MAX_PURGE_MESSAGES
        ]
    ):
        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "This command only works in text channels.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            deleted = await channel.purge(
                limit=amount
            )

            await interaction.followup.send(
                f"Deleted **{len(deleted)}** message(s).",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "Judy needs the Manage Messages permission.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            await interaction.followup.send(
                f"Discord rejected the purge: {error}",
                ephemeral=True
            )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(
            error,
            app_commands.MissingPermissions
        ):
            message = (
                "You do not have permission to use "
                "that moderation command."
            )

        else:
            print(
                f"[MODERATION COMMAND ERROR] {error}"
            )

            message = (
                "The moderation command hit an "
                "unexpected error."
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
