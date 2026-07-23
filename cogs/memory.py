import discord
from discord.ext import commands
from discord import app_commands

from config import MEMORY_MAX_FACT_LENGTH
from identity_service import (
    delete_user_identity,
)
from memory.memory_manager import (
    forget_user,
    get_user_memory,
    remember_user_fact,
)


class MemoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="remember",
        description="Save something in Judy's long-term memory."
    )
    @app_commands.guild_only()
    @app_commands.describe(
        subject="What the information is about, such as name or favourite_game",
        detail="The information Judy should remember"
    )
    async def remember(
        self,
        interaction: discord.Interaction,
        subject: str,
        detail: str
    ):
        subject = subject.strip().lower().replace(" ", "_")
        detail = detail.strip()

        if not subject or not detail:
            await interaction.response.send_message(
                "Give me something useful to remember, choom.",
                ephemeral=True
            )
            return

        if len(subject) > 100:
            await interaction.response.send_message(
                "That subject name is too long.",
                ephemeral=True
            )
            return

        if len(detail) > MEMORY_MAX_FACT_LENGTH:
            await interaction.response.send_message(
                "That memory is too long. Keep it under "
                f"{MEMORY_MAX_FACT_LENGTH:,} characters.",
                ephemeral=True
            )
            return

        saved = remember_user_fact(
            interaction.guild.id,
            interaction.user.id,
            subject,
            detail
        )

        if not saved:
            await interaction.response.send_message(
                "That memory could not be saved. You may "
                "have reached the memory limit.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Got it. I'll remember `{subject}`: {detail}",
            ephemeral=True
        )

    async def _send_memories(
        self,
        interaction: discord.Interaction
    ):
        stored_memories = get_user_memory(
            interaction.guild.id,
            interaction.user.id
        )

        if not stored_memories:
            await interaction.response.send_message(
                "I don't have any long-term memories about you yet.",
                ephemeral=True
            )
            return

        lines = ["Here's what I remember about you:"]

        for subject, detail in stored_memories.items():
            lines.append(f"- **{subject}:** {detail}")

        response = "\n".join(lines)

        if len(response) > 1900:
            response = response[:1897] + "..."

        await interaction.response.send_message(
            response,
            ephemeral=True
        )

    @app_commands.command(
        name="memories",
        description="Show what Judy remembers about you."
    )
    @app_commands.guild_only()
    async def memories(
        self,
        interaction: discord.Interaction
    ):
        await self._send_memories(
            interaction
        )

    @app_commands.command(
        name="memory",
        description="Show what Judy remembers about you."
    )
    @app_commands.guild_only()
    async def memory(
        self,
        interaction: discord.Interaction
    ):
        await self._send_memories(
            interaction
        )

    @app_commands.command(
        name="forget_me",
        description="Delete everything Judy remembers about you."
    )
    @app_commands.guild_only()
    async def forget_me(
        self,
        interaction: discord.Interaction
    ):
        forget_user(
            interaction.guild.id,
            interaction.user.id
        )

        delete_user_identity(
            interaction.guild.id,
            interaction.user.id
        )

        await interaction.response.send_message(
            "Memory, profile and relationship state wiped. "
            "Clean slate, choom.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(MemoryCog(bot))
