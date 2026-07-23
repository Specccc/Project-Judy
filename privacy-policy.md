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
- preferred names, interaction counts, and server-scoped relationship scores
- image search terms
- operational error and diagnostic information

Judy does not request Discord passwords, account credentials, payment data, or
private authentication tokens from users.

## AI Processing

When a user directly addresses Judy, the current message, recent channel
conversation, relevant server-scoped user memory, display name, and server name
may be sent to Google's Gemini service to generate a response.

Rare ambient AI replies may send the triggering message, display name, server
name, and reaction category to Gemini. Server administrators can leave ambient
AI behavior disabled.

## Image Search

The `/image` command may send the supplied search term to Serper. If Serper is
not configured or available, Judy uses Wikimedia Commons. Search providers may
receive the search term and ordinary connection metadata needed to complete the
request.

## Storage, Isolation, and Retention

Operational data is stored by the service hosting Judy. SQLite records are
separated by Discord server ID. User memories are separated by both server ID
and user ID. Recent conversation history is associated with a Discord channel
ID and is limited to the latest 20 entries per channel.

Retention depends on the data type:

- recent conversation entries remain until displaced by newer entries, cleared
  with `/conversation_clear`, deleted with `/data_delete`, or removed when Judy
  leaves the server
- saved user facts remain until `/forget_me`, `/data_delete`, or server removal
- profiles and relationship state remain until `/forget_me`, `/data_delete`, or
  server removal
- XP, warnings, and server configuration remain until `/data_delete` or server
  removal
- operational logs and backups, if any, follow the host operator's retention
  and deletion processes

## Data Use

Data is used to provide requested bot functions, preserve configured behavior,
maintain leveling and moderation records, generate AI responses, and diagnose
failures. Project Judy does not sell user data.

## Third-Party Services

Judy relies on third parties to provide parts of the service:

- [Discord](https://discord.com/privacy) supplies messages, interactions,
  identities, servers, channels, and permission information required by the bot
- [Google Gemini](https://policies.google.com/privacy) receives the AI inputs
  described above and returns generated responses
- [Serper](https://serper.dev/privacy), when configured, receives image-search
  terms
- [Wikimedia Commons](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy)
  may receive fallback image-search requests
- ACLClouds hosts the running bot and its operational files

Those services process information under their own policies. Project Judy
cannot directly control or delete copies retained in third-party systems.

## Deletion

- `/conversation_clear` deletes the configured channel's recent conversation.
- `/forget_me` deletes the requesting user's saved facts in the current server.
- `/forget_me` also deletes the requesting user's profile and relationship
  state in the current server.
- `/data_delete confirm:True` deletes Judy's stored data for the current server.
- Removing Judy from a server triggers automatic server-data cleanup.

Deletion from third-party provider logs is governed by the provider's own
retention practices. A deletion request only affects data controlled by the
Project Judy deployment.

## Security

Credentials are stored outside the public repository. Public diagnostics do not
display credential values. No internet-connected service can guarantee absolute
security.

## Changes and Contact

Material policy updates are published in the Project Judy repository. Continued
use after an update means the revised policy applies to future use. Privacy
requests and reports can be submitted through:

https://github.com/Specccc/Project-Judy/issues
