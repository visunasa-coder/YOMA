"""Google OAuth 2.0 token exchange for YOMA M13."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    """Base error for Google OAuth failures."""


@dataclass(frozen=True)
class GoogleTokenResponse:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None
    scope: tuple[str, ...]


def exchange_authorization_code(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    timeout: float = 20.0,
) -> GoogleTokenResponse:
    if not client_id:
        raise GoogleOAuthError("Google OAuth client ID is unavailable")

    if not client_secret:
        raise GoogleOAuthError("Google OAuth client secret is unavailable")

    if not redirect_uri:
        raise GoogleOAuthError("Google OAuth redirect URI is unavailable")

    if not code:
        raise GoogleOAuthError("authorization code is unavailable")

    payload = urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")

    request = Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {}

        error = detail.get("error") if isinstance(detail, dict) else None
        description = (
            detail.get("error_description")
            if isinstance(detail, dict)
            else None
        )

        raise GoogleOAuthError(
            f"Google token exchange failed: {error or exc.code}"
            + (f": {description}" if description else "")
        ) from exc
    except URLError as exc:
        raise GoogleOAuthError("Google token endpoint is unreachable") from exc

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoogleOAuthError("Google returned invalid token response") from exc

    access_token = data.get("access_token")
    token_type = data.get("token_type")
    expires_in = data.get("expires_in")

    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthError("Google token response has no access token")

    if not isinstance(token_type, str) or not token_type:
        raise GoogleOAuthError("Google token response has no token type")

    if isinstance(expires_in, bool) or not isinstance(expires_in, int):
        raise GoogleOAuthError("Google token response has invalid expiry")

    refresh_token = data.get("refresh_token")
    if refresh_token is not None and not isinstance(refresh_token, str):
        raise GoogleOAuthError("Google token response has invalid refresh token")

    raw_scope = data.get("scope", "")
    if not isinstance(raw_scope, str):
        raise GoogleOAuthError("Google token response has invalid scope")

    return GoogleTokenResponse(
        access_token=access_token,
        token_type=token_type,
        expires_in=expires_in,
        refresh_token=refresh_token,
        scope=tuple(scope for scope in raw_scope.split() if scope),
    )
