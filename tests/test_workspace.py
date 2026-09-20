from pathlib import Path
import os

import pytest
from fastapi.testclient import TestClient

from yoma.app import create_app
from yoma.config import Settings
from yoma.db import connection_scope
from yoma.storage import approved_path
from yoma.workspace import WorkspacePathError, discover_files, validate_root


def make_workspace_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "yoma.sqlite3",
        approved_roots=(),
        host="127.0.0.1",
        port=8765,
        session_ttl_seconds=3600,
        bootstrap_username="admin",
        bootstrap_password="correct horse battery staple",
        credential_vault_path=tmp_path / "credentials.vault",
        credential_vault_key="test-vault-key-" + ("x" * 32),
    )
    return TestClient(create_app(settings))


def login(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "correct horse battery staple"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_workspace_root_add_list_remove_and_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    with make_workspace_client(tmp_path) as client:
        headers = login(client)
        added = client.post("/workspace/roots", json={"path": str(root / "nested" / "..")}, headers=headers)
        assert added.status_code == 201
        root_id = added.json()["id"]
        assert Path(added.json()["path"]) == root.resolve()

        listed = client.get("/workspace/roots", headers=headers)
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [root_id]

        duplicate = client.post("/workspace/roots", json={"path": str(root)}, headers=headers)
        assert duplicate.status_code == 409

        removed = client.delete(f"/workspace/roots/{root_id}", headers=headers)
        assert removed.status_code == 204
        assert client.get("/workspace/roots", headers=headers).json() == []


def test_workspace_requires_authentication(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    with make_workspace_client(tmp_path) as client:
        assert client.get("/workspace/roots").status_code == 401
        assert client.post("/workspace/roots", json={"path": str(root)}).status_code == 401


def test_workspace_file_discovery_is_metadata_only_and_audited(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    nested = root / "nested"
    nested.mkdir(parents=True)
    file_path = nested / "report.txt"
    file_path.write_text("private content", encoding="utf-8")
    with make_workspace_client(tmp_path) as client:
        headers = login(client)
        root_id = client.post("/workspace/roots", json={"path": str(root)}, headers=headers).json()["id"]
        listed = client.get("/workspace/roots", headers=headers)
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [root_id]
        response = client.get(f"/workspace/roots/{root_id}/files", headers=headers)
        assert response.status_code == 200
        assert response.json()[0]["relative_path"] == "nested/report.txt"
        assert response.json()[0]["filename"] == "report.txt"
        assert response.json()[0]["extension"] == ".txt"
        assert response.json()[0]["size"] == len("private content")
        assert "private content" not in response.text

        with connection_scope(tmp_path / "yoma.sqlite3") as connection:
            event_types = [row["event_type"] for row in connection.execute("SELECT event_type FROM audit_events").fetchall()]
        assert "workspace.root_added" in event_types
        assert "workspace.root_listed" in event_types
        assert "workspace.files_listed" in event_types


def test_workspace_rejects_invalid_roots_and_missing_root_access(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    outside = tmp_path / "outside"
    outside.mkdir()
    with make_workspace_client(tmp_path) as client:
        headers = login(client)
        assert client.post("/workspace/roots", json={"path": str(missing)}, headers=headers).status_code == 400
        assert client.post("/workspace/roots", json={"path": str(outside / ".." / "outside")}, headers=headers).status_code == 201
        assert client.get("/workspace/roots/999/files", headers=headers).status_code == 404


def test_discovery_handles_traversal_and_nonexistent_paths_safely(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()
    (root / "ok.txt").write_text("ok", encoding="utf-8")
    assert [item.relative_path for item in discover_files(root)] == ["ok.txt"]
    assert discover_files(root, max_file_size=1) == []
    with pytest.raises(WorkspacePathError):
        validate_root(tmp_path / "does-not-exist")
    with pytest.raises(PermissionError):
        approved_path(str(root / ".." / "outside.txt"), (root,))


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point behavior is Windows-specific")
def test_discovery_does_not_follow_windows_symlink_like_escape(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    assert all(item.relative_path != "link/secret.txt" for item in discover_files(root))
