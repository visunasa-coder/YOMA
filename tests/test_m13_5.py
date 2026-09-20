from datetime import datetime, timezone

import pytest

from yoma.credential_vault import CredentialVault
from yoma.google_credentials import (
    GoogleCredentialError,
    GoogleCredentialStore,
)
from yoma.google_oauth import GoogleTokenResponse


def make_store(tmp_path):
    vault = CredentialVault(
        tmp_path / "credentials.vault",
        b"m13.5-test-master-key-" + (b"x" * 32),
    )
    return GoogleCredentialStore(vault)


def make_token():
    return GoogleTokenResponse(
        access_token="access-secret",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="refresh-secret",
        scope=(
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ),
    )


def test_google_credentials_store_roundtrip(tmp_path):
    store = make_store(tmp_path)

    store.store_token(
        user_id=7,
        integration_id="google_workspace",
        token=make_token(),
    )

    credential = store.retrieve_token(
        user_id=7,
        integration_id="google_workspace",
    )

    assert credential.access_token == "access-secret"
    assert credential.token_type == "Bearer"
    assert credential.refresh_token == "refresh-secret"
    assert credential.scopes == (
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
    )
    assert credential.expires_at > datetime.now(timezone.utc)


def test_google_credentials_do_not_store_plaintext(tmp_path):
    vault_path = tmp_path / "credentials.vault"
    store = GoogleCredentialStore(
        CredentialVault(
            vault_path,
            b"m13.5-test-master-key-" + (b"x" * 32),
        )
    )

    store.store_token(
        user_id=7,
        integration_id="google_workspace",
        token=make_token(),
    )

    raw = vault_path.read_text(encoding="utf-8")

    assert "access-secret" not in raw
    assert "refresh-secret" not in raw
    assert "gmail.readonly" not in raw


def test_google_credentials_are_user_scoped(tmp_path):
    store = make_store(tmp_path)

    store.store_token(
        user_id=7,
        integration_id="google_workspace",
        token=make_token(),
    )

    assert store.exists(
        user_id=7,
        integration_id="google_workspace",
    )

    assert not store.exists(
        user_id=8,
        integration_id="google_workspace",
    )


def test_google_credentials_delete(tmp_path):
    store = make_store(tmp_path)

    store.store_token(
        user_id=7,
        integration_id="google_workspace",
        token=make_token(),
    )

    assert store.exists(
        user_id=7,
        integration_id="google_workspace",
    )

    store.delete(
        user_id=7,
        integration_id="google_workspace",
    )

    assert not store.exists(
        user_id=7,
        integration_id="google_workspace",
    )


def test_google_credentials_missing_credential_fails_safely(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(GoogleCredentialError):
        store.retrieve_token(
            user_id=999,
            integration_id="google_workspace",
        )


def test_google_credentials_reject_negative_expiry(tmp_path):
    store = make_store(tmp_path)

    token = GoogleTokenResponse(
        access_token="access",
        token_type="Bearer",
        expires_in=-1,
        refresh_token=None,
        scope=(),
    )

    with pytest.raises(GoogleCredentialError):
        store.store_token(
            user_id=7,
            integration_id="google_workspace",
            token=token,
        )
