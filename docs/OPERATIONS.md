# YOMA Pilot Operations

## Start and stop

Run the project-local Python executable with Uvicorn on `127.0.0.1`. Stop with `Ctrl+C`; do not terminate the process while a write is in progress. `/healthz` checks liveness, `/readyz` checks database readiness and reports optional provider/integration availability, and `/version` reports the local release identifier.

## Data locations

The SQLite path is controlled by `YOMA_DATABASE_PATH` or defaults under `YOMA_DATA_DIR`. Approved workspace files remain outside the YOMA database. The database contains local identity/session metadata, audit records, indexed document text, conversations, memories, agent records, and integration metadata.

## Troubleshooting

- `401`: authenticate with a valid bearer session.
- `403`: the role is not allowlisted for the operation.
- `404`: the resource is not owned by the authenticated user or does not exist.
- `409`: approval, connection, or lifecycle state prevents the operation.
- `413`: a configured request/resource bound was exceeded.
- Provider/integration unavailable: confirm explicit configuration and egress policy; optional services must not prevent local startup.

Do not enable debug output or paste environment variables, tokens, prompts, or document contents into support logs.
