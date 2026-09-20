"""YOMA M53 - Enterprise enrollment and first-run provisioning."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class ProvisioningState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    ORGANIZATION_PENDING = "organization_pending"
    JSON_IMPORTED = "json_imported"
    VALIDATED = "validated"
    AUTHORIZATION_PENDING = "authorization_pending"
    AUTHORIZED = "authorized"
    CONNECTION_TESTED = "connection_tested"
    ACTIVE = "active"
    ERROR = "error"


class SetupStep(str, Enum):
    WELCOME = "welcome"
    ORGANIZATION = "organization"
    GOOGLE_SETUP = "google_setup"
    JSON_IMPORT = "json_import"
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    CONNECTION_TEST = "connection_test"
    COMPLETE = "complete"


@dataclass(frozen=True)
class OAuthValidationResult:
    valid: bool
    client_type: str | None
    has_client_id: bool
    has_client_secret: bool
    has_redirect_uris: bool
    fingerprint: str | None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "client_type": self.client_type,
            "has_client_id": self.has_client_id,
            "has_client_secret": self.has_client_secret,
            "has_redirect_uris": self.has_redirect_uris,
            "fingerprint": self.fingerprint,
            "error": self.error,
        }


class OAuthJsonValidator:
    @staticmethod
    def validate(payload: Mapping[str, Any]) -> OAuthValidationResult:
        try:
            if not isinstance(payload, Mapping):
                raise ValueError("OAuth configuration must be a JSON object.")

            client = payload.get("installed") or payload.get("web")

            if not isinstance(client, Mapping):
                raise ValueError(
                    "OAuth JSON must contain an 'installed' or 'web' client."
                )

            client_id = client.get("client_id")
            client_secret = client.get("client_secret")

            if not isinstance(client_id, str) or not client_id.strip():
                raise ValueError("OAuth client_id is missing.")

            if not isinstance(client_secret, str) or not client_secret.strip():
                raise ValueError("OAuth client_secret is missing.")

            redirects = client.get("redirect_uris", [])
            if redirects is None:
                redirects = []

            if not isinstance(redirects, list):
                raise ValueError("redirect_uris must be a list.")

            client_type = "installed" if payload.get("installed") else "web"

            canonical = json.dumps(
                {
                    "client_id": client_id,
                    "client_type": client_type,
                    "redirect_uris": redirects,
                },
                sort_keys=True,
                separators=(",", ":"),
            )

            fingerprint = hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest()[:16]

            return OAuthValidationResult(
                valid=True,
                client_type=client_type,
                has_client_id=True,
                has_client_secret=True,
                has_redirect_uris=bool(redirects),
                fingerprint=fingerprint,
            )

        except Exception as exc:
            return OAuthValidationResult(
                False,
                None,
                False,
                False,
                False,
                None,
                str(exc),
            )

    @classmethod
    def validate_file(cls, path: str | Path) -> OAuthValidationResult:
        try:
            p = Path(path)

            if not p.exists():
                return OAuthValidationResult(
                    False, None, False, False, False, None,
                    "OAuth JSON file does not exist.",
                )

            if p.suffix.lower() != ".json":
                return OAuthValidationResult(
                    False, None, False, False, False, None,
                    "OAuth configuration must be a .json file.",
                )

            payload = json.loads(
                p.read_text(encoding="utf-8-sig")
            )

            return cls.validate(payload)

        except json.JSONDecodeError:
            return OAuthValidationResult(
                False, None, False, False, False, None,
                "The selected file is not valid JSON.",
            )
        except Exception as exc:
            return OAuthValidationResult(
                False, None, False, False, False, None,
                str(exc),
            )


class SecureProvisioningStore:
    """Provisioning persistence boundary.

    The public API intentionally never returns secrets.
    Windows production packaging should protect the resulting directory
    using the existing M48 host ACL/secret mechanisms.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(
            root or (Path.home() / ".yoma" / "provisioning")
        )
        self.root.mkdir(parents=True, exist_ok=True)

        self.credential_file = self.root / "google_oauth.secure.json"
        self.state_file = self.root / "setup_state.json"

    def save_oauth_payload(
        self,
        payload: Mapping[str, Any],
        fingerprint: str,
    ) -> None:
        data = {
            "provider": "google",
            "fingerprint": fingerprint,
            "payload": dict(payload),
        }

        fd, temporary = tempfile.mkstemp(
            prefix=".yoma_google_",
            suffix=".tmp",
            dir=str(self.root),
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

            os.replace(temporary, self.credential_file)

            try:
                os.chmod(self.credential_file, 0o600)
            except OSError:
                pass

        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def save_state(self, state: ProvisioningState) -> None:
        temporary = self.state_file.with_suffix(".tmp")

        temporary.write_text(
            json.dumps(
                {
                    "provider": "google",
                    "state": state.value,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        os.replace(temporary, self.state_file)

        try:
            os.chmod(self.state_file, 0o600)
        except OSError:
            pass

    def has_credentials(self) -> bool:
        return self.credential_file.exists()

    def get_state(self) -> ProvisioningState:
        if not self.state_file.exists():
            return ProvisioningState.NOT_CONFIGURED

        try:
            data = json.loads(
                self.state_file.read_text(encoding="utf-8")
            )
            return ProvisioningState(data["state"])
        except Exception:
            return ProvisioningState.ERROR


@dataclass(frozen=True)
class ProvisioningStatus:
    state: ProvisioningState
    setup_step: SetupStep
    google_configured: bool
    oauth_json_validated: bool
    authorization_complete: bool
    connection_tested: bool
    credentials_securely_stored: bool
    execution_authorized: bool = False
    executable: bool = False
    requires_human_approval: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "setup_step": self.setup_step.value,
            "google_configured": self.google_configured,
            "oauth_json_validated": self.oauth_json_validated,
            "authorization_complete": self.authorization_complete,
            "connection_tested": self.connection_tested,
            "credentials_securely_stored": self.credentials_securely_stored,
            "execution_authorized": False,
            "executable": False,
            "requires_human_approval": True,
        }


class GoogleProvisioningManager:
    def __init__(self, store: SecureProvisioningStore | None = None):
        self.store = store or SecureProvisioningStore()
        self._validated = False
        self._authorized = False
        self._connection_tested = False

        state = self.store.get_state()

        if state in {
            ProvisioningState.AUTHORIZED,
            ProvisioningState.CONNECTION_TESTED,
            ProvisioningState.ACTIVE,
        }:
            self._validated = True
            self._authorized = True

    def import_oauth_json(
        self,
        path: str | Path,
    ) -> OAuthValidationResult:
        result = OAuthJsonValidator.validate_file(path)

        if not result.valid:
            self.store.save_state(ProvisioningState.ERROR)
            return result

        payload = json.loads(
            Path(path).read_text(encoding="utf-8-sig")
        )

        self.store.save_oauth_payload(
            payload,
            result.fingerprint or secrets.token_hex(8),
        )

        self._validated = True
        self.store.save_state(ProvisioningState.VALIDATED)

        return result

    def begin_authorization(self) -> bool:
        if not self._validated or not self.store.has_credentials():
            return False

        self.store.save_state(
            ProvisioningState.AUTHORIZATION_PENDING
        )
        return True

    def mark_authorized(self) -> bool:
        if not self._validated or not self.store.has_credentials():
            return False

        self._authorized = True
        self.store.save_state(
            ProvisioningState.AUTHORIZED
        )
        return True

    def mark_connection_tested(self, success: bool) -> bool:
        if not self._authorized:
            return False

        self._connection_tested = bool(success)

        self.store.save_state(
            ProvisioningState.ACTIVE
            if success
            else ProvisioningState.ERROR
        )

        return bool(success)

    def status(self) -> ProvisioningStatus:
        state = self.store.get_state()

        if state == ProvisioningState.ACTIVE:
            step = SetupStep.COMPLETE
        elif state in {
            ProvisioningState.AUTHORIZED,
            ProvisioningState.CONNECTION_TESTED,
        }:
            step = SetupStep.CONNECTION_TEST
        elif state == ProvisioningState.AUTHORIZATION_PENDING:
            step = SetupStep.AUTHORIZATION
        elif state == ProvisioningState.VALIDATED:
            step = SetupStep.AUTHORIZATION
        elif state == ProvisioningState.JSON_IMPORTED:
            step = SetupStep.VALIDATION
        else:
            step = SetupStep.WELCOME

        return ProvisioningStatus(
            state=state,
            setup_step=step,
            google_configured=self.store.has_credentials(),
            oauth_json_validated=self._validated or state in {
                ProvisioningState.VALIDATED,
                ProvisioningState.AUTHORIZATION_PENDING,
                ProvisioningState.AUTHORIZED,
                ProvisioningState.ACTIVE,
            },
            authorization_complete=self._authorized,
            connection_tested=self._connection_tested,
            credentials_securely_stored=self.store.has_credentials(),
        )


class FirstRunSetupWizard:
    FEATURES = (
        "AI workplace assistant",
        "Google Gmail intelligence",
        "Google Calendar",
        "Google Contacts",
        "Google Drive",
        "Knowledge and document intelligence",
        "Attendance and integration support",
        "Enterprise security monitoring",
        "Enterprise data protection",
        "Governed AI automation",
    )

    GOOGLE_STEPS = (
        "Create or select the organization's Google Cloud project.",
        "Configure the Google OAuth consent screen.",
        "Enable the required Google Workspace APIs.",
        "Create an OAuth Client ID.",
        "Download the OAuth client JSON.",
        "Select the JSON file in YOMA.",
        "YOMA validates and provisions the configuration.",
        "YOMA opens the browser for administrator authorization.",
        "YOMA verifies the resulting Google connection.",
    )

    @classmethod
    def welcome(cls) -> dict[str, Any]:
        return {
            "product": "YOMA",
            "title": "Welcome to YOMA Enterprise",
            "features": list(cls.FEATURES),
            "google_setup": list(cls.GOOGLE_STEPS),
            "execution_authorized": False,
            "executable": False,
            "requires_human_approval": True,
        }

    @classmethod
    def instructions(cls) -> list[str]:
        return list(cls.GOOGLE_STEPS)
