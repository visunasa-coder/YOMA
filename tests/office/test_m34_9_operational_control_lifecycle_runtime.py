from datetime import datetime, timezone

from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedResult,
)
from yoma.office.intelligence.operational_control_lifecycle_runtime import (
    OperationalControlLifecycleRuntime,
)
from yoma.office.intelligence.operational_control_outcome import (
    OperationalControlOutcome,
)
from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.operations.model import OperationalSignal

BASE = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_signal():
    return OperationalSignal(
        signal_id="SIG-1",
        signal_type="workload.high",
        detected_at=BASE,
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        score=0.80,
        severity="high",
        evidence_event_ids=("EV1",),
    )


def make_decision():
    return DecisionContext(
        signal=make_signal(),
        recommendations=(
            {
                "type": "workload_review",
                "reason": "Operational workload signal requires human review.",
            },
        ),
        actions=(),
        requires_human_approval=True,
    )


def make_operational_result():
    return OperationalUnifiedResult(
        events=(),
        signals=(make_signal(),),
        situations=(),
        contexts=(),
        patterns=(),
        decisions=(make_decision(),),
    )


def process(**kwargs):
    return OperationalControlLifecycleRuntime().process(
        make_operational_result(),
        scheduled_at=BASE,
        created_at=BASE,
        **kwargs,
    )


def test_m34_9_creates_complete_lifecycle():
    result = process()
    assert result.bridge is not None
    assert result.lifecycle is not None
    assert result.outcome is None
    assert result.reconciliation is None
    assert result.observation is None
    assert result.learning is None
    assert result.lifecycle.state.value == "awaiting_approval"
    assert result.lifecycle.requires_human_approval is True
    assert result.executable is False


def test_m34_9_composes_approved_path():
    result = process(
        outcome=OperationalControlOutcome.APPROVED,
        observed_state="approved",
    )
    assert result.outcome is not None
    assert result.reconciliation is not None
    assert result.observation is not None
    assert result.learning is not None
    assert result.reconciliation.state.value == "consistent"
    assert result.learning.learning_signal == "control_outcome_consistent"
    assert result.executable is False


def test_m34_9_composes_rejected_path():
    result = process(
        outcome=OperationalControlOutcome.REJECTED,
        observed_state="rejected",
    )
    assert result.outcome is not None
    assert result.reconciliation is not None
    assert result.observation is not None
    assert result.learning is not None
    assert result.reconciliation.state.value == "consistent"
    assert result.learning.learning_signal == "control_outcome_consistent"
    assert result.executable is False


def test_m34_9_detects_divergence():
    result = process(
        outcome=OperationalControlOutcome.APPROVED,
        observed_state="rejected",
    )
    assert result.reconciliation is not None
    assert result.reconciliation.state.value == "diverged"
    assert result.learning is not None
    assert result.learning.learning_signal == "control_outcome_diverged"
    assert result.executable is False


def test_m34_9_preserves_identity():
    result = process(
        outcome=OperationalControlOutcome.APPROVED,
        observed_state="approved",
    )
    assert result.lifecycle.decision_id == result.outcome.decision_id
    assert result.lifecycle.decision_id == result.reconciliation.decision_id
    assert result.lifecycle.decision_id == result.observation.decision_id
    assert result.lifecycle.decision_id == result.learning.decision_id
    assert result.lifecycle.plan_id == result.outcome.plan_id
    assert result.lifecycle.plan_id == result.reconciliation.plan_id
    assert result.lifecycle.plan_id == result.observation.plan_id
    assert result.lifecycle.plan_id == result.learning.plan_id
    assert result.lifecycle.orchestration_id == result.outcome.orchestration_id
    assert result.lifecycle.orchestration_id == result.reconciliation.orchestration_id
    assert result.lifecycle.orchestration_id == result.observation.orchestration_id
    assert result.lifecycle.orchestration_id == result.learning.orchestration_id


def test_m34_9_never_becomes_executable():
    for outcome, observed in (
        (None, None),
        (OperationalControlOutcome.APPROVED, "approved"),
        (OperationalControlOutcome.REJECTED, "rejected"),
        (OperationalControlOutcome.APPROVED, "rejected"),
    ):
        result = process(outcome=outcome, observed_state=observed)
        assert result.executable is False
        if result.outcome:
            assert result.outcome.executable is False
        if result.reconciliation:
            assert result.reconciliation.executable is False
        if result.observation:
            assert result.observation.executable is False
        if result.learning:
            assert result.learning.executable is False


def test_m34_9_is_composition_only():
    result = process()
    assert result.metadata["source"] == "M34.9"
    assert result.metadata["composition_only"] is True


def test_m34_9_learning_handoff_preserved():
    result = process(
        outcome=OperationalControlOutcome.APPROVED,
        observed_state="approved",
    )
    assert result.learning is not None
    assert result.learning.metadata["learning_owner"] == (
        "existing_outcome_learning"
    )
