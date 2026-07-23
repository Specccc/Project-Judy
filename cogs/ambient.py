import asyncio
import json
import random
import sqlite3
import time
from threading import Lock
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ai_service import ai_service
from config import (
    AMBIENT_ACTION_WEIGHTS,
    AMBIENT_DATABASE_FILE,
    AMBIENT_RESPONSES_FILE,
    AMBIENT_SERVER_COOLDOWN_SECONDS,
    AMBIENT_TRIGGER_PROBABILITIES,
    AMBIENT_USER_COOLDOWN_SECONDS,
    COLOR_ERROR,
    COLOR_SUCCESS,
    DATABASE_FOLDER,
)


_database_lock = Lock()


CATEGORY_KEYWORDS = {
    "funny": [
        "lol",
        "lmao",
        "lmfao",
        "haha",
        "hahaha",
        "funny",
        "hilarious",
        "joke",
        "meme",
        "dying",
        "cracked me up",
    ],
    "excitement": [
        "omg",
        "no way",
        "let's go",
        "lets go",
        "finally",
        "amazing",
        "awesome",
        "insane",
        "incredible",
        "preem",
        "nova",
        "we did it",
        "it works",
    ],
    "frustration": [
        "broken",
        "stuck",
        "annoying",
        "frustrated",
        "exhausted",
        "hate this",
        "doesn't work",
        "doesnt work",
        "failed again",
        "why is this happening",
        "giving up",
    ],
    "affection": [
        "love you",
        "love this",
        "miss you",
        "proud of you",
        "cute",
        "beautiful",
        "adorable",
        "wholesome",
        "sweet",
        "means a lot",
    ],
    "tech": [
        "cyberpunk",
        "braindance",
        "bd editor",
        "netrunner",
        "neural",
        "code",
        "coding",
        "python",
        "discord bot",
        "server",
        "database",
        "hardware",
        "software",
        "wiring",
        "headset",
        "game",
        "gaming",
        "graphics card",
        "gpu",
    ],
}


IGNORED_CHANNEL_NAMES = {
    "mod-log",
    "mod-logs",
    "moderation-log",
    "moderation-logs",
    "audit-log",
    "audit-logs",
    "staff-log",
    "staff-logs",
    "bot-log",
    "bot-logs",
}


# ==================================================
# Database
# ==================================================

