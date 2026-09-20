from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from yoma.office.intelligence.operational_control_observation import (
    OperationalControlObservation,
)
from yoma.office.intelligence.operational_control_reconciliation import (
    OperationalControlReconciliationState,
)


@dataclass(frozen=True)
class OperationalControlLearningHandoff:
    decision_id: str
    plan_id: str
    orchestration_id: str
    observed_state: str
    reconciliation_state: OperationalControlReconciliationState
    learning_signal: str
    observed_at: datetime
    handed_off_at: datetime
    autonomous_learning: bool
    executable: bool
    metadata: dict[str, Any]


class OperationalControlLearningRuntime:
    """
    M34.8 — Operational Control Learning Handoff.

    Converts M34.7 observations into a learning-ready signal for
    YOMA's existing outcome-learning infrastructure.

    This component does not modify policy, execute actions, approve
    actions, or autonomously alter future behavior.
    """

    @staticmethod
    def prepare(
        observation: OperationalControlObservation,
    ) -> OperationalControlLearningHandoff:
        if not observation.decision_id:
            raise ValueError("M34.8 requires decision_id")

        if not observation.plan_id:
            raise ValueError("M34.8 requires plan_id")

        if not observation.orchestration_id:
            raise ValueError("M34.8 requires orchestration_id")

        if (
            observation.reconciliation_state
            == OperationalControlReconciliationState.CONSISTENT
        ):
            learning_signal = "control_outcome_consistent"
        elif (
            observation.reconciliation_state
            == OperationalControlReconciliationState.DIVERGED
        ):
            learning_signal = "control_outcome_diverged"
        else:
            learning_signal = "control_outcome_pending"

        return OperationalControlLearningHandoff(
            decision_id=observation.decision_id,
            plan_id=observation.plan_id,
            orchestration_id=observation.orchestration_id,
            observed_state=observation.observed_state,
            reconciliation_state=observation.reconciliation_state,
            learning_signal=learning_signal,
            observed_at=observation.observed_at,
            handed_off_at=datetime.now(timezone.utc),
            autonomous_learning=False,
            executable=False,
            metadata={
                **observation.metadata,
                "source": "M34.8",
                "learning_handoff_only": True,
                "learning_owner": "existing_outcome_learning",
            },
        )
