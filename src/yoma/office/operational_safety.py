"""Audit and operational safety assessment for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class OperationalSafetyResult:
    safe: bool
    audit_enabled: bool
    traceable: bool
    approval_boundary_intact: bool
    execution_blocked: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "audit_enabled": self.audit_enabled,
            "traceable": self.traceable,
            "approval_boundary_intact": self.approval_boundary_intact,
            "execution_blocked": self.execution_blocked,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class OperationalSafety:
    """Read-only production audit and operational safety assessment."""

    def assess(
        self,
        *,
        audit_enabled: bool,
        traceable: bool,
        approval_boundary_intact: bool,
        execution_blocked: bool,
        issues: Iterable[str] = (),
    ) -> OperationalSafetyResult:
        normalized_issues = tuple(dict.fromkeys(str(item) for item in issues))

        checks = (
            audit_enabled,
            traceable,
            approval_boundary_intact,
            execution_blocked,
        )

        return OperationalSafetyResult(
            safe=all(checks),
            audit_enabled=audit_enabled,
            traceable=traceable,
            approval_boundary_intact=approval_boundary_intact,
            execution_blocked=execution_blocked,
            issues=normalized_issues,
        )
