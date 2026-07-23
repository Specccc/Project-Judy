import asyncio

import discord
from discord.ext import commands

from config import (
    BOT_NAME,
    BOT_VERSION,
    COGS_FOLDER,
    COMMAND_PREFIX,
    DISCORD_TOKEN,
    validate_configuration,
)
from database import initialize
from logger import info, success, error

# ==================================================
# Discord Intents
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ==================================================
# Bot
# ==================================================

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    allowed_mentions=(
        discord.AllowedMentions.none()
    )
)

# ==================================================
# Events
# ==================================================

@bot.event
async def on_ready():
    info(f"{BOT_NAME} v{BOT_VERSION}")
    success(f"Connected as {bot.user}")

    await bot.change_presence(
        activity=discord.Game(
            name=f"/help • v{BOT_VERSION}"
        )
    )

    try:
        synced = await bot.tree.sync()
        success(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        error(f"Command sync failed: {e}")


@bot.tree.error
async def on_app_command_error(
    interaction,
    exception
):
    error(
        f"Unhandled command error: {exception}"
    )

    message = (
        "That command hit an unexpected error. "
        "Try `/health` before reporting it."
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

# ==================================================
# Startup
# ==================================================

async def load_cogs():
    for file_path in sorted(
        COGS_FOLDER.glob("*.py")
    ):
        if file_path.name.startswith("_"):
            continue

        if file_path.stat().st_size == 0:
            info(
                f"Skipped empty cog: "
                f"{file_path.name}"
            )
            continue

        extension = (
            f"cogs.{file_path.stem}"
        )

        try:
            await bot.load_extension(extension)
            info(
                f"Loaded cog: {file_path.name}"
            )

        except Exception as exception:
            error(
                f"Failed loading "
                f"{file_path.name}: {exception}"
            )

async def main():
    configuration_errors, warnings = (
        validate_configuration()
    )

    for warning in warnings:
        info(f"Configuration warning: {warning}")

    if configuration_errors:
        raise RuntimeError(
            "Configuration error(s): "
            + " ".join(configuration_errors)
        )

    await initialize()

    await load_cogs()

    async with bot:
        await bot.start(DISCORD_TOKEN)

# ==================================================
# Run
# ==================================================

if __name__ == "__main__":
    asyncio.run(main())
