# Phase 1 Milestone 6 — Secure Conversation Layer

M6 adds a persistent local conversation boundary around the existing authenticated `/assistant/query` gateway. Conversation endpoints never read files directly and reuse the same retrieval, context, provider-policy, citation, and audit orchestration as the standalone assistant endpoint.

## Storage and ownership

SQLite stores user-owned `conversations` and ordered `messages`. Message roles are constrained to `user` and `assistant`; metadata is JSON and contains no credentials. Full message text is stored locally to support conversation history and is not copied into `audit_events`. Each conversation and message is linked to its owning user through the conversation record. Deleting a conversation cascades only to its messages; documents and workspace roots are unaffected.

## Message lifecycle

The message endpoint authenticates and verifies ownership, stores the user message, passes bounded prior message content to the existing assistant gateway, then stores the assistant result and source citation metadata. Retrieval remains limited to indexed documents authorized for the user. Conversation history is untrusted user content and cannot replace system/security instructions or retrieved-document boundaries.

Title, message, per-conversation message-count, history-message-count, and history-character limits are configurable through `YOMA_*` settings. The current implementation has no automatic retention period; users explicitly delete conversations.

## Provider, privacy, and audit boundaries

The configured provider receives only the existing bounded context plus bounded conversation history, and only when the M5 egress policy permits it. With no provider, retrieval succeeds but generation is explicitly unavailable. Audit records contain IDs, roles, provider/status, counts, and policy outcomes, never message text, prompts, document text, answers, tokens, or keys.

Prompt injection is not perfectly preventable. The enforceable boundary is structural: system instructions are a separate higher-priority provider message, while document and conversation text are serialized as untrusted data. No message can invoke tools, shell commands, or filesystem access.

## Known limitations and non-goals

M6 is local SQLite persistence with no synchronization, automated retention, editing/versioning, streaming, or multi-device conversation support. It adds no integrations, models, embeddings, vector search, telemetry, or autonomous actions.
