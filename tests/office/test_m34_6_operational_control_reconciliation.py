from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.operational_control_outcome import (
    OperationalControlOutcome,
    OperationalControlOutcomeResult,
)
from yoma.office.intelligence.operational_control_reconciliation import (
    OperationalControlReconciliationRuntime,
    OperationalControlReconciliationState,
)


def make_outcome(outcome=OperationalControlOutcome.APPROVED):
    return OperationalControlOutcomeResult(
        decision_id="decision-m34-6",
        plan_id="plan-m34-6",
        orchestration_id="orchestration-m34-6",
        previous_state=None,
        outcome=outcome,
        recorded_at=datetime.now(timezone.utc),
        requires_human_approval=False,
        execution_handoff_available=(
            outcome == OperationalControlOutcome.APPROVED
        ),
        executable=False,
        metadata={"test": True},
    )


def test_m34_6_pending_without_observation():
    result = OperationalControlReconciliationRuntime.reconcile(
        make_outcome()
    )

    assert result.state == OperationalControlReconciliationState.PENDING
    assert result.observed_state == "unknown"
    assert result.executable is False


def test_m34_6_approved_consistent():
    result = OperationalControlReconciliationRuntime.reconcile(
        make_outcome(),
        "approved",
    )

    assert result.state == OperationalControlReconciliationState.CONSISTENT
    assert result.observed_state == "approved"


def test_m34_6_rejected_consistent():
    result = OperationalControlReconciliationRuntime.reconcile(
        make_outcome(OperationalControlOutcome.REJECTED),
        "rejected",
    )

    assert result.state == OperationalControlReconciliationState.CONSISTENT


def test_m34_6_detects_divergence():
    result = OperationalControlReconciliationRuntime.reconcile(
        make_outcome(),
        "rejected",
    )

    assert result.state == OperationalControlReconciliationState.DIVERGED
    assert result.observed_state == "rejected"


def test_m34_6_preserves_identity():
    result = OperationalControlReconciliationRuntime.reconcile(
        make_outcome(),
        "approved",
    )

    assert result.decision_id == "decision-m34-6"
    assert result.plan_id == "plan-m34-6"
    assert result.orchestration_id == "orchestration-m34-6"


def test_m34_6_never_becomes_executable():
    for observed in (None, "approved", "rejected"):
        result = OperationalControlReconciliationRuntime.reconcile(
            make_outcome(),
            observed,
        )

        assert result.executable is False


def test_m34_6_rejects_missing_decision_id():
    outcome = make_outcome()
    outcome = OperationalControlOutcomeResult(
        decision_id="",
        plan_id=outcome.plan_id,
        orchestration_id=outcome.orchestration_id,
        previous_state=outcome.previous_state,
        outcome=outcome.outcome,
        recorded_at=outcome.recorded_at,
        requires_human_approval=outcome.requires_human_approval,
        execution_handoff_available=outcome.execution_handoff_available,
        executable=False,
        metadata=outcome.metadata,
    )

    with pytest.raises(ValueError):
        OperationalControlReconciliationRuntime.reconcile(outcome)


def test_m34_6_rejects_empty_observation():
    with pytest.raises(ValueError):
        OperationalControlReconciliationRuntime.reconcile(
            make_outcome(),
            "   ",
        )
