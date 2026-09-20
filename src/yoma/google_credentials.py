"""Secure Google OAuth credential persistence for YOMA M13.5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from yoma.credential_vault import CredentialVault, CredentialVaultError
from yoma.google_oauth import GoogleTokenResponse


class GoogleCredentialError(RuntimeError):
    """Base error for Google credential persistence failures."""


@dataclass(frozen=True)
class GoogleCredential:
    access_token: str
    token_type: str
    refresh_token: str | None
    expires_at: datetime
    scopes: tuple[str, ...]


class GoogleCredentialStore:
    """Secure persistence boundary for Google OAuth credentials.

    OAuth tokens are persisted only through CredentialVault.
    This class never writes plaintext credentials to disk.
    """

    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    @staticmethod
    def _credential_id(user_id: int | str, integration_id: str) -> str:
        if not str(user_id):
            raise GoogleCredentialError("user ID is required")

        if not integration_id:
            raise GoogleCredentialError("integration ID is required")

        return f"google:{integration_id}:{user_id}"

    def store_token(
        self,
        *,
        user_id: int | str,
        integration_id: str,
        token: GoogleTokenResponse,
    ) -> None:
        if not token.access_token:
            raise GoogleCredentialError("access token is required")

        if not token.token_type:
            raise GoogleCredentialError("token type is required")

        if token.expires_in < 0:
            raise GoogleCredentialError("token expiry is invalid")

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=token.expires_in)
        ).isoformat()

        payload: dict[str, Any] = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "refresh_token": token.refresh_token,
            "expires_at": expires_at,
            "scopes": list(token.scope),
        }

        credential_id = self._credential_id(user_id, integration_id)

        try:
            self._vault.store(credential_id, payload)
        except CredentialVaultError as exc:
            raise GoogleCredentialError(
                "Google credential could not be stored"
            ) from exc

    def retrieve_token(
        self,
        *,
        user_id: int | str,
        integration_id: str,
    ) -> GoogleCredential:
        credential_id = self._credential_id(user_id, integration_id)

        try:
            payload = self._vault.retrieve(credential_id)
        except CredentialVaultError as exc:
            raise GoogleCredentialError(
                "Google credential could not be retrieved"
            ) from exc

        access_token = payload.get("access_token")
        token_type = payload.get("token_type")
        refresh_token = payload.get("refresh_token")
        expires_at_raw = payload.get("expires_at")
        scopes = payload.get("scopes", [])

        if not isinstance(access_token, str) or not access_token:
            raise GoogleCredentialError("stored access token is invalid")

        if not isinstance(token_type, str) or not token_type:
            raise GoogleCredentialError("stored token type is invalid")

        if refresh_token is not None and not isinstance(refresh_token, str):
            raise GoogleCredentialError("stored refresh token is invalid")

        if not isinstance(expires_at_raw, str):
            raise GoogleCredentialError("stored expiry is invalid")

        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError as exc:
            raise GoogleCredentialError("stored expiry is invalid") from exc

        if not isinstance(scopes, list) or not all(
            isinstance(scope, str) for scope in scopes
        ):
            raise GoogleCredentialError("stored scopes are invalid")

        return GoogleCredential(
            access_token=access_token,
            token_type=token_type,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=tuple(scopes),
        )

    def exists(
        self,
        *,
        user_id: int | str,
        integration_id: str,
    ) -> bool:
        return self._vault.exists(
            self._credential_id(user_id, integration_id)
        )

    def delete(
        self,
        *,
        user_id: int | str,
        integration_id: str,
    ) -> None:
        credential_id = self._credential_id(user_id, integration_id)

        try:
            self._vault.delete(credential_id)
        except CredentialVaultError as exc:
            raise GoogleCredentialError(
                "Google credential could not be deleted"
            ) from exc
