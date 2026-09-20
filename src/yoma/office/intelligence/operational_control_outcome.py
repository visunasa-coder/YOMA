from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from yoma.office.intelligence.operational_control_lifecycle import (
    OperationalControlLifecycle,
    OperationalControlLifecycleState,
)


class OperationalControlOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class OperationalControlOutcomeResult:
    decision_id: str
    plan_id: str
    orchestration_id: str
    previous_state: OperationalControlLifecycleState
    outcome: OperationalControlOutcome
    recorded_at: datetime
    requires_human_approval: bool
    execution_handoff_available: bool
    executable: bool
    metadata: dict[str, Any]


class OperationalControlOutcomeRuntime:
    """
    M34.5 — Operational Control Outcome Handoff.

    Records the explicit human outcome of an M34.4 lifecycle.

    This component never executes an action and never authorizes
    execution on its own. An APPROVED outcome only indicates that
    the existing approval/execution infrastructure may be used by
    a separate, explicitly authorized flow.
    """

    @staticmethod
    def record(
        lifecycle: OperationalControlLifecycle,
        outcome: OperationalControlOutcome,
    ) -> OperationalControlOutcomeResult:
        if lifecycle.state != OperationalControlLifecycleState.AWAITING_APPROVAL:
            raise ValueError(
                "M34.5 requires lifecycle state AWAITING_APPROVAL"
            )

        recorded_at = datetime.now(timezone.utc)

        if outcome == OperationalControlOutcome.APPROVED:
            return OperationalControlOutcomeResult(
                decision_id=lifecycle.decision_id,
                plan_id=lifecycle.plan_id,
                orchestration_id=lifecycle.orchestration_id,
                previous_state=lifecycle.state,
                outcome=outcome,
                recorded_at=recorded_at,
                requires_human_approval=False,
                execution_handoff_available=True,
                executable=False,
                metadata={
                    **lifecycle.metadata,
                    "source": "M34.5",
                    "human_outcome": "approved",
                    "execution_owner": "existing_approval_execution_bridge",
                },
            )

        return OperationalControlOutcomeResult(
            decision_id=lifecycle.decision_id,
            plan_id=lifecycle.plan_id,
            orchestration_id=lifecycle.orchestration_id,
            previous_state=lifecycle.state,
            outcome=outcome,
            recorded_at=recorded_at,
            requires_human_approval=False,
            execution_handoff_available=False,
            executable=False,
            metadata={
                **lifecycle.metadata,
                "source": "M34.5",
                "human_outcome": "rejected",
                "execution_owner": None,
            },
        )
