# Phase 1 Milestone 5 — Real AI Provider Integration

M5 connects the existing secure retrieval gateway to one real, vendor-neutral OpenAI-compatible provider boundary.

## Provider architecture

`/assistant/query` continues to authenticate the user, retrieve only authorized indexed documents, assemble bounded context, enforce policy, and audit the operation. `OpenAICompatibleProvider` is isolated in `src/yoma/provider.py`; retrieval, workspace, and document code do not depend on its HTTP protocol.

## Configuration and secrets

Configuration is environment-only:

- `YOMA_AI_PROVIDER=none` or `openai-compatible`
- `YOMA_AI_BASE_URL`
- `YOMA_AI_MODEL`
- `YOMA_AI_API_KEY`
- `YOMA_AI_TIMEOUT_SECONDS`
- `YOMA_EXTERNAL_AI_EGRESS_ENABLED=true|false`

The default provider is `none`, and external egress is disabled by default. API keys are held only in process configuration and are never stored in SQLite, responses, audits, or normal error messages.

## Trust and prompt-injection boundary

Retrieved text is bounded indexed data and is sent as explicitly labeled user data. System instructions state that retrieved text is untrusted and cannot override security policy or execute tools. This is a boundary and handling rule, not a claim of perfect prompt-injection prevention.

## Errors, citations, and audit

Timeouts, provider failures, rate limits, invalid credentials, incomplete configuration, and malformed responses return sanitized machine-readable generation states. Citations are constructed from the actual authorized retrieval sources; model-generated citation claims are not trusted. Audits contain provider/status/duration/result metadata and document IDs, never prompts, document contents, tokens, or keys.

## Non-goals and limitations

M5 adds no second provider, model download, embeddings, vector search, tool execution, autonomous control, or provider SDK. The HTTP provider has a single bounded request with no automatic retry; process isolation and perfect prompt-injection prevention are not implemented.

