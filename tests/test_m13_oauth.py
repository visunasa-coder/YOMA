from yoma.google_oauth import (
    GoogleOAuthError,
    GoogleTokenResponse,
    exchange_authorization_code,
)


def test_google_token_response_shape():
    token = GoogleTokenResponse(
        access_token="access",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="refresh",
        scope=("scope.one", "scope.two"),
    )

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert token.expires_in == 3600
    assert token.scope == ("scope.one", "scope.two")


def test_google_oauth_requires_client_id():
    try:
        exchange_authorization_code(
            client_id="",
            client_secret="secret",
            redirect_uri="http://127.0.0.1:8765/oauth/google/callback",
            code="test-code",
        )
    except GoogleOAuthError as exc:
        assert "client ID" in str(exc)
    else:
        raise AssertionError("missing client ID was accepted")


def test_google_oauth_requires_code():
    try:
        exchange_authorization_code(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://127.0.0.1:8765/oauth/google/callback",
            code="",
        )
    except GoogleOAuthError as exc:
        assert "authorization code" in str(exc)
    else:
        raise AssertionError("missing authorization code was accepted")
