from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from yoma.office.intelligence.operational_unified_control_bridge import (
    OperationalUnifiedControlBridge,
)
from yoma.office.intelligence.operational_control_lifecycle import (
    OperationalControlLifecycle,
)
from yoma.office.intelligence.operational_control_outcome import (
    OperationalControlOutcome,
    OperationalControlOutcomeResult,
    OperationalControlOutcomeRuntime,
)
from yoma.office.intelligence.operational_control_reconciliation import (
    OperationalControlReconciliationResult,
    OperationalControlReconciliationRuntime,
)
from yoma.office.intelligence.operational_control_observation import (
    OperationalControlObservation,
    OperationalControlObservationRuntime,
)
from yoma.office.intelligence.operational_control_learning import (
    OperationalControlLearningHandoff,
    OperationalControlLearningRuntime,
)


@dataclass(frozen=True)
class OperationalControlLifecycleResult:
    bridge: Any
    lifecycle: OperationalControlLifecycle
    outcome: OperationalControlOutcomeResult | None
    reconciliation: OperationalControlReconciliationResult | None
    observation: OperationalControlObservation | None
    learning: OperationalControlLearningHandoff | None
    requires_human_approval: bool
    executable: bool
    metadata: dict[str, Any]


class OperationalControlLifecycleRuntime:
    """M34.9 ? Unified Operational Control Lifecycle Composition."""

    def process(
        self,
        operational_result: Any,
        *,
        scheduled_at: datetime,
        created_at: datetime,
        outcome: OperationalControlOutcome | None = None,
        observed_state: str | None = None,
    ) -> OperationalControlLifecycleResult:
        if scheduled_at.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        bridge = OperationalUnifiedControlBridge().process(
            operational_result,
            scheduled_at=scheduled_at,
            created_at=created_at,
        )

        lifecycle = OperationalControlLifecycle.from_bridge_result(bridge)

        outcome_result = None
        reconciliation = None
        observation = None
        learning = None

        if outcome is not None:
            outcome_result = OperationalControlOutcomeRuntime.record(
                lifecycle, outcome
            )
            reconciliation = OperationalControlReconciliationRuntime.reconcile(
                outcome_result, observed_state
            )
            observation = OperationalControlObservationRuntime.observe(
                reconciliation
            )
            learning = OperationalControlLearningRuntime.prepare(observation)

        return OperationalControlLifecycleResult(
            bridge=bridge,
            lifecycle=lifecycle,
            outcome=outcome_result,
            reconciliation=reconciliation,
            observation=observation,
            learning=learning,
            requires_human_approval=(
                lifecycle.requires_human_approval
                if outcome_result is None
                else outcome_result.requires_human_approval
            ),
            executable=False,
            metadata={
                "source": "M34.9",
                "composition_only": True,
                "execution_authority": "existing_approval_execution_bridge",
            },
        )
