import asyncio
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

from ai_service import ai_service
from config import (
    AMBIENT_RESPONSES_FILE,
    BOT_NAME,
    BOT_VERSION,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    CONVERSATION_MEMORY_FILE,
    DATABASE_FOLDER,
    JUDY_MEMORY_FILE,
    PROJECT_ROOT,
    safe_configuration_summary,
    validate_configuration,
)
from identity_service import (
    identity_statistics,
)


STARTED_AT = datetime.now(timezone.utc)


def owner_only():
    async def predicate(
        interaction: discord.Interaction
    ):
        return await interaction.client.is_owner(
            interaction.user
        )

    return app_commands.check(predicate)


def format_bytes(size):
    size = float(size)

    units = [
        "B",
        "KiB",
        "MiB",
        "GiB"
    ]

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} TiB"


def get_current_memory_usage():
    status_file = Path(
        "/proc/self/status"
    )

    try:
        content = status_file.read_text(
            encoding="utf-8"
        )

        for line in content.splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()

                if len(parts) >= 2:
                    kilobytes = int(parts[1])
                    return kilobytes * 1024

    except (OSError, ValueError):
        pass

    return None


def inspect_json_file(file_path):
    if not file_path.exists():
        return {
            "status": "missing",
            "size": 0,
            "entries": 0
        }

    try:
        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            return {
                "status": "empty",
                "size": file_path.stat().st_size,
                "entries": 0
            }

        data = json.loads(content)

        if isinstance(data, dict):
            entries = len(data)

        elif isinstance(data, list):
            entries = len(data)

        else:
            entries = 1

        return {
            "status": "healthy",
            "size": file_path.stat().st_size,
            "entries": entries
        }

    except json.JSONDecodeError:
        return {
            "status": "invalid JSON",
            "size": file_path.stat().st_size,
            "entries": 0
        }

    except OSError:
        return {
            "status": "unreadable",
            "size": 0,
            "entries": 0
        }


def inspect_database_file(file_path):
    try:
        connection = sqlite3.connect(
            f"file:{file_path}?mode=ro",
            uri=True,
            timeout=5
        )

        result = connection.execute(
            "PRAGMA quick_check"
        ).fetchone()

        table_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchone()

        connection.close()

        status = (
            result[0]
            if result
            else "unknown"
        )

        table_count = (
            table_rows[0]
            if table_rows
            else 0
        )

        return {
            "status": status,
            "tables": table_count,
            "size": file_path.stat().st_size
        }

    except sqlite3.Error as error:
        return {
            "status": f"error: {error}",
            "tables": 0,
            "size": (
                file_path.stat().st_size
                if file_path.exists()
                else 0
            )
        }


def inspect_all_databases():
    if not DATABASE_FOLDER.exists():
        return []

    results = []

    for file_path in sorted(
        DATABASE_FOLDER.glob("*.db")
    ):
        information = inspect_database_file(
            file_path
        )

        results.append(
            (
                file_path.name,
                information
            )
        )

    return results


