from __future__ import annotations

from enum import IntEnum


class SecurityPrecedence(IntEnum):
    REVIEW = 10
    GOVERNANCE_DENY = 20
    DATA_DENY = 30
    THREAT_DENY = 40
    IDENTITY_DENY = 50
    HOST_COMPROMISE = 60
    INVALID_REQUEST = 70
    CRITICAL_DENY = 100


class SecurityDecisionPrecedence:
    """
    Higher precedence always wins.

    A lower layer cannot override a higher-priority denial.
    """

    @staticmethod
    def highest(*values: SecurityPrecedence) -> SecurityPrecedence:
        if not values:
            return SecurityPrecedence.REVIEW
        return max(values)
