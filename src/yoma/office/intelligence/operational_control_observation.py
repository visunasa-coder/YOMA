from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from yoma.office.intelligence.operational_control_reconciliation import (
    OperationalControlReconciliationResult,
    OperationalControlReconciliationState,
)


@dataclass(frozen=True)
class OperationalControlObservation:
    decision_id: str
    plan_id: str
    orchestration_id: str
    observed_state: str
    reconciliation_state: OperationalControlReconciliationState
    observed_at: datetime
    execution_allowed: bool
    executable: bool
    metadata: dict[str, Any]


class OperationalControlObservationRuntime:
    """
    M34.7 — Operational Control Observation.

    Converts the M34.6 reconciliation result into an immutable
    observation record.

    This component records state only. It does not execute,
    approve, retry, repair, or mutate the underlying control.
    """

    @staticmethod
    def observe(
        reconciliation: OperationalControlReconciliationResult,
    ) -> OperationalControlObservation:
        if not reconciliation.decision_id:
            raise ValueError("M34.7 requires decision_id")

        if not reconciliation.plan_id:
            raise ValueError("M34.7 requires plan_id")

        if not reconciliation.orchestration_id:
            raise ValueError("M34.7 requires orchestration_id")

        return OperationalControlObservation(
            decision_id=reconciliation.decision_id,
            plan_id=reconciliation.plan_id,
            orchestration_id=reconciliation.orchestration_id,
            observed_state=reconciliation.observed_state,
            reconciliation_state=reconciliation.state,
            observed_at=datetime.now(timezone.utc),
            execution_allowed=False,
            executable=False,
            metadata={
                **reconciliation.metadata,
                "source": "M34.7",
                "observation_only": True,
            },
        )
