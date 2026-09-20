# YOMA Clean-Machine Pilot Smoke Test

Use synthetic data and a fresh local database. Record only HTTP status codes and safe IDs.

1. Install Python 3.12, create `.venv`, install the project, and start Uvicorn.
2. Check `/healthz`, `/readyz`, and `/version`.
3. Log in and create an approved temporary workspace.
4. List workspace files, create a synthetic TXT file, ingest it, search it, and retrieve its metadata/text.
5. Run `/assistant/query`; with no provider configured, confirm explicit provider-unavailable behavior.
6. Create a conversation and send a synthetic message.
7. Create and search an explicit memory.
8. Invoke `workspace.list_files` or `workspace.file_info` through `/tools/invoke`.
9. Create an agent read plan. For a write plan, approve it before execution and verify the synthetic output file.
10. Confirm audit metadata contains IDs/statuses but no passwords, tokens, prompts, answers, memory text, or file content.
11. Restart YOMA and confirm conversations, memories, workspace metadata, and audit records persist.
12. If an integration is configured, verify status/disconnect behavior without using confidential external data.
13. Stop with `Ctrl+C`.

A failed readiness component or any secret/content leakage stops the pilot pending investigation.
