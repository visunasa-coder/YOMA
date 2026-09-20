# YOMA Architectural Decisions

## Decision 1: YOMA Is Independent

**Decision:** YOMA is an independent project: Your Office Managing Architectural AI. It must not use LYRA branding, code, repositories, assumptions, files, or product identity.

**Rationale:** A clean identity and architecture prevent accidental coupling and product confusion.

## Decision 2: Local-First Is Mandatory

**Decision:** YOMA must run initially on a normal Windows PC without a hosted backend.

**Rationale:** Local operation supports privacy, offline resilience, low startup cost, and private enterprise adoption.

## Decision 3: Windows-First MVP

**Decision:** The MVP targets Windows with a Windows-compatible background agent.

**Rationale:** The mission is office management on normal Windows PCs, so endpoint behavior, filesystem access, notifications, and local security must be designed for Windows first.

## Decision 4: Modular Monolith Before Services

**Decision:** The MVP should be a modular monolith with clear internal boundaries, not unnecessary microservices.

**Rationale:** A modular monolith reduces operational overhead while preserving paths to later office and enterprise deployments.

## Decision 5: Python, FastAPI, SQLite, and Local Storage for MVP

**Decision:** Prefer Python, FastAPI, SQLite, local filesystem storage, and local indexing for the MVP unless a specific technical reason requires otherwise.

**Rationale:** These choices are simple, Windows-compatible, testable, and sufficient for a single-PC local assistant.

## Decision 6: AI Provider Abstraction

**Decision:** YOMA must not be tightly coupled to one AI provider. It must support local AI, optional cloud AI, and offline fallback through an abstraction.

**Rationale:** Provider independence protects privacy, cost control, availability, and enterprise deployment flexibility. Model names belong in configuration, not scattered through code.

## Decision 7: External Integrations Use Adapters

**Decision:** Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, Zoho, and Microsoft 365 integrations must be isolated through adapters and official APIs.

**Rationale:** Adapter boundaries keep core YOMA behavior stable when providers change or become unavailable.

## Decision 8: Security Is a Foundational Subsystem

**Decision:** Authentication, authorization, RBAC, validation, secure secrets, audit, safe errors, and security tests are core architecture, not later add-ons.

**Rationale:** YOMA will handle workplace data and potentially security-sensitive actions, so controls must exist from the beginning.

## Decision 9: LLMs Cannot Execute Arbitrary OS Commands

**Decision:** YOMA must never allow an LLM to execute arbitrary operating-system commands. All execution must use an explicit allowlisted tool layer.

**Rationale:** Prompt injection and model error are expected risks. Tool calls need typed inputs, authorization, policy checks, verification, and audit.

## Decision 10: Sensitive Actions Require Authorization

**Decision:** Destructive or external actions follow `PLAN -> SHOW INTENT -> AUTHORIZATION -> EXECUTE -> VERIFY -> AUDIT`.

**Rationale:** Sending email, deleting content, transferring files, changing permissions, modifying policies, financial actions, and organizational record changes must not be autonomous.

## Decision 11: Document Intelligence Must Be Grounded

**Decision:** Document answers must follow validation, extraction, normalization, indexing, retrieval, AI context, and source-attributed response.

**Rationale:** YOMA must not invent document contents. Source attribution makes answers reviewable.

## Decision 12: DLP and Physical Security Start as Simulations or Interfaces

**Decision:** DLP enforcement and physical security are future capabilities. MVP work must simulate security-sensitive OS enforcement and physical security events until explicitly approved.

**Rationale:** Real enforcement and surveillance-adjacent systems create safety, legal, privacy, and trust risks that require staged validation.

## Decision 13: Enterprise Scale Uses Clear Boundaries

**Decision:** YOMA should scale from PC to office server, enterprise cluster, and private data center by separating endpoint processing, office/edge processing, control plane, AI compute, storage, identity, and security.

**Rationale:** One workstation cannot serve thousands of users, but the same architecture can grow if responsibilities remain separable.
