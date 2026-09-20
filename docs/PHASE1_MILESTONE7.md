# Phase 1 Milestone 7 — Secure Tool Execution

M7 adds one authenticated `/tools/invoke` endpoint backed by a central registry and five explicitly bounded local workspace operations. It does not create an AI-to-tool execution chain.

## Supported tools

- `workspace.list_files`: bounded metadata discovery in an owned approved root.
- `workspace.file_info`: metadata for one contained file.
- `workspace.read_text`: bounded UTF-8 reads for `.txt`, `.md`, and `.markdown` files.
- `workspace.write_text`: creates a new text file without overwriting an existing file.
- `workspace.create_directory`: creates a contained directory without shell execution.

Unknown tools, arbitrary commands, executables, registry operations, process management, and unrestricted filesystem access are not supported.

## Authorization and filesystem boundary

The endpoint requires a bearer session and the existing RBAC allowlist. Every operation verifies the authenticated user's ownership of the workspace root, revalidates the persisted canonical root, and canonicalizes the requested relative path. Absolute paths, traversal, unavailable roots, and paths escaping the approved root are rejected. Existing workspace discovery skips links/reparse points; invocation additionally rejects reparse-point path components where they can be identified.

## Limits and audit

Environment-backed limits bound serialized tool arguments, text reads/writes, returned file metadata, and directory depth. Writes are UTF-8, create-only, and never overwrite. Tool audit events contain tool name, success/error code, and bounded result metadata; they never contain file contents, credentials, full arguments, or internal exceptions.

## Threat model and limitations

M7 assumes the local host filesystem and Python process are not already compromised. There is no process isolation or transactional filesystem rollback, and Windows reparse-point behavior can vary by filesystem/provider. A create-only write reduces overwrite risk but does not provide a general file-locking or enterprise policy engine. AI providers cannot invoke these tools implicitly; a future explicit workflow would require a separate authorization decision and audit boundary.
