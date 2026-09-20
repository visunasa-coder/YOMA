from pathlib import Path

import pytest

from yoma.credential_vault import (
    CredentialNotFound,
    CredentialVault,
    CredentialVaultError,
)


def test_vault_round_trip(tmp_path: Path):
    path = tmp_path / "credentials.json"
    vault = CredentialVault(path, b"x" * 32)

    value = {
        "access_token": "secret-access-token",
        "refresh_token": "secret-refresh-token",
        "scope": ["gmail.readonly"],
    }

    vault.store("google:user:1", value)

    assert vault.exists("google:user:1")
    assert vault.retrieve("google:user:1") == value


def test_vault_does_not_store_plaintext(tmp_path: Path):
    path = tmp_path / "credentials.json"
    vault = CredentialVault(path, b"x" * 32)

    vault.store(
        "google:user:1",
        {"access_token": "SUPER-SECRET-TOKEN"},
    )

    raw = path.read_text(encoding="utf-8")

    assert "SUPER-SECRET-TOKEN" not in raw


def test_wrong_key_fails(tmp_path: Path):
    path = tmp_path / "credentials.json"

    CredentialVault(path, b"x" * 32).store(
        "google:user:1",
        {"access_token": "secret"},
    )

    with pytest.raises(CredentialVaultError):
        CredentialVault(path, b"y" * 32).retrieve("google:user:1")


def test_missing_credential_fails(tmp_path: Path):
    vault = CredentialVault(
        tmp_path / "credentials.json",
        b"x" * 32,
    )

    with pytest.raises(CredentialNotFound):
        vault.retrieve("missing")


def test_delete_credential(tmp_path: Path):
    vault = CredentialVault(
        tmp_path / "credentials.json",
        b"x" * 32,
    )

    vault.store("google:user:1", {"access_token": "secret"})
    vault.delete("google:user:1")

    assert not vault.exists("google:user:1")

    with pytest.raises(CredentialNotFound):
        vault.retrieve("google:user:1")
