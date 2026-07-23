# Privacy Policy

**Last Updated:** 23 July 2026

## Scope

Project Judy is a Discord bot providing AI chat, ambient interactions,
moderation, leveling, image search, setup, and diagnostics.

## Data Processed

Depending on enabled features, Judy may process or store:

- Discord user, server, channel, and moderator IDs
- selected server configuration
- XP totals and XP-earning message counts
- moderation warnings and supplied reasons
- recent conversation text in configured chat channels
- user facts explicitly saved with `/remember`
- image search terms
- operational error and diagnostic information

Judy does not request Discord passwords, account credentials, payment data, or
private authentication tokens from users.

## AI Processing

When a user directly addresses Judy, the current message, recent channel
conversation, relevant server-scoped user memory, display name, and server name
may be sent to Google's Gemini service to generate a response.

Rare ambient AI replies may send the triggering message, display name, server
name, and reaction category to Gemini.

Server administrators can leave ambient AI behavior disabled.

## Image Search

The `/image` command may send the supplied search term to Serper. If Serper is
not configured or available, Judy uses Wikimedia Commons.

## Storage and Isolation

Operational data is stored by the service hosting Judy. SQLite records are
separated by Discord server ID. User memories are separated by both server ID
and user ID. Recent conversation history is associated with a Discord channel
ID and is limited in length.

## Data Use

Data is used to provide requested bot functions, preserve configured behavior,
maintain leveling and moderation records, generate AI responses, and diagnose
failures. Project Judy does not sell user data.

## Deletion

- `/conversation_clear` deletes the configured channel's recent conversation.
- `/forget_me` deletes the requesting user's saved facts in the current server.
- `/data_delete confirm:True` deletes Judy's stored data for the current server.
- Removing Judy from a server triggers automatic server-data cleanup.

Deletion from third-party provider logs is governed by the provider's own
retention practices.

## Security

Credentials are stored outside the public repository. Public diagnostics do not
display credential values. No internet-connected service can guarantee absolute
security.

## Changes and Contact

Policy updates are published in the Project Judy repository. Privacy requests
and reports can be submitted through:

https://github.com/Specccc/Project-Judy/issues
