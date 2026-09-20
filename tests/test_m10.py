import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from yoma.app import create_app
from yoma.config import Settings
from yoma.db import connection_scope
from yoma.integrations import validate_registered_url
from yoma.security import hash_password


def settings_for(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "yoma.sqlite3",
        "approved_roots": (),
        "host": "127.0.0.1",
        "port": 8765,
        "session_ttl_seconds": 3600,
        "bootstrap_username": "admin",
        "bootstrap_password": "correct horse battery staple",
        "credential_vault_key": "test-vault-key-" + ("x" * 32),
        "credential_vault_path": tmp_path / "credentials.vault",
    }
    values.update(overrides)
    return Settings(**values)


def login(client: TestClient, username: str = "admin", password: str = "correct horse battery staple") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_integrations_are_authenticated_and_registered(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    assert client.get("/integrations").status_code == 401
    headers = login(client)
    response = client.get("/integrations", headers=headers)
    assert response.status_code == 200
    google = response.json()[0]
    assert google["integration_id"] == "google_workspace"
    assert google["enabled"] is False
    assert {item["capability_id"] for item in google["capabilities"]} == {"google.gmail.read", "google.gmail.send", "google.calendar.read", "google.calendar.create", "google.contacts.read", "google.drive.read"}
    assert client.get("/integrations/connections", headers=headers).json() == []
    assert client.get("/integrations/google_workspace/status", headers=headers).json()["status"] == "unavailable"


def test_unavailable_connect_unknown_integration_and_oauth_state_validation(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    unavailable = client.post("/integrations/google_workspace/connect", headers=headers)
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "unavailable"
    assert "client_secret" not in unavailable.text
    assert client.post("/integrations/not-registered/connect", headers=headers).status_code == 404
    invalid = client.post("/integrations/google_workspace/callback", json={"state": "bad", "code": "authorization-code"}, headers=headers)
    assert invalid.status_code == 400

    configured = TestClient(create_app(settings_for(
        tmp_path / "configured", external_integration_egress_enabled=True,
        google_oauth_client_id="client-id", google_oauth_client_secret="client-secret",
        google_oauth_redirect_uri="http://127.0.0.1:8765/oauth/callback",
    )))
    configured_headers = login(configured)
    started = configured.post("/integrations/google_workspace/connect", headers=configured_headers)
    assert started.status_code == 200
    assert started.json()["status"] == "authorization_required"
    assert "client-secret" not in started.text
    assert "client_secret" not in started.text
    callback = configured.post("/integrations/google_workspace/callback", json={"state": started.json()["state"], "code": "authorization-code"}, headers=configured_headers)
    assert callback.status_code == 200
    assert callback.json()["status"] == "unavailable"


def test_connections_are_user_owned_expire_and_disconnect_without_credentials(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    expires = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO integration_connections (id, user_id, integration_id, status, granted_scopes_json, created_at, updated_at, expires_at) VALUES ('c1', 1, 'google_workspace', 'connected', ?, datetime('now'), datetime('now'), ?)", (json.dumps(["scope"]), expires))
        connection.commit()
    connections = client.get("/integrations/connections", headers=headers)
    assert connections.status_code == 200
    assert connections.json()[0]["status"] == "expired"
    assert client.get("/integrations/google_workspace/status", headers=headers).json()["status"] == "expired"
    disconnected = client.post("/integrations/google_workspace/disconnect", headers=headers)
    assert disconnected.status_code == 200
    assert client.get("/integrations/connections", headers=headers).json() == []


def test_capability_boundary_rejects_unknown_urls_egress_and_missing_connection(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    unknown = client.post("/integrations/google_workspace/capabilities/google.unknown", json={"arguments": {}}, headers=headers)
    assert unknown.status_code == 404
    missing = client.post("/integrations/google_workspace/capabilities/google.gmail.read", json={"arguments": {}}, headers=headers)
    assert missing.status_code == 503
    arbitrary = client.post("/integrations/google_workspace/capabilities/google.gmail.read", json={"arguments": {"url": "https://evil.example"}}, headers=headers)
    assert arbitrary.status_code == 400
    assert validate_registered_url("google_workspace", "https://www.googleapis.com/gmail/v1/users/me/messages") is True
    assert validate_registered_url("google_workspace", "https://evil.example") is False


def test_capability_requires_connection_scope_and_read_only_reference_is_bounded(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, external_integration_egress_enabled=True)
    client = TestClient(create_app(settings))
    headers = login(client)
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO integration_connections (id, user_id, integration_id, status, granted_scopes_json, created_at, updated_at) VALUES ('c1', 1, 'google_workspace', 'connected', ?, datetime('now'), datetime('now'))", (json.dumps(["not-the-required-scope"]),))
        connection.commit()
    denied = client.post("/integrations/google_workspace/capabilities/google.gmail.read", json={"arguments": {}}, headers=headers)
    assert denied.status_code == 403
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("UPDATE integration_connections SET granted_scopes_json = ? WHERE id = 'c1'", (json.dumps(["https://www.googleapis.com/auth/gmail.readonly"]),))
        connection.commit()
    unavailable = client.post("/integrations/google_workspace/capabilities/google.gmail.read", json={"arguments": {"max_results": 100000}}, headers=headers)
    assert unavailable.status_code == 413


def test_connection_and_audit_metadata_never_expose_secrets(tmp_path: Path) -> None:
    secret = "client-secret-never-log"
    client = TestClient(create_app(settings_for(tmp_path, google_oauth_client_secret=secret)))
    headers = login(client)
    client.post("/integrations/google_workspace/connect", headers=headers)
    audit = client.get("/admin/audit", headers=headers)
    assert secret not in audit.text
    assert "access_token" not in audit.text
    assert "refresh_token" not in audit.text
