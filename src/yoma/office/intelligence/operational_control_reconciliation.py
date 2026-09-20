from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from yoma.office.intelligence.operational_control_outcome import (
    OperationalControlOutcome,
    OperationalControlOutcomeResult,
)


class OperationalControlReconciliationState(str, Enum):
    PENDING = "pending"
    CONSISTENT = "consistent"
    DIVERGED = "diverged"


@dataclass(frozen=True)
class OperationalControlReconciliationResult:
    decision_id: str
    plan_id: str
    orchestration_id: str
    expected_outcome: OperationalControlOutcome
    observed_state: str
    state: OperationalControlReconciliationState
    reconciled_at: datetime
    requires_human_approval: bool
    executable: bool
    metadata: dict[str, Any]


class OperationalControlReconciliationRuntime:
    """
    M34.6 — Operational Control Reconciliation.

    Compares the expected human control outcome with an externally
    observed downstream state.

    This layer does not execute, approve, retry, or repair actions.
    """

    @staticmethod
    def reconcile(
        outcome_result: OperationalControlOutcomeResult,
        observed_state: str | None = None,
    ) -> OperationalControlReconciliationResult:
        if not outcome_result.decision_id:
            raise ValueError("M34.6 requires decision_id")

        if not outcome_result.plan_id:
            raise ValueError("M34.6 requires plan_id")

        if not outcome_result.orchestration_id:
            raise ValueError("M34.6 requires orchestration_id")

        if observed_state is None:
            return OperationalControlReconciliationResult(
                decision_id=outcome_result.decision_id,
                plan_id=outcome_result.plan_id,
                orchestration_id=outcome_result.orchestration_id,
                expected_outcome=outcome_result.outcome,
                observed_state="unknown",
                state=OperationalControlReconciliationState.PENDING,
                reconciled_at=datetime.now(timezone.utc),
                requires_human_approval=False,
                executable=False,
                metadata={
                    **outcome_result.metadata,
                    "source": "M34.6",
                    "reconciliation": "pending",
                },
            )

        normalized = str(observed_state).strip().lower()

        if not normalized:
            raise ValueError("observed_state cannot be empty")

        expected = outcome_result.outcome.value

        state = (
            OperationalControlReconciliationState.CONSISTENT
            if normalized == expected
            else OperationalControlReconciliationState.DIVERGED
        )

        return OperationalControlReconciliationResult(
            decision_id=outcome_result.decision_id,
            plan_id=outcome_result.plan_id,
            orchestration_id=outcome_result.orchestration_id,
            expected_outcome=outcome_result.outcome,
            observed_state=normalized,
            state=state,
            reconciled_at=datetime.now(timezone.utc),
            requires_human_approval=False,
            executable=False,
            metadata={
                **outcome_result.metadata,
                "source": "M34.6",
                "reconciliation": state.value,
            },
        )
