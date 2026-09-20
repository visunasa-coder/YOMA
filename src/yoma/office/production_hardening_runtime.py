"""Production hardening runtime for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from yoma.office.operational_safety import OperationalSafety
from yoma.office.production_hardening import ProductionHardening
from yoma.office.runtime_failure_isolation import RuntimeFailureIsolation


@dataclass(frozen=True)
class ProductionHardeningRuntimeResult:
    ready: bool
    secure: bool
    failure_isolated: bool
    operationally_safe: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "secure": self.secure,
            "failure_isolated": self.failure_isolated,
            "operationally_safe": self.operationally_safe,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProductionHardeningRuntime:
    """Composes production hardening assessments without executing changes."""

    def assess(
        self,
        *,
        configuration_valid: bool,
        secrets_protected: bool,
        execution_governed: bool,
        failures_isolated: bool,
        components: Iterable[str],
        failed_components: Iterable[str] = (),
        audit_enabled: bool,
        traceable: bool,
        approval_boundary_intact: bool,
        execution_blocked: bool,
        issues: Iterable[str] = (),
    ) -> ProductionHardeningRuntimeResult:
        hardening = ProductionHardening().assess(
            configuration_valid=configuration_valid,
            secrets_protected=secrets_protected,
            execution_governed=execution_governed,
            failures_isolated=failures_isolated,
            issues=tuple(issues),
        )

        isolation = RuntimeFailureIsolation().assess(
            components=components,
            failed_components=failed_components,
            failures=hardening.issues,
        )

        safety = OperationalSafety().assess(
            audit_enabled=audit_enabled,
            traceable=traceable,
            approval_boundary_intact=approval_boundary_intact,
            execution_blocked=execution_blocked,
            issues=hardening.issues,
        )

        combined_issues = tuple(
            dict.fromkeys(
                (
                    *hardening.issues,
                    *isolation.failures,
                    *safety.issues,
                )
            )
        )

        ready = (
            hardening.secure
            and isolation.isolated
            and safety.safe
        )

        return ProductionHardeningRuntimeResult(
            ready=ready,
            secure=hardening.secure,
            failure_isolated=isolation.isolated,
            operationally_safe=safety.safe,
            issues=combined_issues,
        )
