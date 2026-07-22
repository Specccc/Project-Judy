import discord
from discord.ext import commands
from discord import app_commands


class Diagnostics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check if Judy is online."
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🏓 Pong! Judy is online.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Diagnostics(bot))
