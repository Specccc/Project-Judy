# Support

Project Judy support and bug tracking are handled through
[GitHub Issues](https://github.com/Specccc/Project-Judy/issues).

## Before Reporting a Problem

1. Run `/ping`.
2. Run `/health`.
3. If you are the bot owner, run `/diagnostics`.
4. Confirm `/setup_status` shows the intended server configuration.
5. Restart the bot once and capture the new startup output.
6. Check that the issue still occurs on the current production release.

## Include

- Project Judy version
- hosting platform and Python version
- command or action that failed
- exact error message or relevant console lines
- steps that reproduce the problem
- expected and actual behavior

Redact Discord tokens, API keys, passwords, authorization headers, private
message content, personal data, and `.env` values. Never upload an entire
runtime database or memory file to a public issue.

## Security Problems

Follow [SECURITY.md](SECURITY.md) instead of publishing exploit details or
secrets in a normal issue.
