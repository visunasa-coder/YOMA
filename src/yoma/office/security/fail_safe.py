from __future__ import annotations

from enum import Enum


class SecurityFailSafeState(str, Enum):
    NORMAL = "normal"
    FAIL_CLOSED = "fail_closed"
    EVIDENCE_PRESERVATION = "evidence_preservation"
    RECOVERY_REVIEW = "recovery_review"


class SecurityFailSafe:
    def evaluate(
        self,
        *,
        security_valid: bool,
        evidence_preserved: bool = False,
        recovery_approved: bool = False,
    ) -> SecurityFailSafeState:

        if not security_valid:
            if not evidence_preserved:
                return SecurityFailSafeState.EVIDENCE_PRESERVATION
            return SecurityFailSafeState.FAIL_CLOSED

        if not recovery_approved:
            return SecurityFailSafeState.RECOVERY_REVIEW

        return SecurityFailSafeState.NORMAL
