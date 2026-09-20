from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OperationalControlLifecycleState(str, Enum):
    CREATED = "created"
    ANALYZED = "analyzed"
    CONTROL_PLANNED = "control_planned"
    ORCHESTRATED = "orchestrated"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class OperationalControlLifecycle:
    decision_id: str
    plan_id: str
    orchestration_id: str
    state: OperationalControlLifecycleState
    created_at: datetime
    updated_at: datetime
    requires_human_approval: bool
    executable: bool
    metadata: dict[str, Any]

    @classmethod
    def from_bridge_result(
        cls,
        bridge_result: Any,
    ) -> "OperationalControlLifecycle":
        operational = bridge_result.operational
        decision_intelligence = bridge_result.decision_intelligence
        unified_results = bridge_result.unified_control

        if not unified_results:
            raise ValueError(
                "M34.4 requires at least one unified-control result"
            )

        first_unified = unified_results[0]

        decision_id = str(getattr(decision_intelligence, "decision_id", ""))
        if not decision_id:
            decisions = getattr(decision_intelligence, "decisions", ())
            if decisions:
                decision_id = str(getattr(decisions[0], "decision_id", ""))
        if not decision_id:
            decision_id = str(getattr(operational, "decision_id", ""))

        plan_id = str(getattr(first_unified, "plan_id", ""))
        orchestration_id = str(
            getattr(first_unified, "orchestration_id", "")
        )

        if not decision_id:
            raise ValueError("M34.4 requires decision_id")
        if not plan_id:
            raise ValueError("M34.4 requires plan_id")
        if not orchestration_id:
            raise ValueError("M34.4 requires orchestration_id")

        created_at = getattr(operational, "created_at", None)
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        now = datetime.now(timezone.utc)

        # Automated processing terminates at the human-approval boundary.
        return cls(
            decision_id=decision_id,
            plan_id=plan_id,
            orchestration_id=orchestration_id,
            state=OperationalControlLifecycleState.AWAITING_APPROVAL,
            created_at=created_at,
            updated_at=now,
            requires_human_approval=True,
            executable=False,
            metadata={
                "source": "M34.3",
                "automated_terminal_state": True,
            },
        )

    def transition(
        self,
        state: OperationalControlLifecycleState,
    ) -> "OperationalControlLifecycle":
        allowed = {
            OperationalControlLifecycleState.CREATED: {
                OperationalControlLifecycleState.ANALYZED,
            },
            OperationalControlLifecycleState.ANALYZED: {
                OperationalControlLifecycleState.CONTROL_PLANNED,
            },
            OperationalControlLifecycleState.CONTROL_PLANNED: {
                OperationalControlLifecycleState.ORCHESTRATED,
            },
            OperationalControlLifecycleState.ORCHESTRATED: {
                OperationalControlLifecycleState.AWAITING_APPROVAL,
            },
            OperationalControlLifecycleState.AWAITING_APPROVAL: {
                OperationalControlLifecycleState.APPROVED,
                OperationalControlLifecycleState.REJECTED,
            },
            OperationalControlLifecycleState.APPROVED: set(),
            OperationalControlLifecycleState.REJECTED: set(),
        }

        if state not in allowed[self.state]:
            raise ValueError(
                f"Invalid lifecycle transition: "
                f"{self.state.value} -> {state.value}"
            )

        # M34.4 itself never converts approval into execution.
        if state == OperationalControlLifecycleState.APPROVED:
            return replace(
                self,
                state=state,
                updated_at=datetime.now(timezone.utc),
                requires_human_approval=False,
                executable=False,
            )

        return replace(
            self,
            state=state,
            updated_at=datetime.now(timezone.utc),
        )
