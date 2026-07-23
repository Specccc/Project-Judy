# Project Judy Architecture

## Runtime Flow

`main.py` validates configuration, initializes storage, loads non-empty cogs,
connects to Discord, synchronizes slash commands, and publishes the current
version in Judy's activity.

`config.py` is the source of truth for project paths, database locations,
credentials, models, AI controls, feature limits, cooldowns, public URLs,
colors, and version metadata.

## Unified AI Core

`ai_service.py` owns all Gemini access.

The service provides:

- one configured Gemini client
- one central system prompt
- chat and ambient prompt construction
- global concurrency control
- request timeouts
- bounded retries with delay
- input truncation
- empty-response handling
- request, failure, and latency diagnostics

Chat and ambient cogs no longer create their own Gemini clients.

For direct chat, the AI service also receives bounded server-scoped identity
and relationship context from `identity_service.py`. Scores and internal tiers
are context only and must not be exposed in normal conversation.

## Identity and Relationships

`identity_service.py` stores profiles and relationship state in
`database/identity.db`.

Each Discord server has an independent profile for a user. Direct interactions
update:

- current Discord display name
- optional user-controlled preferred name
- first and last interaction times
- direct interaction count
- bounded trust, familiarity, and affinity scores
- a derived relationship tier

Progression is deterministic, gradual, and clamped. It does not use a second AI
request or allow one message to create a high-trust relationship.

## Public-Server Setup

`guild_service.py` stores setup state in `database/guilds.db`.

`cogs/utility.py` provides:

- `/setup`
- `/setup_status`
- `/help`
- `/invite`
- `/privacy`
- `/terms`
- `/support`
- `/data_delete`

Setup validates channel permissions, configures the chat channel, optionally
enables ambient presence, updates live cog state, and persists the result.

## Persistence

Runtime SQLite databases:

- `judy.db`: core bootstrap
- `guilds.db`: setup state
- `chat.db`: configured chat channel per server
- `ambient.db`: ambient settings and ignored channels
- `xp.db`: server-isolated XP
- `moderation.db`: server-isolated warnings
- `identity.db`: server-isolated profiles and relationships

The memory manager stores recent channel conversations and server-scoped user
facts in JSON. A one-server legacy installation automatically converts old
unscoped user-memory keys during the first 2.0 startup.

## Data Isolation and Deletion

Server-specific records include a Discord guild ID. User facts, profiles, and
relationships are keyed by guild ID and user ID.

`data_service.py` removes configuration, chat settings, ambient settings, XP,
warnings, user memory, identity state, and known channel conversations when:

- an administrator confirms `/data_delete`
- Judy is removed from a server

## Cog Responsibilities

- `chat.py`: direct conversation routing and recent context
- `memory.py`: user-controlled server-scoped memories
- `identity.py`: profile, preferred-name, and relationship commands
- `ambient.py`: passive reactions, replies, and GIFs
- `xp.py`: XP, ranks, and leaderboards
- `images.py`: external image search
- `moderation.py`: warnings and moderation actions
- `utility.py`: setup, help, install, legal, support, and deletion
- `diagnostics.py`: health and private operational inspection
- `owner.py`: owner-only runtime administration

## Security Boundaries

- Secrets are loaded from `.env`.
- Safe diagnostics expose only whether credentials are loaded.
- User content sent to Gemini is bounded in length.
- Conversation and memory text is treated as context rather than authority.
- Bot-generated replies suppress mentions.
- Public setup checks channel permissions before enabling chat.
- Source control excludes credentials and runtime user data.
