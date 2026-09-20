# Phase 1 Milestone 9 — Secure Agent Planning & Orchestration

M9 adds bounded orchestration around the existing M7 tool layer. It is a deterministic planner and sequential execution engine, not unrestricted autonomous execution.

## Planning and persistence

`agent_runs` stores the authenticated owner, optional conversation association, bounded goal, lifecycle status, approval state, cancellation state, and failure category. `agent_steps` stores an inspectable plan with an allowlisted tool name, bounded arguments, status, and bounded result metadata. Planning performs no filesystem or provider operation.

The initial planner recognizes explicit goal forms such as `read file root 1 path: note.txt`, `list files root 1`, `create directory root 1 path: reports`, and `write text root 1 path: note.txt content: text`. Unrecognized goals are rejected; no arbitrary action name is accepted.

## Approval and execution

Read operations may execute when the run is planned. Writes and directory creation start as `awaiting_approval` and require owner approval. Execution is sequential and rechecks ownership, current RBAC, registry membership, argument bounds, approved-root ownership, path containment, and cancellation immediately before each step. Existing `execute_tool()` remains the sole filesystem execution authority.

Each successful write/directory operation performs bounded existence and containment verification. Read results are size-checked, but raw contents are never persisted in step result metadata or audit events. A step failure fails the run and prevents later steps; cancellation prevents future steps. There are no retries, parallel steps, recursive agents, or background workers.

## Provider, memory, and conversation boundaries

M9 does not call an AI planner or allow a provider to invoke tools. Any future provider proposal would require conversion into this explicit validated plan before execution. Agent runs may reference an owned conversation but do not automatically append execution details to it. M9 does not create memories and does not bypass the M8 memory boundary.

## Audit, limits, and limitations

Creation, planning, approval, start, step start/completion/failure, cancellation, completion, and run failure are audited using IDs, tool names, statuses, counts, and failure categories only. Goals and raw tool outputs are not copied into audit details. Environment-backed limits bound goals, steps, plan/argument sizes, execution duration, run counts, and result metadata.

The planner is intentionally narrow and string-pattern based. Execution is local and synchronous; process isolation, hard interruption of an already-running filesystem call, retries, and semantic verification are not implemented. Shell execution, arbitrary code, external integrations, automatic memory creation, and permission escalation are explicit non-goals.
