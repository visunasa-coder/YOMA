# YOMA Architecture

## Executive Architecture Summary

YOMA - Your Office Managing Architectural AI - is a Windows-first, local-first AI office management and intelligence system. YOMA is an independent project and must not use LYRA branding, code, repositories, assumptions, files, or product identity.

The MVP architecture is a modular monolith running on a normal Windows PC. It should use a local Windows background agent, a secure local API, SQLite, local filesystem storage, local indexing, and a local AI runtime through a provider abstraction. Hosted cloud infrastructure must remain optional, not required.

The same boundaries must support later growth from one PC to a small office server, enterprise cluster, private data center, and optional hybrid integrations.

## Component Architecture

- **Windows Agent:** Windows-compatible background process for local user interaction, endpoint state, notifications, and safe calls into the Local API.
- **Local API:** FastAPI-based localhost service for application actions, health, admin operations, retrieval, and integration coordination.
- **AI Provider Abstraction:** Interface for local AI, optional cloud AI, and offline fallback. Model identifiers are configuration, never scattered constants.
- **AI Orchestration:** Plans user requests, retrieves context, calls AI providers, applies policy, and follows `PLAN -> SHOW INTENT -> AUTHORIZATION -> EXECUTE -> VERIFY -> AUDIT`.
- **Retrieval/Search:** Local search and indexing over approved organizational content with source metadata.
- **Document Intelligence:** `Document -> Validation -> Extraction -> Normalization -> Indexing -> Retrieval -> AI Context -> Response`.
- **Local Data Layer:** SQLite for MVP metadata, policy state, audit records, indexes, and configuration pointers. Files remain on local storage unless explicitly synced later.
- **Authentication:** Local secure session model for MVP, extensible to enterprise identity.
- **Authorization/RBAC:** Role and permission checks for every sensitive action.
- **Workplace Integrations:** Adapter interfaces for Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, Zoho, and Microsoft 365 using official APIs and OAuth.
- **Security/DLP:** Policy engine, audit events, tool allowlists, sensitivity classification, and future transfer decisioning.
- **Audit/Observability:** Structured logs, health, errors, latency, resource failures, and security events without secrets or unnecessary sensitive content.
- **Configuration:** Local configuration files plus secure secret storage. No API keys in source.
- **Administration:** Local admin views and future enterprise administration APIs.
- **Future Enterprise Control Plane:** Optional on-premise or private cloud layer for fleet policy, identity integration, device registration, audit aggregation, and update coordination.

## Data Flow

For assistant responses, the user request enters the Windows Agent or local UI, is authenticated by the Local API, authorized by RBAC, evaluated by orchestration, enriched by retrieval, sent to the selected AI provider, and returned with source attribution where applicable.

For document intelligence, YOMA validates file type, size, path, and permissions before extraction. Extracted content is normalized, indexed with source references, retrieved by query, and supplied as bounded AI context. YOMA must not invent document contents.

For actions such as sending email, deleting files, external transfers, permission changes, policy changes, financial actions, or organizational record updates, orchestration must show intent and require explicit authorization before execution.

## Trust Boundaries

Key trust boundaries are the user session, local API, local filesystem, AI provider, integration adapters, future enterprise control plane, and external SaaS APIs. Data crossing a boundary requires authentication, authorization, validation, auditability, and least-privilege access. Security-sensitive failures must fail closed.

## Local-First Design

The MVP must operate on one Windows PC without a hosted backend. Core functions should continue with local files, SQLite metadata, local search, and local AI. External APIs, cloud AI, and enterprise services are optional extensions. If a network provider is unavailable, core local search, local document intelligence, and offline fallback behavior should remain available.

## External Integration Boundaries

Integrations must be isolated behind adapters. Each adapter owns OAuth, API clients, rate-limit handling, provider-specific errors, and permission scopes. The core system consumes normalized capabilities and must not depend on one provider being present.

Adapters must use official APIs, least-privilege scopes, secure token storage, retry/backoff, and explicit user or admin consent. Provider outages degrade features but must not break local operation.

## Scalability Model

YOMA scales by preserving component boundaries:

- **PC:** Agent, API, SQLite, local search, local AI, and local admin run together.
- **Office Server:** Shared indexing, policy, audit, and optional AI compute move to an office node.
- **Enterprise Cluster:** Identity, storage, audit, policy, integration sync, and AI compute become independently scalable services.
- **Private Data Center:** Control plane, data residency, high availability, observability, and enterprise security controls operate on private infrastructure.

Endpoint processing, office/edge processing, enterprise control plane, AI compute, storage, identity, and security must remain separable.

## Deployment Model

Phase 1 targets a single Windows PC. Later deployments may add an office server, private enterprise services, or optional hybrid/cloud integrations. No design should assume one workstation will serve thousands of users.

Enterprise deployments should support private/on-premise infrastructure first, with optional hybrid connections where an organization approves them.

## Failure Handling

YOMA must handle local AI unavailability with offline fallback or clear degraded responses. Integration failures should be isolated, retried when safe, and reported without blocking local features. Database lock or corruption scenarios require safe errors and recovery paths. Document parser failures must quarantine the failed item and preserve auditability.

Security, authorization, policy, and secret-store failures must fail closed. Logs must capture structured diagnostics without passwords, tokens, API keys, or unnecessary content.
