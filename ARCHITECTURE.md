# Project Judy Architecture

## Overview

Project Judy is a modular Discord bot built using Python and discord.py.

The project is designed so that new features can be added without modifying the core framework.

---

# Core Files

## main.py

Starts Judy.

- Loads every Cog automatically.
- Connects to Discord.
- Starts all core services.

---

## config.py

Stores configuration.

Examples:

- Bot Version
- Bot Name
- Discord Token
- Gemini API Key
- Embed Colours

---

## database.py

Handles all SQLite connections.

Every Cog shares this database.

---

## logger.py

Console logging.

Provides:

- INFO
- SUCCESS
- WARNING
- ERROR

---

## log_service.py

Creates Discord embeds for logging.

All modules use one logging system.

---

## ai_service.py

Single connection to Google Gemini.

Future AI features will use this service instead of creating their own Gemini connections.

---

## errors.py

Shared error handling.

Keeps command responses consistent.

---

# Cogs

Every major system belongs inside its own Cog.

Examples:

- diagnostics.py
- moderation.py
- verification.py
- leveling.py
- welcome.py
- chatmode.py
- ask.py

The core should almost never require editing.

Adding a feature should normally mean adding a new Cog.

---

# Database

SQLite

Planned tables include:

- guild_config
- users
- xp
- warnings
- moderation
- verification

---

# Assets

Stores:

- Images
- Icons
- Temporary files

---

# Design Philosophy

Project Judy follows four principles:

1. Modular architecture.
2. Shared services.
3. SQLite-first design.
4. Backwards compatibility.

The objective is for Judy to continue growing without requiring rewrites of existing systems.
