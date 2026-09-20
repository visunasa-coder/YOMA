# YOMA Privacy Policy

This document describes behavior evidenced by the current YOMA source. It is not legal advice. The project maintainer must review it for the jurisdictions and deployment environments in which YOMA is distributed.

## Local data

YOMA stores application state in local SQLite/filesystem storage. Depending on the enabled features, local data can include:

- user accounts, password hashes, sessions, and authentication audit records;
- documents and extracted/indexed content supplied through approved workspace paths;
- conversations, memory, operational records, and workflow/audit metadata;
- configuration, logs, runtime state, and service/health information;
- encrypted integration credentials and OAuth token material in the local credential vault;
- voice-agent input and generated audio while the voice features are used.

The application includes authorization, ownership checks, bounded document access, audit recording, and approval controls. Local retention and deletion behavior depends on the configured deployment and the relevant application workflows; operators must define retention periods before production use.

## Microphone and voice behavior

The source contains microphone/audio abstractions and a voice agent. Microphone or audio data is not a claim-free “no data collection” area: when voice functionality is enabled and used, the application can process voice input locally and can invoke the configured speech/voice runtime. Users should be informed before enabling those features.

## External network behavior

YOMA does not have a single unconditional “never network” behavior. The source contains optional, explicitly configured network integrations including:

- Google OAuth authorization and Google Workspace APIs for Gmail, Calendar, Contacts, and Drive;
- an OpenAI-compatible provider path for configured AI services;
- configured integration/provider endpoints;
- local browser navigation to the local Control Server.

External integration egress is configuration-controlled and is intended to fail closed when required configuration is absent. When a user enables an external provider, data needed for that authorized operation may leave the device and is subject to that provider’s privacy terms. The operator must configure only endpoints and scopes approved for the deployment.

## Credentials and secrets

The source uses environment/configuration inputs for bootstrap credentials, provider API keys, OAuth client settings, and vault configuration. OAuth and integration credentials are intended to be stored in the local encrypted credential vault. Secrets must not be committed to the repository or included in release artifacts.

## Telemetry and analytics

No standalone telemetry or analytics service was identified in the reviewed YOMA source. Operational logs, audit events, health information, and application records are still local data and can contain sensitive metadata. They must be protected and retained according to the deployment policy.

## User-generated and organizational content

Users or administrators may provide documents, workspace paths, messages, and operational data. YOMA’s authorization and containment controls are intended to limit access to approved data, but operators remain responsible for configuring approved roots, integrations, permissions, and retention.

## Third-party services and components

Google services, configured AI providers, Piper, Whisper-related components, and Python native dependencies have their own terms and privacy policies. A production distribution must include an accurate third-party notice and must link the applicable provider policies when those integrations are enabled.

## Maintainer release obligation

Before public distribution, the maintainer must review this document against the exact release, complete the deployment-specific disclosures, and ensure that the installer and public download page make the privacy policy available to users.