def uptime_text():
    current_time = datetime.now(timezone.utc)
    difference = current_time - STARTED_AT

    total_seconds = int(
        difference.total_seconds()
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

    return (
        f"{days}d {hours}h "
        f"{minutes}m {seconds}s"
    )


class Diagnostics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check whether Judy is responsive."
    )
    async def ping(
        self,
        interaction: discord.Interaction
    ):
        latency = round(
            self.bot.latency * 1000
        )

        await interaction.response.send_message(
            f"Online. **{latency} ms**."
        )

    @app_commands.command(
        name="health",
        description="Show Judy's basic system health."
    )
    async def health(
        self,
        interaction: discord.Interaction
    ):
        errors, warnings = (
            validate_configuration()
        )

        ai_status = ai_service.status()

        memory_files = [
            inspect_json_file(
                CONVERSATION_MEMORY_FILE
            ),
            inspect_json_file(
                JUDY_MEMORY_FILE
            ),
            inspect_json_file(
                AMBIENT_RESPONSES_FILE
            )
        ]

        invalid_memory_files = [
            result
            for result in memory_files
            if result["status"] not in {
                "healthy",
                "empty"
            }
        ]

        if errors or invalid_memory_files:
            status = "Critical"
            color = COLOR_ERROR

        elif warnings:
            status = "Warning"
            color = COLOR_WARNING

        else:
            status = "Healthy"
            color = COLOR_SUCCESS

        embed = discord.Embed(
            title=f"{BOT_NAME} Health",
            color=color,
            timestamp=datetime.now(
                timezone.utc
            )
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )

        embed.add_field(
            name="Version",
            value=BOT_VERSION,
            inline=True
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
            value=uptime_text(),
            inline=True
        )

        embed.add_field(
            name="Loaded Cogs",
            value=str(len(self.bot.cogs)),
            inline=True
        )

        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds)),
            inline=True
        )

        embed.add_field(
            name="AI Core",
            value=(
                "Ready"
                if ai_status.configured
                else "Unavailable"
            ),
            inline=True
        )

        if errors:
            embed.add_field(
                name="Errors",
                value="\n".join(
                    f"• {error}"
                    for error in errors
                )[:1024],
                inline=False
            )

        if warnings:
            embed.add_field(
                name="Warnings",
                value="\n".join(
                    f"• {warning}"
                    for warning in warnings
                )[:1024],
                inline=False
            )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="diagnostics",
        description="Display Judy's detailed private diagnostics."
    )
    @owner_only()
    async def diagnostics(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        errors, warnings = (
            validate_configuration()
        )

        configuration = (
            safe_configuration_summary()
        )

        ai_status = ai_service.status()

        database_results = await asyncio.to_thread(
            inspect_all_databases
        )

        conversation_information = (
            await asyncio.to_thread(
                inspect_json_file,
                CONVERSATION_MEMORY_FILE
            )
        )

        memory_information = (
            await asyncio.to_thread(
                inspect_json_file,
                JUDY_MEMORY_FILE
            )
        )

        ambient_information = (
            await asyncio.to_thread(
                inspect_json_file,
                AMBIENT_RESPONSES_FILE
            )
        )

        identity_information = (
            await asyncio.to_thread(
                identity_statistics
            )
        )

        disk = shutil.disk_usage(
            PROJECT_ROOT
        )

        memory_usage = (
            get_current_memory_usage()
        )

        if errors:
            status = "Critical"
            color = COLOR_ERROR

        elif warnings:
            status = "Warning"
            color = COLOR_WARNING

        else:
            status = "Healthy"
            color = COLOR_INFO

        embed = discord.Embed(
            title="Project Judy Diagnostics",
            description=(
                f"Overall status: **{status}**"
            ),
            color=color,
            timestamp=datetime.now(
                timezone.utc
            )
        )

        embed.add_field(
            name="Runtime",
            value=(
                f"Version: `{BOT_VERSION}`\n"
                f"Uptime: `{uptime_text()}`\n"
                f"Latency: "
                f"`{round(self.bot.latency * 1000)} ms`\n"
                f"Servers: `{len(self.bot.guilds)}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Environment",
            value=(
                f"Discord token: "
                f"`{configuration['discord_token_loaded']}`\n"
                f"Gemini key: "
                f"`{configuration['gemini_key_loaded']}`\n"
                f"Serper key: "
                f"`{configuration['serper_key_loaded']}`\n"
                f"Chat model: "
                f"`{configuration['chat_model']}`\n"
                f"Ambient model: "
                f"`{configuration['ambient_model']}`"
            ),
            inline=False
        )

        embed.add_field(
            name="AI Core",
            value=(
                f"Configured: `{ai_status.configured}`\n"
                f"Active requests: "
                f"`{ai_status.active_requests}`\n"
                f"Total requests: "
                f"`{ai_status.total_requests}`\n"
                f"Failed requests: "
                f"`{ai_status.failed_requests}`\n"
                f"Last latency: "
                f"`{ai_status.last_latency_ms} ms`"
            ),
            inline=False
        )

        embed.add_field(
            name="Memory Files",
            value=(
                "Conversation cache: "
                f"`{conversation_information['status']}` "
                f"({format_bytes(conversation_information['size'])}, "
                f"{conversation_information['entries']} channels)\n"
                "User memory: "
                f"`{memory_information['status']}` "
                f"({format_bytes(memory_information['size'])}, "
                f"{memory_information['entries']} users)\n"
                "Ambient library: "
                f"`{ambient_information['status']}` "
                f"({format_bytes(ambient_information['size'])})"
            ),
            inline=False
        )

        tier_text = ", ".join(
            f"{name}: {count}"
            for name, count
            in identity_information[
                "tiers"
            ].items()
        )

        embed.add_field(
            name="Identity System",
            value=(
                f"Profiles: "
                f"`{identity_information['profiles']}`\n"
                f"Relationships: "
                f"`{identity_information['relationships']}`\n"
                f"Tiers: `{tier_text}`"
            )[:1024],
            inline=False
        )

        if database_results:
            database_lines = []

            for name, information in database_results:
                database_lines.append(
                    f"`{name}` — "
                    f"{information['status']}, "
                    f"{information['tables']} tables, "
                    f"{format_bytes(information['size'])}"
                )

            database_text = "\n".join(
                database_lines
            )

        else:
            database_text = (
                "No SQLite databases found."
            )

        embed.add_field(
            name="SQLite Databases",
            value=database_text[:1024],
            inline=False
        )

        embed.add_field(
            name="Resources",
            value=(
                "Current bot RAM: "
                f"`{format_bytes(memory_usage)}`\n"
                if memory_usage is not None
                else "Current bot RAM: `Unavailable`\n"
            ) + (
                f"Disk used: "
                f"`{format_bytes(disk.used)}`\n"
                f"Disk free: "
                f"`{format_bytes(disk.free)}`"
            ),
            inline=False
        )

        loaded_cogs = ", ".join(
            sorted(self.bot.cogs.keys())
        )

        embed.add_field(
            name="Loaded Cogs",
            value=(
                loaded_cogs[:1024]
                or "None"
            ),
            inline=False
        )

        if errors:
            embed.add_field(
                name="Configuration Errors",
                value="\n".join(
                    f"• {error}"
                    for error in errors
                )[:1024],
                inline=False
            )

        if warnings:
            embed.add_field(
                name="Configuration Warnings",
                value="\n".join(
                    f"• {warning}"
                    for warning in warnings
                )[:1024],
                inline=False
            )

        await interaction.followup.send(
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
            app_commands.CheckFailure
        ):
            message = (
                "Detailed diagnostics are restricted "
                "to Project Judy's owner."
            )

        else:
            print(
                f"[DIAGNOSTICS ERROR] {error}"
            )

            message = (
                "The diagnostics command failed."
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
    await bot.add_cog(Diagnostics(bot))
