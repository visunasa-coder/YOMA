# SignPath Foundation application brief

This brief is prepared from the current YOMA repository only. Bracketed items
are maintainer actions; they are not placeholders for values that YOMA has
claimed or that SignPath has issued.

## Application fields

| Field | Submission value or status |
|---|---|
| Project name | YOMA |
| Repository URL | `[MAINTAINER ACTION: provide the canonical public GitHub repository URL]` — no Git remote or public URL is declared in this checkout |
| Homepage URL | `[MAINTAINER ACTION: provide a public YOMA homepage URL, or confirm that the repository URL is the homepage]` |
| Download URL | `[MAINTAINER ACTION: publish docs/PUBLIC_DOWNLOAD_PAGE_DRAFT.md at the canonical public release/download URL after the first legitimately released Windows artifact exists]` |
| Privacy policy URL | `[MAINTAINER ACTION: publish docs/PRIVACY.md at a stable public URL]` — the repository contains the policy document, but no public URL is declared |
| Tagline | Windows-first, local-first office management assistant |
| Description | YOMA (Your Office Managing Architectural AI) is a Windows-first, local-first office-management application. It provides a Python/FastAPI control server, Windows service integration, a voice agent, a setup wizard, local SQLite/filesystem storage and indexing, human-governed action approval and audit boundaries, and optional configured provider integrations. |
| Reputation/evidence | Repository evidence only: source code, architecture/security/privacy documentation, automated tests, a Windows release workflow, PyInstaller onedir packaging, Inno Setup installer configuration, and checked-in SignPath artifact configurations. No user counts, downloads, customers, media coverage, or adoption claims are asserted. |
| Maintainer type | `[MAINTAINER ACTION: select and state the truthful owner type, such as individual maintainer, company, nonprofit, or educational project]` |
| Build system | GitHub Actions on `windows-latest`; Python 3.12; PyInstaller onedir; Inno Setup; SignPath GitHub Actions signing requests |

## Technical signing description

The intended release flow is:

```text
GitHub-hosted clean build
  -> tests
  -> unsigned YOMA executable artifact
  -> SignPath signing request and provider approval
  -> verified signed YOMA executables
  -> installer build
  -> SignPath installer signing request and provider approval
  -> verified signed installer
  -> manifest/checksums and authoritative ZIP
```

The repository does not contain a production certificate, private key, API
token, SignPath organization/project identifier, signing policy identifier, or
approval record. The development `YOMA TEST Code Signing` certificate is
explicitly prohibited from every production path.

## Foundation eligibility checks

SignPath Foundation's published conditions include an OSI-approved license for
all components, active maintenance, an existing release in the form to be
signed, a public page documenting the functionality, and a public code-signing
policy/privacy-policy presentation where applicable. YOMA's repository has
documentation and local release preparation, but it does not yet prove a
public repository, public release/download page, published license, or public
maintainer/team roles. These are application blockers, not facts to fill with
guesses.

YOMA's optional provider integrations and voice features can transfer or
process user-provided data when explicitly configured, so the existing privacy
policy should be published at a stable public URL and linked from the public
project/download page. If the maintainer changes the product behavior, the
policy must be reviewed again.

## Application prerequisites still requiring maintainer action

1. Publish the repository under a canonical public URL and supply the public
   homepage, download, and privacy-policy URLs.
2. Select and publish an OSI-approved license, after confirming all source,
   build scripts, dependencies, runtimes, models, and other distributed assets
   can be redistributed. See [LICENSE_AUDIT.md](LICENSE_AUDIT.md),
   [LICENSE_SELECTION.md](LICENSE_SELECTION.md), and
   [LICENSING_STATUS.md](LICENSING_STATUS.md).
3. Make at least one public release of the same Windows artifact form that
   will be submitted for signing, and publish a download page documenting its
   functionality and code-signing policy. Draft content is prepared in
   [PUBLIC_DOWNLOAD_PAGE_DRAFT.md](PUBLIC_DOWNLOAD_PAGE_DRAFT.md).
4. Identify the truthful project owner, authors/committers, reviewers, and
   signing approvers; see [MAINTAINERS.md](MAINTAINERS.md).
5. Submit this information to SignPath Foundation and complete its approval
   process.

## After approval

Store `SIGNPATH_API_TOKEN` only as a GitHub Actions secret. Store the issued
organization, project, signing-policy, executable-artifact-configuration, and
installer-artifact-configuration values only as GitHub Actions variables using
the names already consumed by
`.github/workflows/windows-release.yml`. Do not put any of these values, a
private key, or a certificate password in the repository.
