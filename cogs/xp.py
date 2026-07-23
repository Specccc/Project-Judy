import asyncio
import random
import sqlite3
import time
from threading import Lock
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from config import (
    COLOR_JUDY,
    COMMAND_PREFIX,
    DATABASE_FOLDER,
    XP_BASE_REQUIREMENT,
    XP_COOLDOWN_SECONDS,
    XP_DATABASE_FILE,
    XP_MAXIMUM_AWARD,
    XP_MINIMUM_AWARD,
)


_database_lock = Lock()


def initialize_xp_database():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    with _database_lock:
        with sqlite3.connect(
            XP_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS xp_users (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    xp INTEGER NOT NULL DEFAULT 0,
                    messages INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )

            connection.commit()


def calculate_level(xp):
    return int(
        (xp / XP_BASE_REQUIREMENT) ** 0.5
    )


def level_start_xp(level):
    return (
        level
        * level
        * XP_BASE_REQUIREMENT
    )


def next_level_xp(level):
    return (
        (level + 1)
        * (level + 1)
        * XP_BASE_REQUIREMENT
    )


def add_user_xp(
    guild_id,
    user_id,
    amount
):
    with _database_lock:
        with sqlite3.connect(
            XP_DATABASE_FILE,
            timeout=10
        ) as connection:
            existing = connection.execute(
                """
                SELECT xp, messages
                FROM xp_users
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            ).fetchone()

            old_xp = (
                existing[0]
                if existing
                else 0
            )

            connection.execute(
                """
                INSERT INTO xp_users (
                    guild_id,
                    user_id,
                    xp,
                    messages
                )
                VALUES (?, ?, ?, 1)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET
                    xp = xp + excluded.xp,
                    messages = messages + 1
                """,
                (
                    guild_id,
                    user_id,
                    amount
                )
            )

            connection.commit()

            updated = connection.execute(
                """
                SELECT xp, messages
                FROM xp_users
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            ).fetchone()

            return (
                old_xp,
                updated[0],
                updated[1]
            )


def get_user_rank(
    guild_id,
    user_id
):
    with _database_lock:
        with sqlite3.connect(
            XP_DATABASE_FILE,
            timeout=10
        ) as connection:
            row = connection.execute(
                """
                SELECT xp, messages
                FROM xp_users
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            ).fetchone()

            if not row:
                return 0, 0, 0

            rank_row = connection.execute(
                """
                SELECT COUNT(*) + 1
                FROM xp_users
                WHERE guild_id = ?
                AND xp > ?
                """,
                (
                    guild_id,
                    row[0]
                )
            ).fetchone()

            return (
                row[0],
                row[1],
                rank_row[0]
            )


def get_leaderboard(
    guild_id,
    limit=10
):
    with _database_lock:
        with sqlite3.connect(
            XP_DATABASE_FILE,
            timeout=10
        ) as connection:
            return connection.execute(
                """
                SELECT
                    user_id,
                    xp,
                    messages
                FROM xp_users
                WHERE guild_id = ?
                ORDER BY xp DESC
                LIMIT ?
                """,
                (
                    guild_id,
                    limit
                )
            ).fetchall()


def create_progress_bar(
    progress,
    required,
    length=10
):
    if required <= 0:
        filled = length

    else:
        ratio = min(
            max(
                progress / required,
                0
            ),
            1
        )

        filled = round(
            ratio * length
        )

    return (
        "▰" * filled
        + "▱" * (length - filled)
    )


class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

        initialize_xp_database()

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):
        if message.author.bot:
            return

        if message.guild is None:
            return

        content = message.content.strip()

        if len(content) < 3:
            return

        if content.startswith(
            COMMAND_PREFIX
        ):
            return

        cooldown_key = (
            message.guild.id,
            message.author.id
        )

        current_time = time.monotonic()

        last_award = self.cooldowns.get(
            cooldown_key,
            0
        )

        if (
            current_time - last_award
            < XP_COOLDOWN_SECONDS
        ):
            return

        self.cooldowns[cooldown_key] = (
            current_time
        )

        amount = random.randint(
            XP_MINIMUM_AWARD,
            XP_MAXIMUM_AWARD
        )

        old_xp, new_xp, _ = (
            await asyncio.to_thread(
                add_user_xp,
                message.guild.id,
                message.author.id,
                amount
            )
        )

        old_level = calculate_level(
            old_xp
        )

        new_level = calculate_level(
            new_xp
        )

        if new_level > old_level:
            try:
                await message.channel.send(
                    f"{message.author.mention}, "
                    f"you reached level "
                    f"**{new_level}**. "
                    f"Not bad, choom.",
                    allowed_mentions=(
                        discord.AllowedMentions(
                            users=True
                        )
                    )
                )

            except discord.HTTPException:
                pass

    @app_commands.command(
        name="rank",
        description="Show your XP level and server rank."
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="The member whose rank you want to view"
    )
    async def rank(
        self,
        interaction: discord.Interaction,
        user: Optional[
            discord.Member
        ] = None
    ):
        target = (
            user
            or interaction.user
        )

        xp, messages, position = (
            await asyncio.to_thread(
                get_user_rank,
                interaction.guild.id,
                target.id
            )
        )

        level = calculate_level(
            xp
        )

        starting_xp = level_start_xp(
            level
        )

        required_xp = next_level_xp(
            level
        )

        progress = xp - starting_xp

        progress_needed = (
            required_xp - starting_xp
        )

        progress_bar = create_progress_bar(
            progress,
            progress_needed
        )

        embed = discord.Embed(
            title=(
                f"{target.display_name}'s Rank"
            ),
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Level",
            value=str(level),
            inline=True
        )

        embed.add_field(
            name="Server Rank",
            value=(
                f"#{position}"
                if position
                else "Unranked"
            ),
            inline=True
        )

        embed.add_field(
            name="Total XP",
            value=str(xp),
            inline=True
        )

        embed.add_field(
            name="Next Level",
            value=(
                f"{progress_bar}\n"
                f"{progress} / "
                f"{progress_needed} XP"
            ),
            inline=False
        )

        embed.add_field(
            name="XP-earning Messages",
            value=str(messages),
            inline=False
        )

        embed.set_thumbnail(
            url=target.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="leaderboard",
        description="Show the server XP leaderboard."
    )
    @app_commands.guild_only()
    async def leaderboard(
        self,
        interaction: discord.Interaction
    ):
        results = await asyncio.to_thread(
            get_leaderboard,
            interaction.guild.id,
            10
        )

        if not results:
            await interaction.response.send_message(
                "Nobody has earned XP yet."
            )
            return

        lines = []

        for position, (
            user_id,
            xp,
            messages
        ) in enumerate(
            results,
            start=1
        ):
            member = (
                interaction.guild.get_member(
                    user_id
                )
            )

            if member:
                name = member.display_name
            else:
                name = f"User {user_id}"

            level = calculate_level(
                xp
            )

            lines.append(
                f"**{position}.** "
                f"{name} — "
                f"Level {level} "
                f"({xp} XP)"
            )

        embed = discord.Embed(
            title="Server XP Leaderboard",
            description="\n".join(lines),
            color=COLOR_JUDY
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(XP(bot))
