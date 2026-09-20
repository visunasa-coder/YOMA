from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_approval import ActionApprovalWorkflow


VALID_OUTCOME_STATUSES = {
    "pending",
    "observed",
    "partial",
    "failed",
    "unknown",
}


@dataclass(frozen=True)
class OperationalObservation:
    observation_id: str
    workflow_id: str
    plan_id: str
    decision_id: str
    observed_at: datetime
    outcome_status: str
    description: str
    expected: bool = True
    event_ids: Tuple[str, ...] = ()
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id.startswith("OBS-"):
            raise ValueError("observation_id must start with OBS-")
        if not self.workflow_id.startswith("AWF-"):
            raise ValueError("workflow_id must start with AWF-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if self.outcome_status not in VALID_OUTCOME_STATUSES:
            raise ValueError("invalid outcome status")
        if not self.description:
            raise ValueError("description must not be empty")


@dataclass(frozen=True)
class ClosedLoopObservation:
    observation_id: str
    workflow_id: str
    plan_id: str
    decision_id: str
    approval_status: str
    observations: Tuple[OperationalObservation, ...] = ()
    expected_event_count: int = 0
    observed_event_count: int = 0
    outcome_status: str = "pending"
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id.startswith("CLOOP-"):
            raise ValueError("observation_id must start with CLOOP-")
        if not self.workflow_id.startswith("AWF-"):
            raise ValueError("workflow_id must start with AWF-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if self.outcome_status not in VALID_OUTCOME_STATUSES:
            raise ValueError("invalid outcome status")
        if self.expected_event_count < 0:
            raise ValueError("expected_event_count must be >= 0")
        if self.observed_event_count < 0:
            raise ValueError("observed_event_count must be >= 0")
        if not self.requires_human_approval:
            raise ValueError(
                "closed-loop observation requires human approval"
            )

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def complete(self) -> bool:
        return self.outcome_status in {
            "observed",
            "partial",
            "failed",
        }

    @property
    def matches_expectation(self) -> Optional[bool]:
        if self.outcome_status in {"pending", "unknown"}:
            return None

        if self.expected_event_count == 0:
            return self.outcome_status == "observed"

        return self.observed_event_count >= self.expected_event_count

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class ClosedLoopObservationEngine:
    """
    Records observations after an approved action workflow.

    This module observes supplied results only. It does not execute
    actions or query external systems itself.
    """

    def create(
        self,
        workflow: ActionApprovalWorkflow,
        expected_event_count: int = 0,
    ) -> ClosedLoopObservation:
        if not isinstance(workflow, ActionApprovalWorkflow):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not workflow.approved:
            raise ValueError(
                "closed-loop observation requires an approved workflow"
            )

        if expected_event_count < 0:
            raise ValueError(
                "expected_event_count must be >= 0"
            )

        return ClosedLoopObservation(
            observation_id=f"CLOOP-{workflow.workflow_id}",
            workflow_id=workflow.workflow_id,
            plan_id=workflow.plan_id,
            decision_id=workflow.decision_id,
            approval_status=workflow.status,
            observations=(),
            expected_event_count=expected_event_count,
            observed_event_count=0,
            outcome_status="pending",
            requires_human_approval=True,
        )

    def record(
        self,
        loop: ClosedLoopObservation,
        observed_at: datetime,
        outcome_status: str,
        description: str,
        event_ids: Tuple[str, ...] | list[str] = (),
        affected_user_ids: Tuple[str, ...] | list[str] = (),
        affected_system_ids: Tuple[str, ...] | list[str] = (),
        evidence: Mapping[str, Any] | None = None,
        expected: bool = True,
    ) -> ClosedLoopObservation:
        if not isinstance(loop, ClosedLoopObservation):
            raise TypeError(
                "loop must be a ClosedLoopObservation"
            )

        if outcome_status not in VALID_OUTCOME_STATUSES:
            raise ValueError("invalid outcome status")

        observation = OperationalObservation(
            observation_id=(
                f"OBS-{loop.observation_id}"
                f"-{len(loop.observations) + 1}"
            ),
            workflow_id=loop.workflow_id,
            plan_id=loop.plan_id,
            decision_id=loop.decision_id,
            observed_at=observed_at,
            outcome_status=outcome_status,
            description=description,
            expected=expected,
            event_ids=tuple(event_ids),
            affected_user_ids=tuple(sorted(set(affected_user_ids))),
            affected_system_ids=tuple(sorted(set(affected_system_ids))),
            evidence=dict(evidence or {}),
        )

        observed_count = loop.observed_event_count + len(
            observation.event_ids
        )

        return ClosedLoopObservation(
            observation_id=loop.observation_id,
            workflow_id=loop.workflow_id,
            plan_id=loop.plan_id,
            decision_id=loop.decision_id,
            approval_status=loop.approval_status,
            observations=(
                *loop.observations,
                observation,
            ),
            expected_event_count=loop.expected_event_count,
            observed_event_count=observed_count,
            outcome_status=outcome_status,
            requires_human_approval=True,
            metadata=dict(loop.metadata),
        )
