# YOMA

YOMA (Your Office Managing Architectural AI) is a Windows-first, local-first office-management application. The repository contains a Python/FastAPI control server, a Windows service wrapper, a voice agent, a setup wizard, local storage and indexing components, optional provider integrations, and a Piper voice runtime.

## Current status

This checkout is being prepared for a legitimate public Windows release. It is not currently a SignPath Foundation-approved project and no release in this repository should be represented as SignPath-signed.

The repository currently has no declared open-source license. Until the maintainer selects and publishes an OSI-approved license, this source must not be redistributed as an approved open-source release.

## Functionality

- Local FastAPI control server and Windows service integration.
- Human-governed actions with authentication, authorization, audit records, and approval boundaries.
- Local SQLite/filesystem storage and document indexing.
- Optional Google Workspace OAuth/API integrations when explicitly configured.
- Optional OpenAI-compatible or other configured AI providers.
- Optional microphone and voice-agent functionality using the bundled Piper runtime.

Optional integrations can transmit user-provided data to the configured provider. See [Privacy](docs/PRIVACY.md).

## Development and validation

The Windows release process is documented in [RELEASE_WINDOWS.md](docs/RELEASE_WINDOWS.md). It uses a clean Python 3.12 environment, PyInstaller onedir outputs, native-file discovery, signature verification, Inno Setup, and a deterministic release ZIP.

The release pipeline fails closed when production signing is unavailable. The development certificate named `YOMA TEST Code Signing` is never accepted as a production identity.

## Code signing policy

See [CODE_SIGNING_POLICY.md](docs/CODE_SIGNING_POLICY.md). The intended production arrangement is free code signing provided by SignPath.io, certificate by SignPath Foundation, subject to application approval and maintainer configuration. Approval has not been granted for this repository at the time of writing.
The factual application brief is documented in [SIGNPATH_APPLICATION.md](docs/SIGNPATH_APPLICATION.md).
License preparation and the repository-wide audit are documented in [LICENSE_SELECTION.md](docs/LICENSE_SELECTION.md) and [LICENSE_AUDIT.md](docs/LICENSE_AUDIT.md); no project license has been granted yet.

## Security

YOMA is intended to run with Windows Smart App Control, Defender, Code Integrity, and other Windows security controls enabled. The release process does not create policy exceptions or security bypasses.
