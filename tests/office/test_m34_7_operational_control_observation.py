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
from yoma.office.intelligence.operational_control_observation import (
    OperationalControlObservationRuntime,
)


def make_outcome():
    return OperationalControlOutcomeResult(
        decision_id="decision-m34-7",
        plan_id="plan-m34-7",
        orchestration_id="orchestration-m34-7",
        previous_state=None,
        outcome=OperationalControlOutcome.APPROVED,
        recorded_at=datetime.now(timezone.utc),
        requires_human_approval=False,
        execution_handoff_available=True,
        executable=False,
        metadata={"test": True},
    )


def make_reconciliation(observed="approved"):
    return OperationalControlReconciliationRuntime.reconcile(
        make_outcome(),
        observed,
    )


def test_m34_7_creates_observation():
    result = OperationalControlObservationRuntime.observe(
        make_reconciliation()
    )

    assert result.decision_id == "decision-m34-7"
    assert result.plan_id == "plan-m34-7"
    assert result.orchestration_id == "orchestration-m34-7"
    assert result.observed_state == "approved"


def test_m34_7_preserves_reconciliation_state():
    reconciliation = make_reconciliation()

    result = OperationalControlObservationRuntime.observe(
        reconciliation
    )

    assert (
        result.reconciliation_state
        == OperationalControlReconciliationState.CONSISTENT
    )


def test_m34_7_detects_diverged_observation():
    result = OperationalControlObservationRuntime.observe(
        make_reconciliation("rejected")
    )

    assert (
        result.reconciliation_state
        == OperationalControlReconciliationState.DIVERGED
    )
    assert result.observed_state == "rejected"


def test_m34_7_preserves_pending_observation():
    reconciliation = OperationalControlReconciliationRuntime.reconcile(
        make_outcome()
    )

    result = OperationalControlObservationRuntime.observe(
        reconciliation
    )

    assert result.reconciliation_state == (
        OperationalControlReconciliationState.PENDING
    )
    assert result.observed_state == "unknown"


def test_m34_7_never_allows_execution():
    for observed in (None, "approved", "rejected"):
        reconciliation = make_reconciliation(observed)

        result = OperationalControlObservationRuntime.observe(
            reconciliation
        )

        assert result.execution_allowed is False
        assert result.executable is False


def test_m34_7_observation_is_timestamped():
    result = OperationalControlObservationRuntime.observe(
        make_reconciliation()
    )

    assert result.observed_at.tzinfo is not None


def test_m34_7_preserves_identity():
    result = OperationalControlObservationRuntime.observe(
        make_reconciliation()
    )

    assert result.decision_id == "decision-m34-7"
    assert result.plan_id == "plan-m34-7"
    assert result.orchestration_id == "orchestration-m34-7"


def test_m34_7_rejects_missing_decision_id():
    reconciliation = make_reconciliation()

    invalid = type(reconciliation)(
        decision_id="",
        plan_id=reconciliation.plan_id,
        orchestration_id=reconciliation.orchestration_id,
        expected_outcome=reconciliation.expected_outcome,
        observed_state=reconciliation.observed_state,
        state=reconciliation.state,
        reconciled_at=reconciliation.reconciled_at,
        requires_human_approval=reconciliation.requires_human_approval,
        executable=False,
        metadata=reconciliation.metadata,
    )

    with pytest.raises(ValueError):
        OperationalControlObservationRuntime.observe(invalid)
