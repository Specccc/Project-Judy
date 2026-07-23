import re
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands

from config import BOT_NAME, COLOR_JUDY


def owner_only():
    async def predicate(
        interaction: discord.Interaction
    ):
        return await interaction.client.is_owner(
            interaction.user
        )

    return app_commands.check(predicate)


class ShutdownConfirmation(discord.ui.View):
    def __init__(self, bot, owner_id):
        super().__init__(timeout=30)

        self.bot = bot
        self.owner_id = owner_id
        self.message = None

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the bot owner can control this.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Shut Down",
        style=discord.ButtonStyle.danger
    )
    async def confirm_shutdown(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="Shutting Judy down.",
            view=self
        )

        await self.bot.close()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_shutdown(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="Shutdown cancelled.",
            view=self
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(
                    content="Shutdown request expired.",
                    view=self
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                pass


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_at = datetime.now(timezone.utc)

    @app_commands.command(
        name="owner_status",
        description="Display Judy's internal bot status."
    )
    @owner_only()
    async def owner_status(
        self,
        interaction: discord.Interaction
    ):
        current_time = datetime.now(timezone.utc)
        uptime = current_time - self.loaded_at

        total_seconds = int(
            uptime.total_seconds()
        )

        days, remainder = divmod(
            total_seconds,
            86400
        )

        hours, remainder = divmod(
            remainder,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )

        uptime_text = (
            f"{days}d {hours}h "
            f"{minutes}m {seconds}s"
        )

        total_members = sum(
            guild.member_count or 0
            for guild in self.bot.guilds
        )

        loaded_extensions = len(
            self.bot.extensions
        )

        loaded_cogs = len(
            self.bot.cogs
        )

        slash_commands = len(
            self.bot.tree.get_commands()
        )

        embed = discord.Embed(
            title=f"{BOT_NAME} — Owner Status",
            color=COLOR_JUDY,
            timestamp=current_time
        )

        embed.add_field(
            name="Connected As",
            value=str(self.bot.user),
            inline=False
        )

        embed.add_field(
            name="Latency",
            value=(
                f"{round(self.bot.latency * 1000)} ms"
            ),
            inline=True
        )

        embed.add_field(
            name="Uptime",
            value=uptime_text,
            inline=True
        )

        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds)),
            inline=True
        )

        embed.add_field(
            name="Visible Members",
            value=str(total_members),
            inline=True
        )

        embed.add_field(
            name="Loaded Cogs",
            value=str(loaded_cogs),
            inline=True
        )

        embed.add_field(
            name="Extensions",
            value=str(loaded_extensions),
            inline=True
        )

        embed.add_field(
            name="Global Commands",
            value=str(slash_commands),
            inline=True
        )

        embed.add_field(
            name="Discord.py",
            value=discord.__version__,
            inline=True
        )

        if self.bot.user is not None:
            embed.set_thumbnail(
                url=self.bot.user.display_avatar.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="owner_cogs",
        description="List Judy's loaded cogs and extensions."
    )
    @owner_only()
    async def owner_cogs(
        self,
        interaction: discord.Interaction
    ):
        cog_names = sorted(
            self.bot.cogs.keys()
        )

        extension_names = sorted(
            self.bot.extensions.keys()
        )

        cog_text = (
            "\n".join(
                f"• `{name}`"
                for name in cog_names
            )
            or "No cogs loaded."
        )

        extension_text = (
            "\n".join(
                f"• `{name}`"
                for name in extension_names
            )
            or "No extensions loaded."
        )

        embed = discord.Embed(
            title="Loaded Components",
            color=COLOR_JUDY
        )

        embed.add_field(
            name="Cogs",
            value=cog_text[:1024],
            inline=False
        )

        embed.add_field(
            name="Extensions",
            value=extension_text[:1024],
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
        name="owner_reload",
        description="Reload one of Judy's cogs."
    )
    @app_commands.describe(
        cog="Cog filename without the .py extension"
    )
    @owner_only()
    async def owner_reload(
        self,
        interaction: discord.Interaction,
        cog: str
    ):
        cog_name = cog.strip().lower()

        if cog_name.endswith(".py"):
            cog_name = cog_name[:-3]

        if not re.fullmatch(
            r"[a-z0-9_]+",
            cog_name
        ):
            await interaction.response.send_message(
                "Invalid cog name.",
                ephemeral=True
            )
            return

        extension = f"cogs.{cog_name}"

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:
            if extension in self.bot.extensions:
                await self.bot.reload_extension(
                    extension
                )

                action = "Reloaded"

            else:
                await self.bot.load_extension(
                    extension
                )

                action = "Loaded"

            await interaction.followup.send(
                f"{action} `{extension}`.",
                ephemeral=True
            )

        except commands.ExtensionNotFound:
            await interaction.followup.send(
                f"Could not find `{extension}`.",
                ephemeral=True
            )

        except commands.NoEntryPointError:
            await interaction.followup.send(
                f"`{extension}` does not contain "
                f"an async `setup(bot)` function.",
                ephemeral=True
            )

        except commands.ExtensionFailed as error:
            print(
                f"[OWNER RELOAD ERROR] {error}"
            )

            await interaction.followup.send(
                f"`{extension}` failed while loading:\n"
                f"```text\n{error}\n```",
                ephemeral=True
            )

        except Exception as error:
            print(
                f"[OWNER RELOAD ERROR] {error}"
            )

            await interaction.followup.send(
                f"Could not reload `{extension}`:\n"
                f"```text\n{error}\n```",
                ephemeral=True
            )

    @app_commands.command(
        name="owner_sync",
        description="Synchronize Judy's global slash commands."
    )
    @owner_only()
    async def owner_sync(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:
            synced = await self.bot.tree.sync()

            await interaction.followup.send(
                f"Synced **{len(synced)}** global "
                f"slash command(s).",
                ephemeral=True
            )

        except discord.HTTPException as error:
            print(
                f"[OWNER SYNC ERROR] {error}"
            )

            await interaction.followup.send(
                f"Discord rejected the command sync:\n"
                f"```text\n{error}\n```",
                ephemeral=True
            )

    @app_commands.command(
        name="owner_activity",
        description="Change Judy's Discord activity text."
    )
    @app_commands.describe(
        text="The activity text Judy should display"
    )
    @owner_only()
    async def owner_activity(
        self,
        interaction: discord.Interaction,
        text: str
    ):
        text = text.strip()

        if not text:
            await interaction.response.send_message(
                "The activity text cannot be empty.",
                ephemeral=True
            )
            return

        if len(text) > 100:
            await interaction.response.send_message(
                "Keep the activity text under "
                "100 characters.",
                ephemeral=True
            )
            return

        await self.bot.change_presence(
            activity=discord.Game(name=text)
        )

        await interaction.response.send_message(
            f"Activity changed to: **{text}**",
            ephemeral=True
        )

    @app_commands.command(
        name="owner_activity_clear",
        description="Remove Judy's custom activity text."
    )
    @owner_only()
    async def owner_activity_clear(
        self,
        interaction: discord.Interaction
    ):
        await self.bot.change_presence(
            activity=None
        )

        await interaction.response.send_message(
            "Custom activity removed.",
            ephemeral=True
        )

    @app_commands.command(
        name="owner_shutdown",
        description="Safely disconnect Judy from Discord."
    )
    @owner_only()
    async def owner_shutdown(
        self,
        interaction: discord.Interaction
    ):
        confirmation = ShutdownConfirmation(
            self.bot,
            interaction.user.id
        )

        await interaction.response.send_message(
            "Confirm Judy's shutdown.",
            view=confirmation,
            ephemeral=True
        )

        confirmation.message = (
            await interaction.original_response()
        )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(
            error,
            app_commands.CheckFailure
        ):
            message = (
                "This command is restricted to "
                f"{BOT_NAME}'s owner."
            )

        else:
            print(
                f"[OWNER COMMAND ERROR] {error}"
            )

            message = (
                "The owner command hit an "
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
    await bot.add_cog(Owner(bot))
