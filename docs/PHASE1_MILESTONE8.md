# Phase 1 Milestone 8 — Secure Memory & Personal Knowledge

M8 adds explicit, user-owned persistent memory. Memories are created only through `/memory`; conversation messages are never automatically promoted to memory.

## Model and APIs

SQLite stores a memory ID, owner, bounded category, content, source, importance, timestamps, optional expiration, and JSON metadata. The API provides authenticated create, list, read, update, delete, and POST search operations. Categories are limited to preference, fact, goal, instruction, project, and context. Memory IDs and all queries are parameterized and ownership-scoped.

## Security and lifecycle

Existing bearer authentication and RBAC are reused. Every read, update, delete, and search is scoped to the authenticated user. Expired memories are excluded from list, read, search, and assistant context; they may remain physically stored until explicitly deleted. Content, metadata, source, category, and importance limits are enforced without truncation. Basic credential-shaped content is rejected.

## Assistant boundary

The existing assistant pipeline performs bounded deterministic memory search using the authenticated user's query. Only matching, non-expired memories within configured count and character limits enter context. They are serialized as `user_memory_data`, separate from conversation history and retrieved document data. System instructions explicitly treat memory as untrusted application content that cannot authorize tools or override security policy. No memory is sent when no relevant match exists.

## Privacy and audit

Memory content is stored locally in SQLite for the owning user and is removed by DELETE. If an external provider is explicitly enabled by the existing M5 policy, only the bounded context—including relevant memory data—may be sent through the existing provider boundary. Audit events record IDs, categories, sources, counts, statuses, and reasons, never memory content, conversation text, credentials, prompts, or provider secrets.

## Non-goals and limitations

M8 has no embeddings, vector search, automatic memory extraction, shared memory, cloud memory, background cleanup, provider-specific memory API, or tool access. Search is deterministic SQLite LIKE matching. Credential detection is conservative pattern-based filtering rather than a complete secret scanner.
