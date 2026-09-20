import json
from pathlib import Path

from fastapi.testclient import TestClient

from yoma.app import create_app
from yoma.config import Settings
from yoma.db import connection_scope
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
        "credential_vault_path": tmp_path / "credentials.vault",
        "credential_vault_key": "test-vault-key-" + ("x" * 32),
    }
    values.update(overrides)
    return Settings(**values)


def login(client: TestClient, username: str = "admin", password: str = "correct horse battery staple") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def approved_root(client: TestClient, headers: dict[str, str], root: Path) -> int:
    response = client.post("/workspace/roots", json={"path": str(root)}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_agent_read_plan_executes_sequentially_and_is_bounded(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("private content", encoding="utf-8")
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_id = approved_root(client, headers, root)
    created = client.post("/agent/runs", json={"goal": f"read file root {root_id} path: note.txt"}, headers=headers)
    assert created.status_code == 201
    run = created.json()
    assert run["status"] == "planned"
    assert run["steps"][0]["tool_name"] == "workspace.read_text"
    executed = client.post("/agent/runs/%s/execute" % run["id"], headers=headers)
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"
    assert executed.json()["steps"][0]["status"] == "completed"
    assert "private content" not in executed.text


def test_agent_writes_require_approval_and_verify_result(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_id = approved_root(client, headers, root)
    created = client.post("/agent/runs", json={"goal": f"write text root {root_id} path: created.txt content: hello"}, headers=headers)
    run = created.json()
    assert created.status_code == 201
    assert run["status"] == "awaiting_approval"
    assert client.post("/agent/runs/%s/execute" % run["id"], headers=headers).status_code == 409
    assert client.post("/agent/runs/%s/approve" % run["id"], headers=headers).json()["status"] == "planned"
    executed = client.post("/agent/runs/%s/execute" % run["id"], headers=headers)
    assert executed.json()["status"] == "completed"
    assert (root / "created.txt").read_text(encoding="utf-8") == "hello"
    assert "hello" not in executed.text


def test_agent_authentication_and_cross_user_isolation(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    assert client.get("/agent/runs").status_code == 401
    headers = login(client)
    run = client.post("/agent/runs", json={"goal": "list files"}, headers=headers).json()
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES ('other', ?, 'user', datetime('now'))", (hash_password("other-password"),))
        connection.commit()
    other = TestClient(create_app(settings_for(tmp_path, bootstrap_username=None, bootstrap_password=None)))
    other_headers = login(other, "other", "other-password")
    assert other.get("/agent/runs", headers=other_headers).json() == []
    assert other.get("/agent/runs/%s" % run["id"], headers=other_headers).status_code == 404
    assert other.post("/agent/runs/%s/cancel" % run["id"], headers=other_headers).status_code == 404


def test_agent_rbac_is_enforced(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES ('restricted', ?, 'restricted', datetime('now'))", (hash_password("restricted-password"),))
        connection.commit()
    restricted = login(client, "restricted", "restricted-password")
    assert client.post("/agent/runs", json={"goal": "list files"}, headers=restricted).status_code == 403


def test_agent_limits_failure_cancellation_and_audit_safety(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path, max_agent_goal_length=10, max_agent_steps=1)))
    headers = login(client)
    assert client.post("/agent/runs", json={"goal": "this goal is too long"}, headers=headers).status_code == 413
    run = client.post("/agent/runs", json={"goal": "list files"}, headers=headers).json()
    assert client.post("/agent/runs/%s/cancel" % run["id"], headers=headers).json()["status"] == "cancelled"
    assert client.post("/agent/runs/%s/execute" % run["id"], headers=headers).status_code == 409
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        rows = connection.execute("SELECT event_type, details_json FROM audit_events").fetchall()
    assert {"agent.created", "agent.plan_created", "agent.cancelled"}.issubset({row["event_type"] for row in rows})
    assert "this goal is too long" not in json.dumps([dict(row) for row in rows])


def test_agent_rejects_invalid_planned_arguments_and_unknown_tampered_tool(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    invalid = client.post("/agent/runs", json={"goal": "read file"}, headers=headers).json()
    failed = client.post("/agent/runs/%s/execute" % invalid["id"], headers=headers)
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    tampered = client.post("/agent/runs", json={"goal": "list files"}, headers=headers).json()
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("UPDATE agent_steps SET tool_name = 'unknown.tool' WHERE agent_run_id = ?", (tampered["id"],))
        connection.commit()
    unknown = client.post("/agent/runs/%s/execute" % tampered["id"], headers=headers)
    assert unknown.json()["status"] == "failed"
