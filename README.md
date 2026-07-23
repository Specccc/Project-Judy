# Project Judy

Project Judy is a personality-driven Discord bot built with Python and
`discord.py`. It combines character chat, server-scoped memory, ambient
presence, moderation, leveling, image search, diagnostics, and owner tools.

Current version: **2.0.0**

Release status: **Production Stable** — deployed and verified on ACLClouds on
23 July 2026.

## 2.0 Highlights

- One Gemini client and request pipeline shared by every AI feature
- Central system prompt and model configuration
- Bounded AI concurrency, timeouts, retries, input limits, and diagnostics
- Server-scoped user memories
- Per-user and per-server chat cooldowns
- Public `/setup`, `/help`, `/invite`, `/privacy`, `/terms`, and `/support`
- Server data deletion through `/data_delete`
- Automatic cleanup when Judy leaves a server
- Centralized paths, database files, limits, colors, URLs, and version metadata

## Features

- Directed character chat with recent channel history
- Persistent user facts isolated by Discord server
- Optional ambient reactions, short replies, and GIF responses
- XP, ranks, and server leaderboards
- Moderation warnings, timeouts, kicks, bans, and message purging
- Image search through Serper with Wikimedia Commons fallback
- Public health checks and private owner diagnostics
- Owner-only status, reload, sync, activity, and shutdown commands

## Project Layout

```text
Project-Judy/
├── assets/                 # Curated ambient response data
├── cogs/                   # Discord commands and event systems
├── memory/                 # Memory manager; runtime JSON is ignored
├── prompts/                # Central AI system prompt
├── ai_service.py           # Unified Gemini request pipeline
├── config.py               # Central configuration
├── data_service.py         # Server-data deletion
├── database.py             # Core database bootstrap
├── guild_service.py        # Public-server setup state
├── main.py                 # Startup and cog loading
└── requirements.txt
```

Secrets, runtime databases, memory caches, logs, local packages, and hosting
artifacts are excluded from Git.

## Requirements

- Python 3.11+
- Discord bot application
- Google Gemini API key
- Optional Serper API key for richer image search

## Installation

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`.

3. Add credentials:

   ```dotenv
   DISCORD_TOKEN=
   GEMINI_API_KEY=
   SERPER_API_KEY=
   ```

4. Enable the Server Members and Message Content privileged gateway intents in
   the Discord Developer Portal.

5. Start Judy:

   ```bash
   python main.py
   ```

6. In Discord, run `/setup`.

Never commit `.env` or share its contents.

## Main Commands

- Setup: `/setup`, `/setup_status`, `/help`, `/invite`
- Chat: `/chatmode_on`, `/chatmode_off`, `/chatmode_status`,
  `/conversation_clear`
- Memory: `/remember`, `/memories`, `/forget_me`
- Ambient: `/ambient_on`, `/ambient_off`, `/ambient_status`,
  `/ambient_ignore`, `/ambient_allow`, `/ambient_preview`
- XP: `/rank`, `/leaderboard`
- Images: `/image`
- Moderation: `/warn`, `/warnings`, `/clear_warnings`, `/timeout`,
  `/untimeout`, `/kick`, `/ban`, `/unban`, `/purge`
- System: `/ping`, `/health`, `/privacy`, `/terms`, `/support`,
  `/data_delete`
- Owner: `/diagnostics`, `/owner_status`, `/owner_cogs`, `/owner_reload`,
  `/owner_sync`, `/owner_activity`, `/owner_activity_clear`,
  `/owner_shutdown`

## Upgrade and Hosting

See [DEPLOYMENT.md](DEPLOYMENT.md) before replacing a running ACLClouds
installation.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)
- [Deployment](DEPLOYMENT.md)
- [Privacy Policy](privacy-policy.md)
- [Terms of Service](terms-of-service.md)
- [Support](SUPPORT.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Public Use

Before adding Judy to a community, review the Privacy Policy and Terms of
Service. Server administrators can run `/setup` to configure Judy, `/help` to
view commands, `/support` for assistance, and `/data_delete confirm:True` to
remove data stored for their server.

Bug reports and non-sensitive support requests belong in
[GitHub Issues](https://github.com/Specccc/Project-Judy/issues). Do not include
bot tokens, API keys, passwords, private message content, or other secrets.

## License

Project Judy is licensed under the [MIT License](LICENSE).

Created by Specccc.
