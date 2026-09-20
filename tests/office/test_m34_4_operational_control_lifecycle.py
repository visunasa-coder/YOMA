from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from yoma.office.intelligence.operational_control_lifecycle import (
    OperationalControlLifecycle,
    OperationalControlLifecycleState,
)


def make_bridge_result():
    created_at = datetime.now(timezone.utc)

    operational = SimpleNamespace(
        created_at=created_at,
    )

    decision_intelligence = SimpleNamespace(
        decision_id="decision-m34-4",
    )

    unified_control = (
        SimpleNamespace(
            plan_id="plan-m34-4",
            orchestration_id="orchestration-m34-4",
        ),
    )

    return SimpleNamespace(
        operational=operational,
        decision_intelligence=decision_intelligence,
        unified_control=unified_control,
    )


def test_m34_4_creates_approval_pending_lifecycle():
    lifecycle = OperationalControlLifecycle.from_bridge_result(
        make_bridge_result()
    )

    assert lifecycle.decision_id == "decision-m34-4"
    assert lifecycle.plan_id == "plan-m34-4"
    assert lifecycle.orchestration_id == "orchestration-m34-4"
    assert lifecycle.state == OperationalControlLifecycleState.AWAITING_APPROVAL
    assert lifecycle.requires_human_approval is True
    assert lifecycle.executable is False


def test_m34_4_lifecycle_transition_order():
    lifecycle = OperationalControlLifecycle(
        decision_id="d1",
        plan_id="p1",
        orchestration_id="o1",
        state=OperationalControlLifecycleState.CREATED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        requires_human_approval=True,
        executable=False,
        metadata={},
    )

    lifecycle = lifecycle.transition(
        OperationalControlLifecycleState.ANALYZED
    )
    lifecycle = lifecycle.transition(
        OperationalControlLifecycleState.CONTROL_PLANNED
    )
    lifecycle = lifecycle.transition(
        OperationalControlLifecycleState.ORCHESTRATED
    )
    lifecycle = lifecycle.transition(
        OperationalControlLifecycleState.AWAITING_APPROVAL
    )

    assert lifecycle.state == OperationalControlLifecycleState.AWAITING_APPROVAL
    assert lifecycle.requires_human_approval is True
    assert lifecycle.executable is False


def test_m34_4_rejects_invalid_transition():
    lifecycle = OperationalControlLifecycle(
        decision_id="d1",
        plan_id="p1",
        orchestration_id="o1",
        state=OperationalControlLifecycleState.CREATED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        requires_human_approval=True,
        executable=False,
        metadata={},
    )

    with pytest.raises(ValueError):
        lifecycle.transition(
            OperationalControlLifecycleState.APPROVED
        )


def test_m34_4_approval_does_not_enable_execution():
    lifecycle = OperationalControlLifecycle(
        decision_id="d1",
        plan_id="p1",
        orchestration_id="o1",
        state=OperationalControlLifecycleState.AWAITING_APPROVAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        requires_human_approval=True,
        executable=False,
        metadata={},
    )

    approved = lifecycle.transition(
        OperationalControlLifecycleState.APPROVED
    )

    assert approved.state == OperationalControlLifecycleState.APPROVED
    assert approved.requires_human_approval is False
    assert approved.executable is False


def test_m34_4_rejects_missing_unified_control():
    bridge_result = make_bridge_result()
    bridge_result.unified_control = ()

    with pytest.raises(ValueError):
        OperationalControlLifecycle.from_bridge_result(bridge_result)


def test_m34_4_rejects_missing_decision_id():
    bridge_result = make_bridge_result()
    bridge_result.decision_intelligence.decision_id = ""

    with pytest.raises(ValueError):
        OperationalControlLifecycle.from_bridge_result(bridge_result)
