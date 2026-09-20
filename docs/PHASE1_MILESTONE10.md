# Phase 1 Milestone 10 — Secure External Integrations

M10 adds a vendor-neutral integration registry, user-owned connection metadata, OAuth state handling, and capability authorization. It deliberately does not add a generic HTTP client or a live Google token exchange.

## Registry and connection lifecycle

`src/yoma/integrations.py` defines registered integrations and capabilities. The initial reference is `google_workspace` with bounded read-only Gmail, Calendar, and Contacts capability definitions. `integration_connections` stores only user ownership, integration ID, status, granted-scope metadata, timestamps, and expiration. OAuth access tokens, refresh tokens, authorization codes, client secrets, and API keys are never stored.

The integration APIs list registered integrations, list owned connection metadata, begin OAuth authorization, validate callback state, disconnect, report status, and invoke a registered capability boundary. Google remains safely unavailable unless explicit environment configuration and egress policy are enabled; even then M10 does not perform a token exchange.

## Security and egress

Authentication and existing RBAC are required. Connection and capability access is scoped to the authenticated user. OAuth state is generated in process, bound to user/integration, expires after ten minutes, and is consumed once. Redirect and authorization hosts are fixed registered values; user-provided URLs, endpoints, hosts, and URIs are rejected. External egress is disabled by default and no capability performs an outbound request in M10.

Capabilities are explicit, bounded, and classified read/write. Read capabilities require a connected owned connection and the required granted scope. Writes are approval-gated by default. Providers and agents cannot invoke integration capabilities directly; a future integration operation must pass the existing authorization and approval boundaries.

## Privacy, trust, and audit

External responses are treated as untrusted data and are not persisted to memory, conversations, or the document index. Audit events contain only integration IDs, capability IDs, statuses, scope decisions, and bounded reasons. They never contain tokens, authorization codes, secrets, email bodies, contact data, calendar descriptions, or full external responses.

## Limitations and non-goals

M10 has no live Google API client, token vault, refresh handling, synchronization, arbitrary URL access, autonomous email/calendar writes, browser automation, or external-data persistence. A future client must be registered per integration, enforce host and egress policy, bound responses, sanitize external content, and require approval for writes.
