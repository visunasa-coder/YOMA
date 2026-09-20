"""M41.4 end-to-end enterprise validation runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from yoma.office.enterprise_safety_boundary import EnterpriseSafetyBoundary
from yoma.office.enterprise_validation import EnterpriseValidation
from yoma.office.cross_layer_workflow_validation import (
    CrossLayerWorkflowValidation,
)


@dataclass(frozen=True)
class E2EValidationRuntimeResult:
    valid: bool
    enterprise_valid: bool
    workflow_valid: bool
    safety_valid: bool
    execution_governed: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "enterprise_valid": self.enterprise_valid,
            "workflow_valid": self.workflow_valid,
            "safety_valid": self.safety_valid,
            "execution_governed": self.execution_governed,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class E2EValidationRuntime:
    """Composes enterprise, workflow, and safety validation."""

    def validate(
        self,
        *,
        stages: Iterable[str],
        events_valid: bool,
        intelligence_valid: bool,
        control_valid: bool,
        background_valid: bool,
        licensing_valid: bool,
        deployment_valid: bool,
        hardening_valid: bool,
        execution_governed: bool,
        human_approval_required: bool,
        execution_blocked: bool,
        authorization_explicit: bool,
        autonomous_execution_blocked: bool,
        issues: Iterable[str] = (),
    ) -> E2EValidationRuntimeResult:
        enterprise = EnterpriseValidation().validate(
            events_valid=events_valid,
            intelligence_valid=intelligence_valid,
            control_valid=control_valid,
            background_valid=background_valid,
            licensing_valid=licensing_valid,
            deployment_valid=deployment_valid,
            hardening_valid=hardening_valid,
            execution_governed=execution_governed,
            issues=tuple(issues),
        )

        workflow = CrossLayerWorkflowValidation().validate(
            stages=stages,
            issues=enterprise.issues,
        )

        safety = EnterpriseSafetyBoundary().validate(
            human_approval_required=human_approval_required,
            execution_blocked=execution_blocked,
            authorization_explicit=authorization_explicit,
            autonomous_execution_blocked=autonomous_execution_blocked,
            issues=enterprise.issues,
        )

        combined_issues = tuple(
            dict.fromkeys(
                (
                    *enterprise.issues,
                    *workflow.issues,
                    *safety.issues,
                )
            )
        )

        valid = (
            enterprise.valid
            and workflow.valid
            and safety.safe
        )

        return E2EValidationRuntimeResult(
            valid=valid,
            enterprise_valid=enterprise.valid,
            workflow_valid=workflow.valid,
            safety_valid=safety.safe,
            execution_governed=execution_governed,
            issues=combined_issues,
        )
