import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from config import (
    COLOR_JUDY,
    PROFILE_MAX_PREFERRED_NAME_LENGTH,
)
from identity_service import (
    clear_preferred_name,
    get_profile,
    get_relationship,
    set_preferred_name,
)


def _format_date(value):
    if not value:
        return "Never"

    try:
        parsed = datetime.fromisoformat(
            value
        )
        return discord.utils.format_dt(
            parsed,
            style="R"
        )
    except ValueError:
        return "Unknown"


class Identity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Show your Project Judy profile."
    )
    @app_commands.guild_only()
    async def profile(
        self,
        interaction: discord.Interaction
    ):
        profile = await asyncio.to_thread(
            get_profile,
            interaction.guild.id,
            interaction.user.id
        )

        relationship = await asyncio.to_thread(
            get_relationship,
            interaction.guild.id,
            interaction.user.id
        )

        if profile is None:
            await interaction.response.send_message(
                "No profile yet. Talk to Judy first.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Your Project Judy Profile",
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Name",
            value=(
                profile.preferred_name
                or profile.display_name
            ),
            inline=True
        )

        embed.add_field(
            name="Discord Name",
            value=profile.display_name,
            inline=True
        )

        embed.add_field(
            name="Relationship",
            value=(
                relationship.tier.title()
                if relationship
                else "Stranger"
            ),
            inline=True
        )

        embed.add_field(
            name="Direct Interactions",
            value=str(
                profile.message_count
            ),
            inline=True
        )

        embed.add_field(
            name="First Seen",
            value=_format_date(
                profile.first_seen_at
            ),
            inline=True
        )

        embed.add_field(
            name="Last Seen",
            value=_format_date(
                profile.last_seen_at
            ),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="relationship",
        description="Show your relationship with Judy."
    )
    @app_commands.guild_only()
    async def relationship(
        self,
        interaction: discord.Interaction
    ):
        relationship = await asyncio.to_thread(
            get_relationship,
            interaction.guild.id,
            interaction.user.id
        )

        if relationship is None:
            await interaction.response.send_message(
                "We're strangers. Talk to me first, choom.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Relationship with Judy",
            description=(
                f"Current tier: "
                f"**{relationship.tier.title()}**"
            ),
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Trust",
            value=str(relationship.trust),
            inline=True
        )

        embed.add_field(
            name="Familiarity",
            value=str(
                relationship.familiarity
            ),
            inline=True
        )

        embed.add_field(
            name="Affinity",
            value=str(
                relationship.affinity
            ),
            inline=True
        )

        embed.set_footer(
            text=(
                "Relationships develop gradually "
                "through direct conversations."
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="set_name",
        description="Set the name Judy should use for you."
    )
    @app_commands.guild_only()
    @app_commands.describe(
        name=(
            "Your preferred name, or leave blank "
            "to use your Discord display name"
        )
    )
    async def set_name(
        self,
        interaction: discord.Interaction,
        name: str = ""
    ):
        name = name.strip()

        if not name:
            await asyncio.to_thread(
                clear_preferred_name,
                interaction.guild.id,
                interaction.user.id
            )

            await interaction.response.send_message(
                "Preferred name cleared. I'll use your "
                "Discord display name.",
                ephemeral=True
            )
            return

        if (
            len(name)
            > PROFILE_MAX_PREFERRED_NAME_LENGTH
        ):
            await interaction.response.send_message(
                "Keep the name under "
                f"{PROFILE_MAX_PREFERRED_NAME_LENGTH} "
                "characters.",
                ephemeral=True
            )
            return

        saved = await asyncio.to_thread(
            set_preferred_name,
            interaction.guild.id,
            interaction.user.id,
            interaction.user.display_name,
            name
        )

        if not saved:
            await interaction.response.send_message(
                "That name could not be saved.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Got it. I'll call you **{name}**.",
            ephemeral=True,
            allowed_mentions=(
                discord.AllowedMentions.none()
            )
        )


async def setup(bot):
    await bot.add_cog(Identity(bot))
