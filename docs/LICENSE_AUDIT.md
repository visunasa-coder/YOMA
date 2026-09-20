# YOMA repository license audit

This is a factual inventory of licensing evidence visible in the current
checkout. It is not legal advice and does not grant a license. SignPath
Foundation requires an OSI-approved license and legally redistributable
components; the maintainer must complete the legal review before publication.

## Repository findings

- No root `LICENSE`, `LICENSE.txt`, `COPYING`, or `NOTICE` file exists.
- `pyproject.toml` has no license declaration.
- No canonical GitHub remote is configured, so public repository status and
  public licensing history cannot be verified from this checkout.
- `README.md`, `docs/`, `src/`, `scripts/`, `installer/`, workflow files, and
  release specifications are present, but repository authorship does not by
  itself establish legal ownership of every contribution.

## Component classification

| Area | Evidence in checkout | Audit status |
|---|---|---|
| YOMA Python source | `src/` and project metadata | Appears to be YOMA application source, but maintainer must confirm copyright/ownership and contributors’ rights |
| YOMA tests and documentation | `tests/`, `docs/`, `README.md` | Appears project-authored; ownership and third-party contribution status require maintainer confirmation |
| Release/build/installer code | `scripts/`, `installer/`, `*.spec`, `.github/` | Appears project-authored; must be included in the ownership and license review because SignPath treats build inputs as part of provenance |
| Python dependencies | `requirements-release.txt` and `pyproject.toml` | Names and versions are declared; individual package licenses and notice obligations are not verified by this checkout |
| Piper runtime | `runtime/piper/piper.exe` and bundled Piper-related files in staging | Redistributable rights and corresponding notices are not established locally; maintainer must verify upstream terms and exact binary provenance |
| Speech/voice models | `models/` and `models/MODEL-MANIFEST.json` | Model files are present, but model licenses, terms, attribution, and redistribution rights are not established locally |
| Whisper/Vosk/Piper model assets | `models/whisper`, `models/vosk-model-small-en-us-0.15`, `models/piper` | Separate upstream terms must be identified and confirmed for distribution; they must not be covered automatically by a YOMA license |
| Native dependencies | DLLs/PYDs and other native files in build/staging trees | Provenance and license/notice obligations require dependency-level review; no blanket YOMA ownership claim is made |
| Installer components | Inno Setup-generated installer and bundled PowerShell installer scripts | Script ownership requires maintainer confirmation; Inno Setup redistribution terms and any embedded components require review |
| Fonts/assets/examples | No project-wide license/notice inventory was found | Contents and redistribution terms require maintainer review before publication |
| Generated/local material | `build/`, `dist/`, `release/`, local environments, caches, audio/test files, historical ZIPs, and temporary milestone directories | Must remain outside the public source release unless individually reviewed; these are not license evidence |

## What is verified locally

The checkout verifies only the following:

1. The declared Python dependency names and pinned release versions.
2. The existence of the Piper executable and model/resource trees used by the
   release staging process.
3. The presence of release documentation and SignPath artifact configurations.
4. The absence of a root project license or a repository license declaration.

The checkout does not verify the legal terms of third-party packages, model
weights, Piper binaries, native libraries, fonts, or generated artifacts.

## Maintainer confirmation required

Before selecting and publishing a project license, the maintainer must:

1. Confirm who owns or is authorized to license each YOMA-authored source,
   test, documentation, build, workflow, installer, and specification file.
2. Review contributor history and obtain any needed copyright assignments or
   permissions.
3. Produce a dependency and third-party notice inventory from the exact
   release environment, including Python packages and native dependencies.
4. Verify redistribution rights, attribution requirements, model terms, and
   restrictions for Piper, Whisper, Vosk, voice models, and every bundled
   runtime/native asset.
5. Review Inno Setup and all installer-distributed components.
6. Decide whether MIT, Apache-2.0, or another OSI-approved license matches the
   project’s legal and patent requirements, then publish the complete license
   text at the repository root.
7. Exclude unreviewed generated files, local data, test audio, credentials,
   local environments, caches, and historical release archives from the public
   source repository.

Until these steps are complete, YOMA must not be represented as an
OSI-licensed project or as eligible for SignPath Foundation signing on the
basis of an assumed license.
