from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.operational_control_lifecycle import (
    OperationalControlLifecycle,
    OperationalControlLifecycleState,
)
from yoma.office.intelligence.operational_control_outcome import (
    OperationalControlOutcome,
    OperationalControlOutcomeRuntime,
)


def make_lifecycle():
    now = datetime.now(timezone.utc)

    return OperationalControlLifecycle(
        decision_id="decision-m34-5",
        plan_id="plan-m34-5",
        orchestration_id="orchestration-m34-5",
        state=OperationalControlLifecycleState.AWAITING_APPROVAL,
        created_at=now,
        updated_at=now,
        requires_human_approval=True,
        executable=False,
        metadata={"test": True},
    )


def test_m34_5_approved_outcome():
    result = OperationalControlOutcomeRuntime.record(
        make_lifecycle(),
        OperationalControlOutcome.APPROVED,
    )

    assert result.decision_id == "decision-m34-5"
    assert result.plan_id == "plan-m34-5"
    assert result.orchestration_id == "orchestration-m34-5"
    assert result.previous_state == (
        OperationalControlLifecycleState.AWAITING_APPROVAL
    )
    assert result.outcome == OperationalControlOutcome.APPROVED
    assert result.requires_human_approval is False
    assert result.execution_handoff_available is True
    assert result.executable is False


def test_m34_5_rejected_outcome():
    result = OperationalControlOutcomeRuntime.record(
        make_lifecycle(),
        OperationalControlOutcome.REJECTED,
    )

    assert result.outcome == OperationalControlOutcome.REJECTED
    assert result.requires_human_approval is False
    assert result.execution_handoff_available is False
    assert result.executable is False


def test_m34_5_preserves_identity():
    result = OperationalControlOutcomeRuntime.record(
        make_lifecycle(),
        OperationalControlOutcome.APPROVED,
    )

    assert result.decision_id == "decision-m34-5"
    assert result.plan_id == "plan-m34-5"
    assert result.orchestration_id == "orchestration-m34-5"


def test_m34_5_never_marks_itself_executable():
    for outcome in (
        OperationalControlOutcome.APPROVED,
        OperationalControlOutcome.REJECTED,
    ):
        result = OperationalControlOutcomeRuntime.record(
            make_lifecycle(),
            outcome,
        )

        assert result.executable is False


def test_m34_5_rejects_non_pending_lifecycle():
    lifecycle = make_lifecycle()
    lifecycle = lifecycle.transition(
        OperationalControlLifecycleState.REJECTED
    )

    with pytest.raises(ValueError):
        OperationalControlOutcomeRuntime.record(
            lifecycle,
            OperationalControlOutcome.APPROVED,
        )


def test_m34_5_approved_handoff_points_to_existing_bridge():
    result = OperationalControlOutcomeRuntime.record(
        make_lifecycle(),
        OperationalControlOutcome.APPROVED,
    )

    assert (
        result.metadata["execution_owner"]
        == "existing_approval_execution_bridge"
    )


def test_m34_5_rejected_has_no_execution_handoff():
    result = OperationalControlOutcomeRuntime.record(
        make_lifecycle(),
        OperationalControlOutcome.REJECTED,
    )

    assert result.execution_handoff_available is False
    assert result.metadata["execution_owner"] is None
