from dataclasses import dataclass
from enum import Enum


class AuthenticationDecision(str, Enum):
    AUTHENTICATED = "authenticated"
    DENIED = "denied"
    REAUTH_REQUIRED = "reauth_required"


@dataclass(frozen=True)
class AuthenticationResult:
    decision: AuthenticationDecision
    identity_id: str | None
    reason: str
    authenticated: bool
    requires_human_approval: bool = True
    executable: bool = False


class AuthenticationBoundary:
    def authenticate(
        self,
        identity_id: str,
        credential_valid: bool,
        session_valid: bool = True,
        active: bool = True,
    ) -> AuthenticationResult:

        if not identity_id or not active:
            return AuthenticationResult(
                AuthenticationDecision.DENIED,
                None,
                "identity unavailable",
                False,
            )

        if not credential_valid:
            return AuthenticationResult(
                AuthenticationDecision.DENIED,
                identity_id,
                "credential validation failed",
                False,
            )

        if not session_valid:
            return AuthenticationResult(
                AuthenticationDecision.REAUTH_REQUIRED,
                identity_id,
                "session requires re-authentication",
                False,
            )

        return AuthenticationResult(
            AuthenticationDecision.AUTHENTICATED,
            identity_id,
            "authentication satisfied",
            True,
        )
