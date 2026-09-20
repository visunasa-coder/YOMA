from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from yoma.app import create_app
from yoma.config import Settings
from yoma.db import health_check


def settings_for(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "yoma.sqlite3",
        "approved_roots": (),
        "host": "127.0.0.1",
        "port": 8765,
        "session_ttl_seconds": 3600,
        "bootstrap_username": "admin",
        "bootstrap_password": "correct horse battery staple",
        "credential_vault_path": tmp_path / "credentials.vault",
        "credential_vault_key": "test-vault-key-" + ("x" * 32),
    }
    values.update(overrides)
    return Settings(**values)


def login(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "correct horse battery staple"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_readiness_version_and_request_ids(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    client = TestClient(create_app(settings))
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "yoma-local-api"}
    assert health.headers["X-Request-ID"]
    readiness = client.get("/readyz")
    assert readiness.status_code == 200
    assert readiness.json()["components"]["database"] == "ok"
    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["application_version"] == "0.1.0"
    supplied = client.get("/healthz", headers={"X-Request-ID": "pilot-check-1"})
    assert supplied.headers["X-Request-ID"] == "pilot-check-1"
    assert health.json().get("database_path") is None
    assert health.json().get("api_key") is None
    assert health_check(settings.database_path) is True


def test_invalid_configuration_fails_closed_and_unexpected_errors_are_sanitized(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_app(settings_for(tmp_path, bootstrap_username="only-user", bootstrap_password=None))
    app = create_app(settings_for(tmp_path / "errors"))

    @app.get("/_pilot_failure")
    def pilot_failure():
        raise RuntimeError("password=do-not-leak database=C:\\private\\secret.sqlite3")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/_pilot_failure")
    assert response.status_code == 500
    assert response.json()["detail"] == "internal server error"
    assert "do-not-leak" not in response.text
    assert "secret.sqlite3" not in response.text
    assert response.headers["X-Request-ID"]


def test_bounded_end_to_end_pilot_flow(tmp_path: Path) -> None:
    root = tmp_path / "pilot-workspace"
    root.mkdir()
    source = root / "report.txt"
    source.write_text("synthetic pilot report", encoding="utf-8")
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_response = client.post("/workspace/roots", json={"path": str(root)}, headers=headers)
    assert root_response.status_code == 201
    root_id = root_response.json()["id"]
    ingest = client.post("/documents/ingest", json={"workspace_root_id": root_id, "relative_path": "report.txt"}, headers=headers)
    assert ingest.status_code == 201
    assert client.get("/documents/search", params={"q": "synthetic pilot"}, headers=headers).status_code == 200
    assert client.post("/assistant/query", json={"query": "synthetic pilot"}, headers=headers).json()["generation_status"] == "unavailable"
    conversation = client.post("/conversations", headers=headers).json()["id"]
    assert client.post("/conversations/%s/messages" % conversation, json={"content": "synthetic question"}, headers=headers).status_code == 200
    memory = client.post("/memory", json={"category": "project", "content": "pilot project", "source": "explicit pilot entry"}, headers=headers)
    assert memory.status_code == 201
    assert client.post("/memory/search", json={"query": "pilot"}, headers=headers).status_code == 200
    assert client.post("/tools/invoke", json={"tool": "workspace.file_info", "arguments": {"workspace_root_id": root_id, "relative_path": "report.txt"}}, headers=headers).status_code == 200
    read_run = client.post("/agent/runs", json={"goal": f"read file root {root_id} path: report.txt"}, headers=headers).json()
    assert client.post("/agent/runs/%s/execute" % read_run["id"], headers=headers).json()["status"] == "completed"
    write_run = client.post("/agent/runs", json={"goal": f"write text root {root_id} path: generated.txt content: synthetic output"}, headers=headers).json()
    assert write_run["status"] == "awaiting_approval"
    assert client.post("/agent/runs/%s/approve" % write_run["id"], headers=headers).status_code == 200
    assert client.post("/agent/runs/%s/execute" % write_run["id"], headers=headers).json()["status"] == "completed"
    assert (root / "generated.txt").read_text(encoding="utf-8") == "synthetic output"
    assert client.get("/integrations", headers=headers).status_code == 200
    audit = client.get("/admin/audit", headers=headers)
    assert audit.status_code == 200
    assert "synthetic output" not in audit.text
