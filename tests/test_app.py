from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from yoma.app import create_app
from yoma.config import Settings
from yoma.db import connection_scope
from yoma.security import hash_password, verify_password


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "yoma.sqlite3",
        approved_roots=(tmp_path,),
        host="127.0.0.1",
        port=8765,
        session_ttl_seconds=3600,
        bootstrap_username="admin",
        bootstrap_password="correct horse battery staple",
        credential_vault_path=tmp_path / "credentials.vault",
        credential_vault_key="test-vault-key-" + ("x" * 32),
    )
    return TestClient(create_app(settings))


def test_login_and_authenticated_me_use_request_scoped_connections(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        login = client.post("/auth/login", json={"username": "admin", "password": "correct horse battery staple"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json() == {"id": 1, "username": "admin", "role": "admin"}


def test_me_rejects_missing_or_invalid_authentication(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/auth/me").status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_login_rejects_incorrect_password_and_audits_attempt(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/auth/login", json={"username": "admin", "password": "wrong password"})
        assert response.status_code == 401

    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        event = connection.execute(
            "SELECT event_type, details_json FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert event["event_type"] == "auth.login_failed"
        assert "wrong password" not in event["details_json"]


def test_malformed_invalid_and_expired_tokens_are_rejected_and_audited(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/auth/me").status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Bearer a b"}).status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401

        login = client.post("/auth/login", json={"username": "admin", "password": "correct horse battery staple"})
        token = login.json()["access_token"]

    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("UPDATE sessions SET expires_at = ?", ("not-a-timestamp",))
        connection.commit()

    with make_client(tmp_path) as client:
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
        with connection_scope(tmp_path / "yoma.sqlite3") as connection:
            event_types = [row["event_type"] for row in connection.execute("SELECT event_type FROM audit_events").fetchall()]
        assert "auth.missing" in event_types
        assert "auth.malformed_token" in event_types
        assert "auth.invalid_token" in event_types
        assert "auth.expired_session" in event_types


def test_rbac_protects_audit_endpoint_and_records_denial(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        with connection_scope(tmp_path / "yoma.sqlite3") as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("user", hash_password("user password that is long"), "user"),
            )
            connection.commit()

        user_login = client.post("/auth/login", json={"username": "user", "password": "user password that is long"})
        user_response = client.get("/admin/audit", headers={"Authorization": f"Bearer {user_login.json()['access_token']}"})
        assert user_response.status_code == 403

        admin_login = client.post("/auth/login", json={"username": "admin", "password": "correct horse battery staple"})
        admin_response = client.get("/admin/audit", headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"})
        assert admin_response.status_code == 200

    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        assert connection.execute("SELECT 1 FROM audit_events WHERE event_type = 'authz.denied'").fetchone() is not None


def test_bootstrap_is_idempotent_and_does_not_replace_existing_credentials(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "yoma.sqlite3",
        approved_roots=(tmp_path,),
        host="127.0.0.1",
        port=8765,
        session_ttl_seconds=3600,
        bootstrap_username="admin",
        bootstrap_password="correct horse battery staple",
        credential_vault_path=tmp_path / "credentials.vault",
        credential_vault_key="test-vault-key-" + ("x" * 32),
    )
    create_app(settings)
    create_app(replace(settings, bootstrap_password="different password that is long"))

    with connection_scope(settings.database_path) as connection:
        users = connection.execute("SELECT username, password_hash, role FROM users").fetchall()
        assert len(users) == 1
        assert users[0]["username"] == "admin"
        assert users[0]["role"] == "admin"
        assert verify_password("correct horse battery staple", users[0]["password_hash"])
        assert not verify_password("different password that is long", users[0]["password_hash"])
