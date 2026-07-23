# ACLClouds Deployment

Project Judy 2.0.0 was successfully deployed and production-tested on
ACLClouds on 23 July 2026.

These instructions also apply to the 2.1 identity and relationship upgrade.

## Preserve Runtime Data

Before uploading 2.1, keep the existing:

- `.env`
- `database/`
- `memory/conversation_cache.json`
- `memory/judy_memory.json`

Do not replace those items with repository files.

## Deploy

1. Stop the ACLClouds server.
2. Upload the 2.1 repository files into `/home/container`.
3. Replace matching source files and folders.
4. Leave `.env`, `database/`, and runtime memory JSON files intact.
5. Confirm the Startup Main File is `main.py`.
6. Start the server.

The requirements file no longer needs the legacy `google-generativeai` package.
ACLClouds may leave that package installed; it is unused.

## First Startup

The first startup automatically:

- creates `guilds.db`
- creates `identity.db` with profile and relationship tables
- adds any missing database tables
- migrates legacy user-memory keys when Judy is currently installed in one
  server
- loads all non-empty cogs
- synchronizes global slash commands

Global Discord commands may take time to refresh in clients.

The successful production deployment synchronized 43 global slash commands.

## Release Test

Run in order:

1. `/ping`
2. `/health`
3. `/diagnostics`
4. `/setup`
5. Address Judy in the configured chat channel
6. `/remember`
7. `/memories`
8. `/ambient_preview`
9. `/profile`
10. `/relationship`
11. `/set_name`
12. Address Judy again and confirm the preferred name is used naturally
13. `/rank`
14. `/image`
15. One reversible moderation test
16. `/setup_status`

The production release passed this validation sequence. Repeat it after source,
dependency, environment, or hosting changes.

Do not test `/data_delete` on the production server unless the stored server
data is intentionally being removed.

## Rollback

If startup fails:

1. Stop the server.
2. Restore the previous source files.
3. Keep the existing `.env`, databases, and memory files.
4. Start the previous version.
5. Preserve the failed console output for diagnosis.
