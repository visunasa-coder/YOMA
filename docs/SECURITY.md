# YOMA Security

## Threat Model

YOMA protects organizational work data, personal data encountered incidentally, credentials, audit records, AI context, indexes, and policy decisions. Primary threats include unauthorized local access, privilege escalation, prompt injection, unsafe tool execution, data exfiltration through integrations, credential theft, path traversal, command injection, SQL injection, malicious documents, dependency compromise, denial of service, and excessive logging.

Security-sensitive actions must fail closed.

## Trust Boundaries

Trust boundaries include the Windows user session, Windows Agent, Local API, SQLite database, local filesystem, AI provider, integration adapters, secret store, admin interface, and future enterprise control plane. Every boundary crossing requires validation, authentication where applicable, authorization, and auditability.

## Authentication

The MVP should use a secure local authentication model appropriate for a single Windows PC. Future deployments must support enterprise identity such as directory or SSO integration. Local APIs must not be exposed broadly by default and should bind to localhost unless explicitly configured otherwise.

## Authorization

RBAC is required for sensitive capabilities. Suggested roles include user, admin, security admin, auditor, and integration service account. Authorization checks must protect file access, search scope, integration actions, security events, policy changes, admin operations, and external transfers.

## Secrets

Secrets must never be stored in source code, logs, indexes, or plain text configuration. OAuth tokens, API keys, and local credentials must use OS-backed secure storage or an approved enterprise secret store. Configuration should reference secret names, not secret values.

## Tool Execution

YOMA must never allow an LLM to execute arbitrary operating-system commands. All tool execution must go through an explicit allowlisted tool layer with typed inputs, policy checks, authorization, validation, bounded side effects, verification, and audit logging.

Destructive or external actions require the action model: `PLAN -> SHOW INTENT -> AUTHORIZATION -> EXECUTE -> VERIFY -> AUDIT`. The system must reject unknown tools, malformed inputs, overbroad scopes, and missing authorization.

## File Security

File access must be limited to approved roots and authorized data categories. Implement canonical path resolution, path traversal prevention, extension and MIME validation, file size limits, parser isolation where practical, safe temporary file handling, and clear errors. Document extraction must treat files as untrusted input.

SQL access must use parameterized queries or safe ORM/query APIs. Shell invocation should be avoided; where unavoidable, use fixed commands with validated arguments and no LLM-controlled command strings.

## DLP Architecture

Future DLP components include sensitivity classification, policy evaluation, external transfer detection, removable-media event modeling, allow/deny/warn decisions, and security audit events. For the MVP, security-sensitive OS enforcement must be simulated and tested before real enforcement is attempted.

DLP decisions should include subject, object, action, policy, decision, reason, timestamp, and reviewer path where applicable.

## Audit Requirements

Audit logs must record authentication events, authorization decisions, admin changes, integration connections, security events, DLP decisions, tool executions, external actions, and policy changes. Logs must be structured, tamper-resistant in future enterprise deployments, and avoid passwords, tokens, API keys, and unnecessary sensitive content.

## Rate Limiting and Abuse Controls

Local APIs should apply rate limiting where appropriate for login, expensive AI calls, document ingestion, integration sync, and administrative actions. Resource exhaustion should produce safe degraded behavior and observable events.

## Security Testing

Security tests must cover authentication, authorization, RBAC, path traversal, input validation, SQL injection prevention, command injection prevention, unsafe tool rejection, secret redaction, DLP simulation, prompt-injection resistance for tool use, and safe error handling.

No feature should be declared complete without appropriate unit, integration, API, regression, and security tests for its risk level.
