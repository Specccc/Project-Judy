# Security Policy

## Supported Version

Security fixes currently target Project Judy 2.0.x.

## Reporting a Vulnerability

Use GitHub's private vulnerability reporting feature if it is available for the
repository. If it is unavailable, open a minimal
[GitHub issue](https://github.com/Specccc/Project-Judy/issues) requesting a
private contact method.

Do not put exploit instructions, Discord tokens, API keys, passwords, private
user data, database contents, or other secrets in a public issue.

Include the affected version, impact, reproducible conditions, and the smallest
safe demonstration needed to understand the problem. Allow time for review and
a fix before public disclosure.

## Operator Security

- keep `.env`, databases, memory JSON, logs, and backups out of Git
- use separate production credentials and rotate any exposed secret
- grant Judy only the Discord permissions required by enabled features
- restrict owner commands to the configured owner ID
- preserve runtime data before upgrades and review dependency changes
