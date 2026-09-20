# Repository Guidelines

## Project Structure & Module Organization

YOMA - Your Office Managing Architectural AI - is an independent Windows-first, local-first AI office management project. It is not LYRA and must not use LYRA branding, code, repositories, assumptions, files, or product identity.

Phase 1 implementation is approved. Runtime source lives under `src/`, tests under `tests/`, and project metadata under the repository root:

- `docs/ARCHITECTURE.md` defines the target system architecture.
- `docs/ROADMAP.md` defines phased delivery.
- `docs/SECURITY.md` defines security requirements.
- `docs/PRIVACY.md` defines privacy requirements.
- `docs/DECISIONS.md` records major architecture decisions.
- `docs/PHASE1_MILESTONE1.md` defines the implemented Phase 1 Milestone 1 boundary.

Do not add credentials, integrations, models, or cloud resources. Future source should live in `src/`, tests in `tests/`, automation in `scripts/`, and static assets in `assets/` or `public/`.

## Build, Test, and Development Commands

Use the repository's virtual environment from normal Windows PowerShell:

- `\.venv\Scripts\python.exe -m uvicorn yoma.app:app --host 127.0.0.1 --port 8765`
- `\.venv\Scripts\python.exe -m pytest`

For documentation-only changes, use:

- `git diff --check` to detect whitespace errors.
- `git status --short` to review changed files.

When a toolchain is approved, document exact build, run, lint, and test commands here.

## Coding Style & Naming Conventions

Prefer Python, FastAPI, SQLite, local filesystem storage, local indexing, and local AI provider support for the MVP. Keep architecture modular and avoid unnecessary microservices.

Use concise Markdown. Future Python code should use 4-space indentation and `snake_case`; future classes should use `PascalCase`. Never hard-code AI model names throughout the application; model IDs belong in configuration.

## Testing Guidelines

No tests exist yet because there is no runtime code. Future features require unit, integration, API, security, and regression tests matching their risk and behavior.

## Security & Privacy Rules

YOMA is local-first, private-by-design, and enterprise-scalable. Never store API keys, tokens, passwords, or OAuth credentials in source. Never allow an LLM to execute arbitrary operating-system commands. All tool execution must use an explicit allowlisted layer with authorization, verification, and audit.

Do not design covert surveillance. Do not collect microphone, camera, unrelated personal files, personal communications, or health data unless a future approved feature has consent and legal review.

## Commit & Pull Request Guidelines

There is no committed history yet. Use short imperative commit messages such as `Add architecture documentation`. Pull requests should include scope, rationale, verification performed, and security or privacy impact when relevant.

## Agent-Specific Instructions

Before editing, inspect the repository and read this file. Keep changes scoped to the user request, avoid overwriting user work, and update documentation when architecture or project rules change.
