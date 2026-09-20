# YOMA Windows production release

YOMA production releases must be built on Windows 11 with Smart App Control and other Windows code-integrity controls left enabled. This process does not add policy exceptions, change registry security settings, or use PowerShell execution-policy bypasses.

## Prerequisites

- Windows 11 x64
- Python 3.12 available through `py -3.12` or an explicit `-PythonExecutable`
- Inno Setup with `ISCC.exe` (set `YOMA_ISCC_PATH` when it is not on `PATH`)
- Windows SDK with `signtool.exe`
- Piper and Whisper model files provisioned locally and outside Git
- A legitimate production code-signing certificate with private-key access through the Windows certificate store or an approved protected signing provider
- RFC3161 timestamping: an explicit service URL for the local certificate-store path, or an RFC3161-enabled timestamp policy configured by the approved provider

For SignPath Foundation releases, the SignPath API token and project
configuration are supplied only by GitHub Actions secrets/variables. Do not
put a certificate, private key, password, API token, organization ID, or
project secret in this repository.

The self-signed `YOMA TEST Code Signing` certificate is development-only and is rejected by the release scripts.

## Clean release

From the repository root:

```powershell
$env:YOMA_PRODUCTION_SIGNING_THUMBPRINT = '<production-certificate-thumbprint>'
$env:YOMA_RFC3161_TIMESTAMP_URL = 'https://<approved-rfc3161-service>/timestamp'
$env:YOMA_SIGNTOOL_PATH = 'C:\Program Files (x86)\Windows Kits\10\bin\<sdk>\x64\signtool.exe'
.\scripts\build-release.ps1 -Version 0.55.0
```

The build creates a fresh `.release-venv` instead of using the broken historical `.venv`, installs `requirements-release.txt`, builds PyInstaller onedir outputs, stages the complete installed application, classifies YOMA-owned and upstream PE/native files, signs required YOMA artifacts, builds the Inno Setup installer from those final application files, signs the installer, verifies the final set, and creates one ZIP under `release\zip`.

The build stops if production signing credentials, SignTool, timestamping, models, Piper, or Inno Setup are unavailable.

## Individual operations

```powershell
.\scripts\sign-release.ps1 -Stage .\release\staging\app
.\scripts\verify-release.ps1 -Stage .\release\staging
.\scripts\create-release-zip.ps1 -Stage .\release\staging -Version 0.55.0
```

The final manifest is `release\staging\release-manifest.json`. It records every discovered EXE, DLL, PYD, OCX, SYS, CPL, SCR, and EFI file, with size, SHA-256, signature status, certificate identity, and timestamp verification status.

## Build modes

### Development

Development builds may be run from source using the project’s development
environment. The historical `YOMA TEST Code Signing` certificate is for local
testing only. It is prohibited by the production scripts and does not create
public Windows trust.

### Unsigned validation

The clean build can produce staging outputs for local validation, tests, and
installer-script checks. These outputs are not public releases and must not be
distributed as production artifacts.

### SignPath production release

The intended production flow is:

```text
clean GitHub-hosted build
  -> unsigned artifact upload
  -> SignPath origin verification
  -> manual release approval
  -> SignPath-signed YOMA artifacts
  -> signed-artifact verification
  -> final installer construction/signing
  -> final verification
  -> authoritative release ZIP
```

SignPath Foundation approval is not implied by this documentation. The
workflow remains fail-closed until the maintainer supplies real SignPath
configuration and the project is approved.

SignPath’s private key remains in SignPath infrastructure. The workflow must
use the official SignPath GitHub Action with `SIGNPATH_API_TOKEN` stored as a
GitHub Actions secret and project identifiers stored as configuration
variables. The local certificate-store variables below are for an approved
non-SignPath provider path only; they are not a substitute for SignPath.

Required SignPath configuration placeholders:

```text
SIGNPATH_API_TOKEN                 GitHub Actions secret
SIGNPATH_ORGANIZATION_ID           GitHub Actions variable
SIGNPATH_PROJECT_SLUG              GitHub Actions variable
SIGNPATH_SIGNING_POLICY_SLUG       GitHub Actions variable
SIGNPATH_APP_ARTIFACT_CONFIGURATION_SLUG       GitHub Actions variable
SIGNPATH_INSTALLER_ARTIFACT_CONFIGURATION_SLUG GitHub Actions variable
```

The YOMA test certificate must never be configured for any production path.
The workflow validates all six SignPath values before uploading a signing
request; empty or missing values stop the job without producing an authoritative
release.

The YOMA executable artifact configuration is a ZIP file containing the three
owned executables. The installer artifact configuration is a single PE file,
so its GitHub Actions upload uses `archive: false` and its SignPath request
uses `skip-decompress: true`. This distinction is required by the SignPath
GitHub integration and must be preserved if the workflow is changed.

For the SignPath path, the RFC3161 timestamp service and certificate are
provider-controlled signing-policy settings; they are not repository secrets
or invented workflow variables. The final verification still requires a valid
signature and timestamp (`signtool verify /pa /all /tw`) before ZIP creation.

## Packaging and Smart App Control

The application specs use PyInstaller onedir output. This keeps native dependencies as explicit files in the installed application instead of hiding them inside one-file archives that extract native payloads into temporary `_MEI` directories. Every native file in the final staging directory is therefore discoverable and must pass the signing and verification gates.

The installer copies the final staging application tree into `C:\Program Files\YOMA`, including `runtime\piper\piper.exe`. It does not copy historical releases, virtual environments, build directories, or private signing material.

A valid production signature is necessary but cannot be asserted from this repository alone. Smart App Control compatibility must be confirmed on a clean Windows 11 test system using the actual trusted production identity.

Unsigned and locally test-signed artifacts are not public production releases.
Do not install a local root certificate or create Windows policy exceptions to
make them run.

## CI/CD

The SignPath Open Source Code Signing workflow should use the supported
GitHub-hosted trusted-build path. It must upload the unsigned artifact before
submitting the request, use the official SignPath signing action, wait for the
configured approval, download the signed artifact, and verify it before any
final ZIP is created. The current local certificate-store workflow remains a
fail-closed fallback for a separately approved signing provider; it does not
represent SignPath integration.

## Troubleshooting

- Missing SignPath configuration: the workflow must stop before signing.
- Missing production certificate: `scripts/sign-release.ps1` stops; never use
  the development certificate as a fallback.
- Invalid chain or missing timestamp: verification fails and no ZIP is made.
- Unexpected native file: the PE inventory fails until the file is classified
  as YOMA-owned or an approved upstream dependency.
- Smart App Control block: record the Windows Code Integrity event and fix the
  legitimate signing/package issue. Do not disable or bypass Windows security.
- Installer mismatch: rebuild from the final verified signed application tree;
  never modify signed files after verification.
