"""YOMA v1.0 production release safety boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ProductionReleaseSafetyResult:
    safe: bool
    human_approval_required: bool
    explicit_authorization_required: bool
    execution_blocked: bool
    autonomous_release_blocked: bool
    release_authorized: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "human_approval_required": self.human_approval_required,
            "explicit_authorization_required": self.explicit_authorization_required,
            "execution_blocked": self.execution_blocked,
            "autonomous_release_blocked": self.autonomous_release_blocked,
            "release_authorized": self.release_authorized,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProductionReleaseSafety:
    """Read-only validation of the final production release boundary."""

    def assess(
        self,
        *,
        human_approval_required: bool,
        explicit_authorization_required: bool,
        execution_blocked: bool,
        autonomous_release_blocked: bool,
        release_authorized: bool = False,
        issues: Iterable[str] = (),
    ) -> ProductionReleaseSafetyResult:
        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            human_approval_required,
            explicit_authorization_required,
            execution_blocked,
            autonomous_release_blocked,
        )

        return ProductionReleaseSafetyResult(
            safe=all(checks),
            human_approval_required=human_approval_required,
            explicit_authorization_required=explicit_authorization_required,
            execution_blocked=execution_blocked,
            autonomous_release_blocked=autonomous_release_blocked,
            release_authorized=release_authorized,
            issues=normalized_issues,
        )
