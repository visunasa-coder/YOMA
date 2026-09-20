# YOMA API Inventory

All endpoints below are local HTTP endpoints. Protected endpoints require a bearer session and the listed existing allowlisted permission; ownership is always enforced.

| Method | Path | Permission / purpose |
|---|---|---|
| GET | `/healthz` | Public liveness |
| GET | `/readyz` | Public bounded readiness |
| GET | `/version` | Public version metadata |
| POST | `/auth/login` | Public login; returns a session token |
| GET | `/auth/me` | Authenticated identity |
| GET | `/admin/audit` | `audit.read`; safe audit metadata |
| GET/POST/PATCH/DELETE | `/workspace/*`, `/documents/*`, `/memory*`, `/conversations*` | Existing M2–M8 authenticated operations and limits |
| POST | `/tools/invoke` | M7 registered local tools only |
| GET/POST | `/agent/runs*` | M9 owner-scoped planning, approval, cancellation, execution |
| GET/POST | `/integrations*` | M10 registered integration metadata/capabilities only |

Exact request and response schemas are generated at `/openapi.json`. Secrets, tokens, arbitrary URLs, raw prompts, and unrestricted external responses are not API fields.
