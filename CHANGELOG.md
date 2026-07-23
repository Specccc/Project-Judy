# Changelog

All notable changes to Project Judy are documented here.

## v2.0.0 — Unified AI Core

### Added

- Unified Gemini request service
- Central system prompt
- AI concurrency limits, timeouts, retries, and latency statistics
- Chat-level user and server cooldowns
- Server-scoped memory keys
- Automatic single-server migration of legacy user memories
- AI-core information in health and owner diagnostics

### Changed

- Chat and ambient systems now use the shared AI service
- Prompt construction moved out of individual cogs
- AI input is length-bounded and stored context is explicitly untrusted
- Bot version and documentation updated to 2.0.0

## v1.9.0 — Public-Server Readiness

### Added

- `/setup` and `/setup_status`
- `/help`, `/invite`, `/privacy`, `/terms`, and `/support`
- `/data_delete` for administrator-controlled server-data removal
- Per-server setup database
- Permission validation during setup
- Automatic server-data cleanup when Judy leaves a guild
- Deployment and upgrade documentation

### Changed

- Public command documentation now matches the implemented command set
- Privacy policy now identifies stored data, providers, retention, and deletion
- Terms now cover permissions, AI output, moderation responsibility, and abuse

## v1.7.0 — Pre-2.0 Stabilization

### Added

- Character chat with channel history
- Persistent user-memory commands
- Ambient reactions, replies, and GIFs
- XP ranks and leaderboards
- Image search with fallback
- Moderation and owner commands
- Public health and private diagnostics

### Changed

- Centralized paths, settings, limits, models, colors, and version metadata
- Empty placeholder cogs are skipped cleanly
- Hosting artifacts and runtime data are excluded from Git

## v1.3.0 — Migration Build

- Migrated Project Judy from Replit to GitHub and ACLClouds
- Added the modular project foundation
