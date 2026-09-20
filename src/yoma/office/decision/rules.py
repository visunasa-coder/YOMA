from __future__ import annotations

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.operations import OperationalAction, OperationalSignal


def workload_decision(signal: OperationalSignal) -> DecisionContext:
    recommendation = {
        "type": "workload_review",
        "reason": (
            "Operational workload signal requires human review."
        ),
        "employee_id": signal.user_id,
        "score": signal.score,
    }

    action = OperationalAction(
        action_id=f"ACT-{signal.signal_id}",
        action_type="workload.review",
        target_user_id=signal.user_id,
        source="yoma_intelligence",
        reason=recommendation["reason"],
        requires_approval=True,
    )

    return DecisionContext(
        signal=signal,
        recommendations=(recommendation,),
        actions=(action,),
        requires_human_approval=True,
    )
