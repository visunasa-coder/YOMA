# YOMA Windows download page draft

This is publication-ready content, but it is not a public page and does not
create a download URL. Publish it only after the maintainer supplies the
canonical repository, homepage, privacy-policy, and release URLs.

## YOMA

YOMA (Your Office Managing Architectural AI) is a Windows-first, local-first
office-management application.

### Functionality

YOMA provides a Python/FastAPI control server, Windows service integration, a
voice agent, a setup wizard, local SQLite/filesystem storage and indexing,
human-governed action approval and audit boundaries, and optional configured
provider integrations. Voice features and external providers are optional;
when enabled, they process the data required for the authorized operation.

### Windows release

The Windows release is built on a GitHub-hosted Windows runner using Python
3.12, PyInstaller onedir outputs, and Inno Setup. The release process discovers
native files, verifies the final staging layout, and creates a release ZIP
only after legitimate production signatures and timestamp verification pass.

No public YOMA download is claimed by this draft. Unsigned and locally
test-signed artifacts are validation material, not production releases.

### Code signing policy

Free code signing provided by SignPath.io, certificate by SignPath Foundation.
YOMA has not been approved by SignPath Foundation at the time this draft was
prepared. A production release may be described as SignPath-signed only after
an approved SignPath request returns signed artifacts and the repository’s
independent verification gates pass.

The project’s release roles and required maintainer entries are documented in
[MAINTAINERS.md](MAINTAINERS.md). The detailed release procedure is in
[RELEASE_WINDOWS.md](RELEASE_WINDOWS.md).

### Privacy

See [PRIVACY.md](PRIVACY.md). YOMA stores application data locally and can
process microphone/audio input and send user-provided data to explicitly
configured external providers. The applicable provider policies must also be
reviewed when those integrations are enabled.

### Maintainer publication checklist

- Add the canonical public repository URL.
- Add the homepage and public release/download URL.
- Publish the privacy policy at a stable URL.
- Publish the selected OSI-approved project license and third-party notices.
- Replace maintainer/team placeholders with truthful project roles.
- Publish the first release in the same Windows artifact form submitted for
  signing.
