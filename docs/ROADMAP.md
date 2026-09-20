# YOMA Roadmap

## Roadmap Principles

YOMA grows from a local Windows assistant into an enterprise-capable workplace intelligence layer. Later phases must not be implemented until their prerequisites are met and explicitly approved. No phase may depend on a mandatory hosted backend.

## Phase 0 - Foundation

**Objectives:** Define architecture, security, privacy, roadmap, and decisions. Establish YOMA as an independent project with no LYRA identity or code assumptions.

**Prerequisites:** Empty repository baseline and approved documentation scope.

**Acceptance Criteria:** Architecture documents are internally consistent, local-first, Windows-first, private-by-design, enterprise-scalable, and contain no runtime implementation.

**Dependencies:** Repository documentation only.

**Risks:** Overdesigning future enterprise systems before validating the local MVP.

## Phase 1 - Local Assistant MVP

**Objectives:** Build a single-PC Windows MVP with a Windows-compatible agent, FastAPI local API, SQLite metadata, local filesystem storage, local search/indexing, AI provider abstraction, local AI priority, document intelligence for initial file types, audit logs, authentication, RBAC, and safe tool execution.

**Prerequisites:** Phase 0 approval, selected Python packaging approach, selected local AI runtime, selected document extraction libraries, and test strategy.

**Acceptance Criteria:** A user can run YOMA locally, authenticate, index approved files, ask document-grounded questions with source attribution, and execute only allowlisted actions after explicit authorization. Unit, API, integration, regression, and security tests cover MVP behavior.

**Dependencies:** Python, FastAPI, SQLite, local storage, local AI runtime such as Ollama, Windows development environment.

**Risks:** Local model quality, resource usage, document parsing complexity, and user trust around file access.

## Phase 2 - Workplace Integrations

**Objectives:** Add isolated adapters for Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, Zoho services, and Microsoft 365 services as approved. Support email prioritization, summarization, task extraction, deadline extraction, meeting preparation, and workflow assistance.

**Prerequisites:** Stable auth, RBAC, audit, integration adapter interface, secure secret handling, and explicit consent flows.

**Acceptance Criteria:** Each integration uses official APIs, OAuth, least-privilege scopes, provider isolation, and graceful degradation when unavailable. Sending email, deleting content, external transfers, and record changes require explicit authorization.

**Dependencies:** External provider APIs, OAuth registration, token storage, rate-limit handling, and integration tests.

**Risks:** API changes, consent gaps, data exposure, provider outages, and confusing cross-provider semantics.

## Phase 3 - Security/DLP

**Objectives:** Add sensitivity classification, policy evaluation, external transfer detection, removable-media event modeling, allow/deny/warn decisions, and security audit events. MVP enforcement remains simulated until real OS enforcement is proven safe.

**Prerequisites:** Mature audit pipeline, RBAC, file event modeling, policy store, admin review workflows, and security tests.

**Acceptance Criteria:** DLP simulations classify content, evaluate policies, produce decisions, and emit audit events without real destructive or blocking OS enforcement.

**Dependencies:** Security policy engine, classification rules, event sources, admin UI/API, and test fixtures.

**Risks:** False positives, false negatives, legal constraints, workplace trust, and unsafe enforcement.

## Phase 4 - Multi-User Enterprise

**Objectives:** Support 100-user, 1,000-user, and 10,000+ user deployments through office/edge processing, centralized identity, shared policy, audit aggregation, admin roles, and scalable storage boundaries.

**Prerequisites:** Proven MVP, migration strategy from SQLite/local storage, enterprise identity integration, tenant/org model, and operational monitoring.

**Acceptance Criteria:** Multiple users can operate under RBAC, centralized policies, auditable actions, isolated permissions, and documented capacity assumptions.

**Dependencies:** Identity provider integration, shared databases, queueing or job orchestration, enterprise observability, and admin tooling.

**Risks:** Scale complexity, data migration, latency, policy drift, and operational burden.

## Phase 5 - Private Enterprise Infrastructure

**Objectives:** Provide private/on-premise enterprise deployment with control plane, fleet management, policy distribution, audit retention, private AI compute, high availability, and optional hybrid/cloud integrations.

**Prerequisites:** Validated multi-user architecture, enterprise security review, deployment automation, backup/restore, and disaster recovery design.

**Acceptance Criteria:** Enterprise customers can deploy YOMA without public cloud dependency while preserving local-first privacy, RBAC, auditability, and provider abstraction.

**Dependencies:** Private infrastructure, enterprise storage, observability stack, identity systems, model hosting, and security operations.

**Risks:** Infrastructure cost, configuration drift, compliance burden, incident response complexity, and AI compute capacity.
