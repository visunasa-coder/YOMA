"""M41.3 enterprise-wide execution safety boundary validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class EnterpriseSafetyBoundaryResult:
    safe: bool
    human_approval_required: bool
    execution_blocked: bool
    authorization_explicit: bool
    autonomous_execution_blocked: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "human_approval_required": self.human_approval_required,
            "execution_blocked": self.execution_blocked,
            "authorization_explicit": self.authorization_explicit,
            "autonomous_execution_blocked": self.autonomous_execution_blocked,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class EnterpriseSafetyBoundary:
    """Read-only validation of YOMA's enterprise execution boundary."""

    def validate(
        self,
        *,
        human_approval_required: bool,
        execution_blocked: bool,
        authorization_explicit: bool,
        autonomous_execution_blocked: bool,
        issues: Iterable[str] = (),
    ) -> EnterpriseSafetyBoundaryResult:
        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            human_approval_required,
            execution_blocked,
            authorization_explicit,
            autonomous_execution_blocked,
        )

        return EnterpriseSafetyBoundaryResult(
            safe=all(checks),
            human_approval_required=human_approval_required,
            execution_blocked=execution_blocked,
            authorization_explicit=authorization_explicit,
            autonomous_execution_blocked=autonomous_execution_blocked,
            issues=normalized_issues,
        )
