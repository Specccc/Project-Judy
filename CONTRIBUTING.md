# Contributing

Contributions to Project Judy should be focused, testable, and safe for public
Discord servers.

## Workflow

1. Fork the repository and create a branch for one change.
2. Install dependencies from `requirements.txt`.
3. Keep credentials in a local `.env`; never commit secrets or runtime data.
4. Preserve server, user, and channel isolation in new storage features.
5. Test startup, affected commands, permission failures, and error handling.
6. Update documentation and `CHANGELOG.md` when behavior changes.
7. Open a pull request explaining the change and how it was tested.

Avoid unrelated rewrites in the same pull request. New AI features should use
the shared service in `ai_service.py`, and configuration belongs in `config.py`
rather than individual cogs.

Security reports must follow [SECURITY.md](SECURITY.md).
