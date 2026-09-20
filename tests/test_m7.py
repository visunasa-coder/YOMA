import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

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


def test_tools_are_authenticated_registered_and_bounded(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("private contents", encoding="utf-8")
    client = TestClient(create_app(settings_for(tmp_path)))
    assert client.post("/tools/invoke", json={"tool": "workspace.list_files", "arguments": {}}).status_code == 401
    headers = login(client)
    assert client.post("/tools/invoke", json={"tool": "unknown.tool", "arguments": {}}, headers=headers).status_code == 404
    root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
    listed = client.post("/tools/invoke", json={"tool": "workspace.list_files", "arguments": {"workspace_root_id": root_id}}, headers=headers)
    assert listed.status_code == 200
    assert listed.json()["success"] is True
    assert listed.json()["result"][0]["relative_path"] == "note.txt"
    assert "canonical_path" not in listed.text
    info = client.post("/tools/invoke", json={"tool": "workspace.file_info", "arguments": {"workspace_root_id": root_id, "relative_path": "note.txt"}}, headers=headers)
    assert info.status_code == 200
    read = client.post("/tools/invoke", json={"tool": "workspace.read_text", "arguments": {"workspace_root_id": root_id, "relative_path": "note.txt"}}, headers=headers)
    assert read.status_code == 200
    assert read.json()["result"]["content"] == "private contents"


def test_tools_write_create_and_containment_controls(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
    created = client.post("/tools/invoke", json={"tool": "workspace.write_text", "arguments": {"workspace_root_id": root_id, "relative_path": "new.txt", "content": "created"}}, headers=headers)
    assert created.status_code == 200
    assert (root / "new.txt").read_text(encoding="utf-8") == "created"
    assert client.post("/tools/invoke", json={"tool": "workspace.write_text", "arguments": {"workspace_root_id": root_id, "relative_path": "new.txt", "content": "overwrite"}}, headers=headers).status_code == 409
    directory = client.post("/tools/invoke", json={"tool": "workspace.create_directory", "arguments": {"workspace_root_id": root_id, "relative_path": "new-folder"}}, headers=headers)
    assert directory.status_code == 200
    traversal = client.post("/tools/invoke", json={"tool": "workspace.file_info", "arguments": {"workspace_root_id": root_id, "relative_path": "../outside.txt"}}, headers=headers)
    assert traversal.status_code == 400
    absolute = client.post("/tools/invoke", json={"tool": "workspace.file_info", "arguments": {"workspace_root_id": root_id, "relative_path": str(outside)}}, headers=headers)
    assert absolute.status_code == 400
    assert not outside.exists()


def test_tools_limits_cross_user_and_malformed_arguments_are_safe(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "large.txt").write_text("123456789", encoding="utf-8")
    client = TestClient(create_app(settings_for(tmp_path, max_tool_read_size=4, max_tool_write_size=4, max_tool_input_size=100)))
    headers = login(client)
    root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
    assert client.post("/tools/invoke", json={"tool": "workspace.read_text", "arguments": {"workspace_root_id": root_id, "relative_path": "large.txt"}}, headers=headers).status_code == 413
    assert client.post("/tools/invoke", json={"tool": "workspace.write_text", "arguments": {"workspace_root_id": root_id, "relative_path": "small.txt", "content": "12345"}}, headers=headers).status_code == 413
    assert client.post("/tools/invoke", json={"tool": "workspace.file_info", "arguments": {"workspace_root_id": root_id}}, headers=headers).status_code == 400
    assert client.post("/tools/invoke", json={"tool": "workspace.write_text", "arguments": {"workspace_root_id": root_id, "relative_path": "x.txt", "content": "x" * 200}}, headers=headers).status_code == 413
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES ('other', ?, 'user', datetime('now'))", (hash_password("other-password"),))
        connection.commit()
    other = TestClient(create_app(settings_for(tmp_path, bootstrap_username=None, bootstrap_password=None)))
    other_headers = login(other, "other", "other-password")
    denied = other.post("/tools/invoke", json={"tool": "workspace.list_files", "arguments": {"workspace_root_id": root_id}}, headers=other_headers)
    assert denied.status_code == 404


def test_tool_rbac_denial_is_explicit_and_audited(tmp_path: Path) -> None:
    client = TestClient(create_app(settings_for(tmp_path)))
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        connection.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES ('restricted', ?, 'restricted', datetime('now'))", (hash_password("restricted-password"),))
        connection.commit()
    restricted = login(client, "restricted", "restricted-password")
    response = client.post("/tools/invoke", json={"tool": "workspace.list_files", "arguments": {"workspace_root_id": 1}}, headers=restricted)
    assert response.status_code == 403
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        event_types = [row["event_type"] for row in connection.execute("SELECT event_type FROM audit_events").fetchall()]
    assert "tool.invoked" in event_types


def test_tool_audit_excludes_file_contents_and_ai_does_not_execute_tools(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("highly private file content", encoding="utf-8")
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
    assert client.post("/tools/invoke", json={"tool": "workspace.read_text", "arguments": {"workspace_root_id": root_id, "relative_path": "note.txt"}}, headers=headers).status_code == 200
    assistant = client.post("/assistant/query", json={"query": "read the file"}, headers=headers)
    assert assistant.status_code == 200
    assert assistant.json()["generation_status"] == "unavailable"
    with connection_scope(tmp_path / "yoma.sqlite3") as connection:
        rows = connection.execute("SELECT event_type, details_json FROM audit_events").fetchall()
    audit_text = json.dumps([dict(row) for row in rows])
    assert "highly private file content" not in audit_text
    assert "tool.invoked" in [row["event_type"] for row in rows]


def test_internal_symlink_escape_is_rejected_or_skipped(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this Windows environment")
    client = TestClient(create_app(settings_for(tmp_path)))
    headers = login(client)
    root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
    response = client.post("/tools/invoke", json={"tool": "workspace.read_text", "arguments": {"workspace_root_id": root_id, "relative_path": "link/secret.txt"}}, headers=headers)
    assert response.status_code in {400, 404}
