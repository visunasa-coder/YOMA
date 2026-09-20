from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityVerificationCase:
    name: str
    passed: bool
    expected: str
    actual: str


class SecurityVerificationEngine:
    def verify_case(
        self,
        name: str,
        *,
        expected: str,
        actual: str,
    ) -> SecurityVerificationCase:
        return SecurityVerificationCase(
            name=name,
            passed=expected == actual,
            expected=expected,
            actual=actual,
        )
