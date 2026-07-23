import asyncio
import sqlite3
from threading import Lock

import discord
from discord.ext import commands
from discord import app_commands

from ai_service import ai_service
from config import (
    CHAT_ERROR_MESSAGE,
    CHAT_DATABASE_FILE,
    CHAT_GUILD_COOLDOWN_SECONDS,
    CHAT_MAX_REPLY_LENGTH,
    CHAT_USER_COOLDOWN_SECONDS,
    DATABASE_FOLDER,
)
from identity_service import (
    build_identity_context,
    record_interaction,
)

from memory.memory_manager import (
    add_conversation_message,
    build_conversation_context,
    build_user_memory_context,
    clear_conversation,
)


_database_lock = Lock()


def initialize_chat_database():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    with _database_lock:
        with sqlite3.connect(
            CHAT_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_channels (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
                """
            )

            connection.commit()


def load_chat_channels():
    with _database_lock:
        with sqlite3.connect(
            CHAT_DATABASE_FILE,
            timeout=10
        ) as connection:
            rows = connection.execute(
                """
                SELECT guild_id, channel_id
                FROM chat_channels
                """
            ).fetchall()

    return {
        guild_id: channel_id
        for guild_id, channel_id in rows
    }


def save_chat_channel(
    guild_id,
    channel_id
):
    with _database_lock:
        with sqlite3.connect(
            CHAT_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                INSERT INTO chat_channels (
                    guild_id,
                    channel_id
                )
                VALUES (?, ?)
                ON CONFLICT(guild_id)
                DO UPDATE SET
                    channel_id = excluded.channel_id
                """,
                (
                    guild_id,
                    channel_id
                )
            )

            connection.commit()


def remove_chat_channel(guild_id):
    with _database_lock:
        with sqlite3.connect(
            CHAT_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                DELETE FROM chat_channels
                WHERE guild_id = ?
                """,
                (guild_id,)
            )

            connection.commit()


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        initialize_chat_database()

        self.chat_channels = (
            load_chat_channels()
        )

        self.channel_locks = {}
        self.user_cooldowns = {}
        self.guild_cooldowns = {}

    def get_channel_lock(
        self,
        channel_id
    ):
        if channel_id not in self.channel_locks:
            self.channel_locks[channel_id] = (
                asyncio.Lock()
            )

        return self.channel_locks[channel_id]

    @app_commands.command(
        name="chatmode_on",
        description="Enable Judy AI chat in this channel."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def chatmode_on(
        self,
        interaction: discord.Interaction
    ):
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        self.chat_channels[guild_id] = (
            channel_id
        )

        await asyncio.to_thread(
            save_chat_channel,
            guild_id,
            channel_id
        )

        await interaction.response.send_message(
            "I'm here. Don't make me regret it, choom."
        )

    @app_commands.command(
        name="chatmode_off",
        description="Disable Judy AI chat for this server."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def chatmode_off(
        self,
        interaction: discord.Interaction
    ):
        guild_id = interaction.guild.id

        self.chat_channels.pop(
            guild_id,
            None
        )

        await asyncio.to_thread(
            remove_chat_channel,
            guild_id
        )

        await interaction.response.send_message(
            "Later, choom."
        )

    @app_commands.command(
        name="chatmode_status",
        description="Show Judy's configured chat channel."
    )
    @app_commands.guild_only()
    async def chatmode_status(
        self,
        interaction: discord.Interaction
    ):
        channel_id = self.chat_channels.get(
            interaction.guild.id
        )

        if channel_id is None:
            await interaction.response.send_message(
                "Chat mode is disabled for this server.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(
            channel_id
        )

        if channel is None:
            value = f"Missing channel `{channel_id}`"
        else:
            value = channel.mention

        await interaction.response.send_message(
            f"Judy's chat channel: {value}",
            ephemeral=True
        )

    @app_commands.command(
        name="conversation_clear",
        description="Clear Judy's conversation for this channel."
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_messages=True
    )
    @app_commands.checks.has_permissions(
        manage_messages=True
    )
    async def conversation_clear(
        self,
        interaction: discord.Interaction
    ):
        removed = await asyncio.to_thread(
            clear_conversation,
            interaction.channel.id
        )

        if removed:
            message = (
                "Conversation wiped. Clean slate."
            )
        else:
            message = (
                "There wasn't anything saved here."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

    async def message_calls_judy(
        self,
        message
    ):
        if self.bot.user is None:
            return False

        if self.bot.user in message.mentions:
            return True

        if (
            message.content
            .casefold()
            .strip()
            .startswith("judy")
        ):
            return True

        if (
            message.reference
            and message.reference.message_id
        ):
            referenced = (
                message.reference.resolved
            )

            if isinstance(
                referenced,
                discord.Message
            ):
                return (
                    referenced.author.id
                    == self.bot.user.id
                )

            try:
                referenced = (
                    await message.channel.fetch_message(
                        message.reference.message_id
                    )
                )

                return (
                    referenced.author.id
                    == self.bot.user.id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                return False

        return False

    def clean_message_content(
        self,
        message
    ):
        content = message.content

        if self.bot.user is not None:
            content = content.replace(
                f"<@{self.bot.user.id}>",
                ""
            )

            content = content.replace(
                f"<@!{self.bot.user.id}>",
                ""
            )

        content = content.strip()

        if not content:
            return (
                "The user called your name."
            )

        return content

    def cooldown_is_active(
        self,
        guild_id,
        user_id
    ):
        current_time = asyncio.get_running_loop().time()

        guild_last = self.guild_cooldowns.get(
            guild_id,
            0
        )

        if (
            current_time - guild_last
            < CHAT_GUILD_COOLDOWN_SECONDS
        ):
            return True

        user_last = self.user_cooldowns.get(
            (guild_id, user_id),
            0
        )

        return (
            current_time - user_last
            < CHAT_USER_COOLDOWN_SECONDS
        )

    def record_cooldown(
        self,
        guild_id,
        user_id
    ):
        current_time = asyncio.get_running_loop().time()

        self.guild_cooldowns[guild_id] = current_time
        self.user_cooldowns[
            (guild_id, user_id)
        ] = current_time

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):
        if message.author.bot:
            return

        if message.guild is None:
            return

        configured_channel = (
            self.chat_channels.get(
                message.guild.id
            )
        )

        if configured_channel is None:
            return

        if message.channel.id != configured_channel:
            return

        if not await self.message_calls_judy(
            message
        ):
            return

        clean_message = (
            self.clean_message_content(
                message
            )
        )

        channel_id = message.channel.id
        user_id = message.author.id
        guild_id = message.guild.id

        if self.cooldown_is_active(
            guild_id,
            user_id
        ):
            return

        self.record_cooldown(
            guild_id,
            user_id
        )

        channel_lock = self.get_channel_lock(
            channel_id
        )

        async with channel_lock:
            conversation_context = (
                await asyncio.to_thread(
                    build_conversation_context,
                    channel_id
                )
            )

            user_memory_context = (
                await asyncio.to_thread(
                    build_user_memory_context,
                    guild_id,
                    user_id
                )
            )

            await asyncio.to_thread(
                record_interaction,
                guild_id,
                user_id,
                message.author.display_name,
                clean_message
            )

            identity_context = (
                await asyncio.to_thread(
                    build_identity_context,
                    guild_id,
                    user_id
                )
            )

            await asyncio.to_thread(
                add_conversation_message,
                channel_id,
                "user",
                (
                    f"{message.author.display_name}: "
                    f"{clean_message}"
                )
            )

            try:
                async with message.channel.typing():
                    reply = await (
                        ai_service.generate_chat_reply(
                            user_name=(
                                message.author.display_name
                            ),
                            user_id=user_id,
                            message=clean_message,
                            conversation_context=(
                                conversation_context
                            ),
                            memory_context=(
                                user_memory_context
                            ),
                            identity_context=(
                                identity_context
                            ),
                            server_name=(
                                message.guild.name
                            )
                        )
                    )

                if len(reply) > CHAT_MAX_REPLY_LENGTH:
                    reply = (
                        reply[
                            :CHAT_MAX_REPLY_LENGTH - 3
                        ]
                        + "..."
                    )

                await asyncio.to_thread(
                    add_conversation_message,
                    channel_id,
                    "assistant",
                    reply
                )

                await message.reply(
                    reply,
                    mention_author=False,
                    allowed_mentions=(
                        discord.AllowedMentions.none()
                    )
                )

            except Exception as error:
                print(
                    f"[CHAT ERROR] {error}"
                )

                await message.reply(
                    CHAT_ERROR_MESSAGE,
                    mention_author=False,
                    allowed_mentions=(
                        discord.AllowedMentions.none()
                    )
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
                "You need the required server "
                "permissions to change chat mode."
            )

        else:
            print(
                f"[CHAT COMMAND ERROR] {error}"
            )

            message = (
                "The chat command hit an "
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
    await bot.add_cog(Chat(bot))
