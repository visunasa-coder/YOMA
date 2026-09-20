# Phase 1 Milestone 1

Milestone 1 establishes the safe local API foundation for YOMA on one Windows PC.

## Included

- FastAPI localhost service with `/healthz`.
- SQLite schema for users, sessions, and structured audit events.
- Environment-backed configuration with no secrets committed to source.
- PBKDF2 password hashing and expiring bearer sessions.
- Initial RBAC role model and explicit allowlisted tool registry.
- Canonical approved-root path validation.
- Unit tests for password verification and filesystem boundary checks.

## Deliberately deferred

Document extraction/indexing, AI provider adapters, Windows background-agent behavior, external integrations, and real DLP enforcement are not part of this milestone.

## Local security boundary

The API defaults to `127.0.0.1`. No endpoint executes shell commands, and the tool registry rejects unknown tools. Configure the bootstrap administrator only through temporary PowerShell environment variables; never commit credentials.

