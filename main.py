import asyncio
import discord
from discord.ext import commands

from config import BOT_NAME, BOT_VERSION
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
    command_prefix="!",
    intents=intents
)

# ==================================================
# Startup
# ==================================================

@bot.event
async def on_ready():
    await initialize()

    info(f"{BOT_NAME} v{BOT_VERSION}")
    success(f"Connected as {bot.user}")

    try:
        synced = await bot.tree.sync()
        success(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        error(f"Command sync failed: {e}")

# ==================================================
# Run Bot
# ==================================================

async def main():
    from config import DISCORD_TOKEN

    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing.")

    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
