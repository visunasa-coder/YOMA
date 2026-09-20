# Phase 1 Milestone 11 — Pilot & Production Readiness

M11 prepares the verified M1–M10 local API for controlled Windows pilot validation. It adds safe configuration validation, request correlation, operational logging, readiness/version endpoints, database health checks, deployment guidance, and recovery documentation. It does not make YOMA a public production service.

## Safe defaults

YOMA binds to `127.0.0.1`, requires bearer authentication for protected operations, keeps external AI/integration egress disabled, uses environment configuration for credentials, and returns sanitized unexpected errors with a request ID. Optional providers and integrations may be unavailable without preventing local startup.

## Operational controls

`/healthz` is a lightweight liveness check. `/readyz` reports bounded database, configuration, provider, and integration statuses without paths or secrets. `/version` reports only application/API/build identifiers. Middleware adds a bounded `X-Request-ID`, rejects oversized request bodies, and logs only method/path/status/request ID/duration.

## Data and recovery

SQLite contains identity, sessions, audit metadata, workspace metadata, indexed document text, conversations, memories, agent plans, and integration connection metadata. It never contains provider/OAuth tokens or secrets. Back up the SQLite database while YOMA is stopped; workspace files are separate and must be backed up independently. Restoring metadata does not restore workspace files, and resetting YOMA metadata must never delete approved workspace files.

M11 means ready for controlled pilot validation. It does not provide public hosting, distributed storage, cloud backup, enterprise SSO, process isolation, or unrestricted network access.
