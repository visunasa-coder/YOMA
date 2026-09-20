"""M41.2 cross-layer workflow validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CrossLayerWorkflowResult:
    valid: bool
    event_stage: bool
    intelligence_stage: bool
    control_stage: bool
    background_stage: bool
    licensing_stage: bool
    deployment_stage: bool
    hardening_stage: bool
    workflow_order_valid: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "event_stage": self.event_stage,
            "intelligence_stage": self.intelligence_stage,
            "control_stage": self.control_stage,
            "background_stage": self.background_stage,
            "licensing_stage": self.licensing_stage,
            "deployment_stage": self.deployment_stage,
            "hardening_stage": self.hardening_stage,
            "workflow_order_valid": self.workflow_order_valid,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class CrossLayerWorkflowValidation:
    """Read-only validation of the enterprise workflow handoff order."""

    EXPECTED_ORDER = (
        "event",
        "intelligence",
        "control",
        "background",
        "licensing",
        "deployment",
        "hardening",
    )

    def validate(
        self,
        *,
        stages: Iterable[str],
        event_stage: bool = True,
        intelligence_stage: bool = True,
        control_stage: bool = True,
        background_stage: bool = True,
        licensing_stage: bool = True,
        deployment_stage: bool = True,
        hardening_stage: bool = True,
        issues: Iterable[str] = (),
    ) -> CrossLayerWorkflowResult:
        normalized_stages = tuple(
            dict.fromkeys(str(stage).lower() for stage in stages)
        )

        workflow_order_valid = (
            normalized_stages == self.EXPECTED_ORDER
        )

        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            event_stage,
            intelligence_stage,
            control_stage,
            background_stage,
            licensing_stage,
            deployment_stage,
            hardening_stage,
            workflow_order_valid,
        )

        return CrossLayerWorkflowResult(
            valid=all(checks),
            event_stage=event_stage,
            intelligence_stage=intelligence_stage,
            control_stage=control_stage,
            background_stage=background_stage,
            licensing_stage=licensing_stage,
            deployment_stage=deployment_stage,
            hardening_stage=hardening_stage,
            workflow_order_valid=workflow_order_valid,
            issues=normalized_issues,
        )