def initialize_database():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ambient_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ambient_ignored_channels (
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, channel_id)
                )
                """
            )

            connection.commit()


def load_enabled_guilds():
    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            rows = connection.execute(
                """
                SELECT guild_id
                FROM ambient_settings
                WHERE enabled = 1
                """
            ).fetchall()

    return {
        row[0]
        for row in rows
    }


def load_ignored_channels():
    ignored = {}

    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            rows = connection.execute(
                """
                SELECT guild_id, channel_id
                FROM ambient_ignored_channels
                """
            ).fetchall()

    for guild_id, channel_id in rows:
        ignored.setdefault(
            guild_id,
            set(),
        ).add(channel_id)

    return ignored


def save_enabled_state(
    guild_id,
    enabled,
):
    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            connection.execute(
                """
                INSERT INTO ambient_settings (
                    guild_id,
                    enabled
                )
                VALUES (?, ?)
                ON CONFLICT(guild_id)
                DO UPDATE SET enabled = excluded.enabled
                """,
                (
                    guild_id,
                    int(enabled),
                ),
            )

            connection.commit()


def save_ignored_channel(
    guild_id,
    channel_id,
):
    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO ambient_ignored_channels (
                    guild_id,
                    channel_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    channel_id,
                ),
            )

            connection.commit()


def remove_ignored_channel(
    guild_id,
    channel_id,
):
    with _database_lock:
        with sqlite3.connect(
            AMBIENT_DATABASE_FILE,
            timeout=10,
        ) as connection:
            connection.execute(
                """
                DELETE FROM ambient_ignored_channels
                WHERE guild_id = ?
                AND channel_id = ?
                """,
                (
                    guild_id,
                    channel_id,
                ),
            )

            connection.commit()


# ==================================================
# Response Library
# ==================================================

def load_response_library():
    try:
        with AMBIENT_RESPONSES_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Ambient response library must be an object."
            )

        return data

    except Exception as error:
        print(
            "[AMBIENT ERROR] "
            f"Could not load response library: {error}"
        )

        return {
            "reactions": {
                "generic": ["👀", "🔥", "💀"],
            },
            "texts": {
                "generic": [
                    "You've got my attention, choom.",
                ],
            },
            "gifs": {
                "generic": [],
            },
        }


# ==================================================
# Message Classification
# ==================================================

def classify_message(content):
    lowered = content.casefold()

    scores = {
        category: 0
        for category in CATEGORY_KEYWORDS
    }

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[category] += 2

    category = max(
        scores,
        key=scores.get,
    )

    score = scores[category]

    if score == 0:
        return None, 0

    if len(content) >= 45:
        score += 1

    if len(content) >= 100:
        score += 1

    if "!!" in content or "??" in content:
        score += 1

    return category, score


def trigger_probability(score):
    if score <= 2:
        level = 2
    elif score == 3:
        level = 3
    elif score == 4:
        level = 4
    else:
        level = 5

    defaults = {
        2: 0.08,
        3: 0.14,
        4: 0.20,
        5: 0.28,
    }

    return AMBIENT_TRIGGER_PROBABILITIES.get(
        level,
        defaults[level],
    )


def format_duration(seconds):
    if seconds % 60 == 0:
        minutes = seconds // 60

        if minutes == 1:
            return "1 minute"

        return f"{minutes} minutes"

    return f"{seconds} seconds"


# ==================================================
# Ambient Cog
# ==================================================

class Ambient(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        initialize_database()

        self.enabled_guilds = load_enabled_guilds()
        self.ignored_channels = load_ignored_channels()
        self.response_library = load_response_library()

        self.guild_cooldowns = {}
        self.user_cooldowns = {}

    def choose_response(
        self,
        response_type,
        category,
    ):
        response_groups = self.response_library.get(
            response_type,
            {},
        )

        choices = (
            response_groups.get(category)
            or response_groups.get("generic")
            or []
        )

        if not choices:
            return None

        return random.choice(choices)

    def channel_is_ignored(
        self,
        message,
    ):
        guild_id = message.guild.id
        channel_id = message.channel.id

        manually_ignored = self.ignored_channels.get(
            guild_id,
            set(),
        )

        if channel_id in manually_ignored:
            return True

        channel_name = getattr(
            message.channel,
            "name",
            "",
        ).casefold()

        if channel_name in IGNORED_CHANNEL_NAMES:
            return True

        if "mod-log" in channel_name:
            return True

        if "audit-log" in channel_name:
            return True

        return False

    async def message_addresses_judy(
        self,
        message,
    ):
        if self.bot.user is None:
            return False

        if self.bot.user in message.mentions:
            return True

        lowered = message.content.casefold().strip()

        if lowered.startswith("judy"):
            return True

        if (
            message.reference
            and message.reference.message_id
        ):
            referenced = message.reference.resolved

            if isinstance(
                referenced,
                discord.Message,
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
                discord.HTTPException,
            ):
                return False

        return False

    def cooldown_is_active(
        self,
        guild_id,
        user_id,
    ):
        current_time = time.monotonic()

        guild_last_time = self.guild_cooldowns.get(
            guild_id,
            0,
        )

        if (
            current_time - guild_last_time
            < AMBIENT_SERVER_COOLDOWN_SECONDS
        ):
            return True

        user_key = (
            guild_id,
            user_id,
        )

        user_last_time = self.user_cooldowns.get(
            user_key,
            0,
        )

        if (
            current_time - user_last_time
            < AMBIENT_USER_COOLDOWN_SECONDS
        ):
            return True

        return False

    def record_interaction(
        self,
        guild_id,
        user_id,
    ):
        current_time = time.monotonic()

        self.guild_cooldowns[guild_id] = (
            current_time
        )

        self.user_cooldowns[
            (guild_id, user_id)
        ] = current_time

    # ==================================================
    # Ambient Actions
    # ==================================================

    async def send_reaction(
        self,
        message,
        category,
    ):
        reaction = self.choose_response(
            "reactions",
            category,
        )

        if reaction is None:
            return False

        try:
            await message.add_reaction(
                reaction
            )

            return True

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            return False

    async def send_text_reply(
        self,
        message,
        category,
    ):
        text = self.choose_response(
            "texts",
            category,
        )

        if text is None:
            return False

        try:
            await message.reply(
                text,
                mention_author=False,
                allowed_mentions=(
                    discord.AllowedMentions.none()
                ),
            )

            return True

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            return False

    async def send_gif_reply(
        self,
        message,
        category,
    ):
        gif_url = self.choose_response(
            "gifs",
            category,
        )

        if gif_url is None:
            return await self.send_text_reply(
                message,
                category,
            )

        try:
            await message.reply(
                gif_url,
                mention_author=False,
                allowed_mentions=(
                    discord.AllowedMentions.none()
                ),
            )

            return True

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            return False

    async def generate_rare_reply(
        self,
        message,
        category,
    ):
        try:
            reply = await (
                ai_service.generate_ambient_reply(
                    user_name=(
                        message.author.display_name
                    ),
                    message=message.content,
                    category=category,
                    server_name=message.guild.name
                )
            )

            if len(reply) > 500:
                reply = reply[:497] + "..."

            await message.reply(
                reply,
                mention_author=False,
                allowed_mentions=(
                    discord.AllowedMentions.none()
                ),
            )

            return True

        except Exception as error:
            print(
                "[AMBIENT GEMINI ERROR] "
                f"{error}"
            )

            return await self.send_text_reply(
                message,
                category,
            )

    async def perform_interaction(
        self,
        message,
        category,
    ):
        supported_actions = {
            "reaction": 72,
            "text": 20,
            "gif": 7,
            "gemini": 1,
        }

        action_weights = {
            action: AMBIENT_ACTION_WEIGHTS.get(
                action,
                default_weight,
            )
            for action, default_weight
            in supported_actions.items()
        }

        interaction_type = random.choices(
            population=list(action_weights.keys()),
            weights=list(action_weights.values()),
            k=1,
        )[0]

        if interaction_type == "reaction":
            success = await self.send_reaction(
                message,
                category,
            )

        elif interaction_type == "text":
            success = await self.send_text_reply(
                message,
                category,
            )

        elif interaction_type == "gif":
            success = await self.send_gif_reply(
                message,
                category,
            )

        else:
            success = await self.generate_rare_reply(
                message,
                category,
            )

        if success:
            print(
                "[AMBIENT] "
                f"{interaction_type} interaction "
                f"in {message.guild.name} "
                f"for {message.author}"
            )

        return success

    # ==================================================
    # Passive Listener
    # ==================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ):
        if message.guild is None:
            return

        if message.guild.id not in self.enabled_guilds:
            return

        if message.author.bot:
            return

        if message.webhook_id is not None:
            return

        content = message.content.strip()

        if not content:
            return

        if content.startswith(
            ("!", "/")
        ):
            return

        if self.channel_is_ignored(message):
            return

        if await self.message_addresses_judy(message):
            return

        if self.cooldown_is_active(
            message.guild.id,
            message.author.id,
        ):
            return

        category, score = classify_message(
            content
        )

        if category is None:
            return

        probability = trigger_probability(
            score
        )

        if random.random() > probability:
            return

        success = await self.perform_interaction(
            message,
            category,
        )

        if success:
            self.record_interaction(
                message.guild.id,
                message.author.id,
            )

    # ==================================================
    # Commands
    # ==================================================

    @app_commands.command(
        name="ambient_on",
        description="Enable Judy's passive server presence.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def ambient_on(
        self,
        interaction: discord.Interaction,
    ):
        guild_id = interaction.guild.id

        self.enabled_guilds.add(
            guild_id
        )

        await asyncio.to_thread(
            save_enabled_state,
            guild_id,
            True,
        )

        await interaction.response.send_message(
            "Ambient presence enabled. "
            "I'll speak when something's worth saying.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ambient_off",
        description="Disable Judy's passive server presence.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def ambient_off(
        self,
        interaction: discord.Interaction,
    ):
        guild_id = interaction.guild.id

        self.enabled_guilds.discard(
            guild_id
        )

        await asyncio.to_thread(
            save_enabled_state,
            guild_id,
            False,
        )

        await interaction.response.send_message(
            "Ambient presence disabled.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ambient_status",
        description="Show Judy's ambient-presence settings.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def ambient_status(
        self,
        interaction: discord.Interaction,
    ):
        guild_id = interaction.guild.id

        enabled = (
            guild_id in self.enabled_guilds
        )

        ignored_count = len(
            self.ignored_channels.get(
                guild_id,
                set(),
            )
        )

        embed = discord.Embed(
            title="Ambient Presence",
            color=(
                COLOR_SUCCESS
                if enabled
                else COLOR_ERROR
            ),
        )

        embed.add_field(
            name="Status",
            value=(
                "Enabled"
                if enabled
                else "Disabled"
            ),
            inline=True,
        )

        embed.add_field(
            name="Server Cooldown",
            value=format_duration(
                AMBIENT_SERVER_COOLDOWN_SECONDS
            ),
            inline=True,
        )

        embed.add_field(
            name="Per-user Cooldown",
            value=format_duration(
                AMBIENT_USER_COOLDOWN_SECONDS
            ),
            inline=True,
        )

        embed.add_field(
            name="Ignored Channels",
            value=str(ignored_count),
            inline=True,
        )

        embed.add_field(
            name="Behavior",
            value=(
                f"{AMBIENT_ACTION_WEIGHTS.get('reaction', 72)}% reaction\n"
                f"{AMBIENT_ACTION_WEIGHTS.get('text', 20)}% short reply\n"
                f"{AMBIENT_ACTION_WEIGHTS.get('gif', 7)}% curated GIF\n"
                f"{AMBIENT_ACTION_WEIGHTS.get('gemini', 1)}% generated reply"
            ),
            inline=False,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @app_commands.command(
        name="ambient_ignore",
        description="Prevent ambient responses in a channel.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.describe(
        channel="Channel Judy should ignore"
    )
    async def ambient_ignore(
        self,
        interaction: discord.Interaction,
        channel: Optional[
            discord.TextChannel
        ] = None,
    ):
        selected_channel = (
            channel
            or interaction.channel
        )

        guild_id = interaction.guild.id

        self.ignored_channels.setdefault(
            guild_id,
            set(),
        ).add(selected_channel.id)

        await asyncio.to_thread(
            save_ignored_channel,
            guild_id,
            selected_channel.id,
        )

        await interaction.response.send_message(
            f"Ambient presence disabled in "
            f"{selected_channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ambient_allow",
        description="Allow ambient responses in a channel.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.describe(
        channel="Channel Judy may interact in"
    )
    async def ambient_allow(
        self,
        interaction: discord.Interaction,
        channel: Optional[
            discord.TextChannel
        ] = None,
    ):
        selected_channel = (
            channel
            or interaction.channel
        )

        guild_id = interaction.guild.id

        ignored = self.ignored_channels.setdefault(
            guild_id,
            set(),
        )

        ignored.discard(
            selected_channel.id
        )

        await asyncio.to_thread(
            remove_ignored_channel,
            guild_id,
            selected_channel.id,
        )

        await interaction.response.send_message(
            f"Ambient presence allowed in "
            f"{selected_channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ambient_preview",
        description="Preview one ambient response type.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        manage_guild=True
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.choices(
        response_type=[
            app_commands.Choice(
                name="Reaction",
                value="reaction",
            ),
            app_commands.Choice(
                name="Short reply",
                value="text",
            ),
            app_commands.Choice(
                name="Judy GIF",
                value="gif",
            ),
        ]
    )
    async def ambient_preview(
        self,
        interaction: discord.Interaction,
        response_type: app_commands.Choice[str],
    ):
        if response_type.value == "reaction":
            reaction = self.choose_response(
                "reactions",
                "generic",
            )

            if not reaction:
                await interaction.response.send_message(
                    "No reactions are configured.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                "Ambient reaction preview:",
                ephemeral=False,
            )

            preview_message = (
                await interaction.original_response()
            )

            await preview_message.add_reaction(
                reaction
            )

        elif response_type.value == "text":
            text = self.choose_response(
                "texts",
                "generic",
            )

            await interaction.response.send_message(
                text or "No replies are configured.",
                ephemeral=text is None,
            )

        else:
            gif_url = self.choose_response(
                "gifs",
                "generic",
            )

            if gif_url:
                await interaction.response.send_message(
                    gif_url
                )
            else:
                await interaction.response.send_message(
                    "No GIFs are configured.",
                    ephemeral=True,
                )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(
            error,
            app_commands.MissingPermissions,
        ):
            message = (
                "You need Manage Server permission "
                "to configure ambient presence."
            )

        else:
            print(
                f"[AMBIENT COMMAND ERROR] {error}"
            )

            message = (
                "The ambient command hit an "
                "unexpected error."
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(Ambient(bot))
