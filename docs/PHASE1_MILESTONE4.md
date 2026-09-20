# Phase 1 Milestone 4 — Secure Retrieval & AI Gateway

M4 adds the controlled retrieval-to-provider boundary without configuring an AI vendor.

## Scope

- Authenticated retrieval from the SQLite document index.
- Revalidation of user ownership, workspace ownership, canonical roots, and document containment.
- Bounded source-bearing context assembly.
- Vendor-neutral provider contract with an explicit `none` provider.
- Authenticated `/assistant/query` orchestration and audit metadata.

## Security boundary

Retrieval uses indexed content only; a query is never treated as a filesystem path. Retrieved document text is untrusted data and is placed in explicit source blocks after system/security instructions. It cannot authorize tools, override policy, or cause OS execution.

## Provider and egress behavior

No external provider is configured in M4. The default provider returns `generation_status=unavailable` and never fabricates an answer or citations. Future providers must pass the generation egress policy before receiving context; external egress is disabled by default.

## Audit and limitations

Retrieval and generation audits record user, operation, provider, result counts, policy decisions, and document IDs without document contents. M4 does not implement embeddings, OCR, model hosting, external APIs, tool execution, or process-isolated parser execution.

