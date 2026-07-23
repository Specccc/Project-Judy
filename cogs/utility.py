import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from cogs.ambient import save_enabled_state
from cogs.chat import save_chat_channel
from config import (
    BOT_NAME,
    BOT_VERSION,
    COLOR_JUDY,
    PRIVACY_POLICY_URL,
    PROJECT_REPOSITORY_URL,
    SUPPORT_URL,
    TERMS_OF_SERVICE_URL,
)
from guild_service import (
    get_guild_settings,
    initialize_guild_database,
    mark_setup_complete,
    register_guild,
)
from data_service import delete_guild_data
from memory.memory_manager import (
    migrate_legacy_user_memories,
)


BOT_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    add_reactions=True,
    embed_links=True,
    attach_files=True,
    manage_messages=True,
    moderate_members=True,
    kick_members=True,
    ban_members=True,
)


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ready_initialized = False
        initialize_guild_database()

    @commands.Cog.listener()
    async def on_ready(self):
        if self.ready_initialized:
            return

        await asyncio.to_thread(
            migrate_legacy_user_memories,
            [
                guild.id
                for guild in self.bot.guilds
            ]
        )

        for guild in self.bot.guilds:
            await asyncio.to_thread(
                register_guild,
                guild.id
            )

        self.ready_initialized = True

    @commands.Cog.listener()
    async def on_guild_join(
        self,
        guild: discord.Guild
    ):
        await asyncio.to_thread(
            register_guild,
            guild.id
        )

    @commands.Cog.listener()
    async def on_guild_remove(
        self,
        guild: discord.Guild
    ):
        await asyncio.to_thread(
            delete_guild_data,
            guild.id,
            [
                channel.id
                for channel in guild.channels
            ]
        )

    @app_commands.command(
        name="setup",
        description="Configure Judy's main server features."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.describe(
        chat_channel=(
            "Channel where Judy should answer direct messages"
        ),
        ambient_presence=(
            "Allow occasional passive reactions and replies"
        )
    )
    async def setup_server(
        self,
        interaction: discord.Interaction,
        chat_channel: Optional[
            discord.TextChannel
        ] = None,
        ambient_presence: bool = False
    ):
        channel = (
            chat_channel
            or interaction.channel
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "Choose a standard server text channel.",
                ephemeral=True
            )
            return

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "Discord did not provide Judy's server member.",
                ephemeral=True
            )
            return

        permissions = channel.permissions_for(
            bot_member
        )

        required_permissions = {
            "View Channel": permissions.view_channel,
            "Send Messages": permissions.send_messages,
            "Read Message History": (
                permissions.read_message_history
            ),
            "Add Reactions": permissions.add_reactions,
            "Embed Links": permissions.embed_links,
        }

        missing = [
            name
            for name, allowed
            in required_permissions.items()
            if not allowed
        ]

        if missing:
            await interaction.response.send_message(
                "Judy is missing these permissions in "
                f"{channel.mention}: "
                + ", ".join(missing),
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        guild_id = interaction.guild.id

        await asyncio.gather(
            asyncio.to_thread(
                save_chat_channel,
                guild_id,
                channel.id
            ),
            asyncio.to_thread(
                save_enabled_state,
                guild_id,
                ambient_presence
            ),
            asyncio.to_thread(
                mark_setup_complete,
                guild_id,
                interaction.user.id,
                channel.id
            ),
        )

        chat_cog = self.bot.get_cog(
            "Chat"
        )

        if chat_cog is not None:
            chat_cog.chat_channels[
                guild_id
            ] = channel.id

        ambient_cog = self.bot.get_cog(
            "Ambient"
        )

        if ambient_cog is not None:
            if ambient_presence:
                ambient_cog.enabled_guilds.add(
                    guild_id
                )
            else:
                ambient_cog.enabled_guilds.discard(
                    guild_id
                )

        embed = discord.Embed(
            title=f"{BOT_NAME} Setup Complete",
            description=(
                "Core server configuration was saved."
            ),
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Chat Channel",
            value=channel.mention,
            inline=False
        )

        embed.add_field(
            name="Ambient Presence",
            value=(
                "Enabled"
                if ambient_presence
                else "Disabled"
            ),
            inline=False
        )

        embed.add_field(
            name="Next Check",
            value=(
                "Run `/health`, then address Judy in "
                f"{channel.mention}."
            ),
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="setup_status",
        description="Show this server's Judy setup status."
    )
    @app_commands.guild_only()
    async def setup_status(
        self,
        interaction: discord.Interaction
    ):
        settings = await asyncio.to_thread(
            get_guild_settings,
            interaction.guild.id
        )

        channel_id = settings[
            "setup_channel_id"
        ]

        channel = (
            interaction.guild.get_channel(
                channel_id
            )
            if channel_id
            else None
        )

        embed = discord.Embed(
            title=f"{BOT_NAME} Setup Status",
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Configured",
            value=(
                "Yes"
                if settings["setup_complete"]
                else "No"
            ),
            inline=True
        )

        embed.add_field(
            name="Chat Channel",
            value=(
                channel.mention
                if channel
                else "Not configured"
            ),
            inline=True
        )

        embed.add_field(
            name="Version",
            value=BOT_VERSION,
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="help",
        description="Show Project Judy's command guide."
    )
    async def help_command(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title=f"{BOT_NAME} Command Guide",
            description=(
                f"Version {BOT_VERSION}. Commands only "
                "appear when you have the required permissions."
            ),
            color=COLOR_JUDY
        )

        groups = {
            "Setup & Chat": (
                "`/setup` `/setup_status` `/chatmode_on` "
                "`/chatmode_off` `/conversation_clear`"
            ),
            "Memory": (
                "`/remember` `/memories` `/forget_me`"
            ),
            "Ambient": (
                "`/ambient_on` `/ambient_off` "
                "`/ambient_status` `/ambient_ignore`"
            ),
            "Community": (
                "`/rank` `/leaderboard` `/image`"
            ),
            "Moderation": (
                "`/warn` `/warnings` `/clear_warnings` "
                "`/timeout` `/untimeout` `/kick` `/ban` "
                "`/unban` `/purge`"
            ),
            "System": (
                "`/ping` `/health` `/privacy` `/terms` "
                "`/support` `/invite` `/data_delete`"
            ),
        }

        for name, value in groups.items():
            embed.add_field(
                name=name,
                value=value,
                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="data_delete",
        description="Delete Judy's stored data for this server."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.describe(
        confirm=(
            "Set to true to permanently delete server data"
        )
    )
    async def data_delete(
        self,
        interaction: discord.Interaction,
        confirm: bool
    ):
        if not confirm:
            await interaction.response.send_message(
                "Nothing was deleted. Run the command with "
                "`confirm: True` to remove this server's "
                "configuration, XP, warnings, chat history "
                "and server-scoped user memories.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        guild_id = interaction.guild.id

        result = await asyncio.to_thread(
            delete_guild_data,
            guild_id,
            [
                channel.id
                for channel in interaction.guild.channels
            ]
        )

        chat_cog = self.bot.get_cog(
            "Chat"
        )

        if chat_cog is not None:
            chat_cog.chat_channels.pop(
                guild_id,
                None
            )

        ambient_cog = self.bot.get_cog(
            "Ambient"
        )

        if ambient_cog is not None:
            ambient_cog.enabled_guilds.discard(
                guild_id
            )

            ambient_cog.ignored_channels.pop(
                guild_id,
                None
            )

        await interaction.followup.send(
            "Server data deleted.\n"
            f"Database rows: "
            f"`{result['database_rows']}`\n"
            f"Memory profiles: "
            f"`{result['user_memory_profiles']}`\n"
            f"Conversation channels: "
            f"`{result['conversation_channels']}`",
            ephemeral=True
        )

    @app_commands.command(
        name="privacy",
        description="Open Project Judy's privacy policy."
    )
    async def privacy(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            f"Privacy policy: {PRIVACY_POLICY_URL}",
            ephemeral=True
        )

    @app_commands.command(
        name="terms",
        description="Open Project Judy's terms of service."
    )
    async def terms(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            f"Terms of service: {TERMS_OF_SERVICE_URL}",
            ephemeral=True
        )

    @app_commands.command(
        name="support",
        description="Open Project Judy's support page."
    )
    async def support(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            f"Support and issue reporting: {SUPPORT_URL}",
            ephemeral=True
        )

    @app_commands.command(
        name="invite",
        description="Generate Project Judy's server install link."
    )
    async def invite(
        self,
        interaction: discord.Interaction
    ):
        if self.bot.user is None:
            await interaction.response.send_message(
                "Judy's application identity is unavailable.",
                ephemeral=True
            )
            return

        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=BOT_PERMISSIONS,
            scopes=(
                "bot",
                "applications.commands"
            )
        )

        embed = discord.Embed(
            title=f"Install {BOT_NAME}",
            description=(
                f"[Add Judy to another server]({invite_url})"
            ),
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Repository",
            value=PROJECT_REPOSITORY_URL,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
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
                "You need Manage Server to change setup."
            )
        else:
            print(
                f"[UTILITY COMMAND ERROR] {error}"
            )

            message = (
                "The utility command hit an unexpected error."
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
    await bot.add_cog(Utility(bot))
