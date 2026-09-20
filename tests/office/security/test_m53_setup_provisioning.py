"""M53 dedicated regression tests."""

import json
from pathlib import Path

from yoma.office.security.m53 import (
    FirstRunSetupWizard,
    GoogleProvisioningManager,
    OAuthJsonValidator,
    ProvisioningState,
    SecureProvisioningStore,
    SetupStep,
    YomaSetupService,
)


def _oauth_payload():
    return {
        "installed": {
            "client_id": "1234567890-example.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def test_m53_welcome_contains_yoma_features():
    welcome = FirstRunSetupWizard.welcome()

    assert welcome["product"] == "YOMA"
    assert "AI workplace assistant" in welcome["features"]
    assert "Google Gmail intelligence" in welcome["features"]
    assert welcome["execution_authorized"] is False
    assert welcome["executable"] is False
    assert welcome["requires_human_approval"] is True


def test_m53_validator_accepts_installed_client():
    result = OAuthJsonValidator.validate(_oauth_payload())

    assert result.valid is True
    assert result.client_type == "installed"
    assert result.has_client_id is True
    assert result.has_client_secret is True
    assert result.fingerprint


def test_m53_validator_rejects_missing_client_secret():
    payload = _oauth_payload()
    del payload["installed"]["client_secret"]

    result = OAuthJsonValidator.validate(payload)

    assert result.valid is False
    assert result.error


def test_m53_validator_rejects_invalid_shape():
    result = OAuthJsonValidator.validate(
        {"something_else": {}}
    )

    assert result.valid is False


def test_m53_file_validation(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    result = OAuthJsonValidator.validate_file(path)

    assert result.valid is True
    assert result.fingerprint


def test_m53_file_validation_rejects_non_json(tmp_path):
    path = tmp_path / "client.txt"
    path.write_text("not json", encoding="utf-8")

    result = OAuthJsonValidator.validate_file(path)

    assert result.valid is False


def test_m53_provisioning_imports_json(tmp_path):
    path = tmp_path / "google.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    result = manager.import_oauth_json(path)

    assert result.valid is True
    assert store.has_credentials()
    assert store.get_state() == ProvisioningState.VALIDATED


def test_m53_authorization_requires_valid_provisioning(tmp_path):
    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    assert manager.begin_authorization() is False
    assert manager.mark_authorized() is False


def test_m53_authorization_state(tmp_path):
    path = tmp_path / "google.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    assert manager.import_oauth_json(path).valid
    assert manager.begin_authorization() is True
    assert manager.mark_authorized() is True

    status = manager.status()

    assert status.authorization_complete is True
    assert status.execution_authorized is False
    assert status.executable is False
    assert status.requires_human_approval is True


def test_m53_connection_activation(tmp_path):
    path = tmp_path / "google.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    manager.import_oauth_json(path)
    manager.begin_authorization()
    manager.mark_authorized()

    assert manager.mark_connection_tested(True) is True

    status = manager.status()

    assert status.state == ProvisioningState.ACTIVE
    assert status.connection_tested is True


def test_m53_failed_connection_does_not_activate(tmp_path):
    path = tmp_path / "google.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    manager.import_oauth_json(path)
    manager.begin_authorization()
    manager.mark_authorized()

    assert manager.mark_connection_tested(False) is False

    status = manager.status()

    assert status.state == ProvisioningState.ERROR
    assert status.executable is False


def test_m53_status_never_exposes_secret(tmp_path):
    path = tmp_path / "google.json"
    path.write_text(
        json.dumps(_oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    manager.import_oauth_json(path)

    status = manager.status().as_dict()

    serialized = json.dumps(status)

    assert "test-secret" not in serialized
    assert "client_secret" not in serialized


def test_m53_service_facade(tmp_path):
    service = YomaSetupService(tmp_path / "store")

    assert service.execution_authorized() is False
    assert service.executable() is False
    assert service.requires_human_approval() is True

    welcome = service.welcome()

    assert welcome["product"] == "YOMA"


def test_m53_setup_step_semantics():
    assert SetupStep.WELCOME.value == "welcome"
    assert SetupStep.GOOGLE_SETUP.value == "google_setup"
    assert SetupStep.JSON_IMPORT.value == "json_import"
    assert SetupStep.AUTHORIZATION.value == "authorization"
    assert SetupStep.COMPLETE.value == "complete"


def test_m53_google_instructions_are_actionable():
    instructions = FirstRunSetupWizard.instructions()

    assert len(instructions) >= 7
    assert any("OAuth" in item for item in instructions)
    assert any("JSON" in item for item in instructions)


def test_m53_store_does_not_make_execution_authority():
    store = SecureProvisioningStore()
    manager = GoogleProvisioningManager(store)

    status = manager.status()

    assert status.execution_authorized is False
    assert status.executable is False
    assert status.requires_human_approval is True
