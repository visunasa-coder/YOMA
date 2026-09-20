from dataclasses import dataclass
from enum import Enum
import time


class SessionDecision(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPICIOUS = "suspicious"


@dataclass(frozen=True)
class SecuritySession:
    session_id: str
    identity_id: str
    issued_at: float
    expires_at: float
    suspicious: bool = False


@dataclass(frozen=True)
class SessionResult:
    decision: SessionDecision
    session_id: str
    reason: str
    reauthentication_required: bool
    requires_human_approval: bool = True
    executable: bool = False


class SessionSecurity:
    def evaluate(
        self,
        session: SecuritySession,
        now: float | None = None,
    ) -> SessionResult:

        current = time.time() if now is None else now

        if session.suspicious:
            return SessionResult(
                SessionDecision.SUSPICIOUS,
                session.session_id,
                "suspicious session",
                True,
            )

        if current >= session.expires_at:
            return SessionResult(
                SessionDecision.EXPIRED,
                session.session_id,
                "session expired",
                True,
            )

        return SessionResult(
            SessionDecision.ACTIVE,
            session.session_id,
            "session active",
            False,
        )
