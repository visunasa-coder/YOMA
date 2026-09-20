from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.action_planning import ActionPlan
from yoma.office.control_intelligence import ControlIntelligenceResult
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.unified_control_runtime import (
    UnifiedControlRuntime,
    UnifiedControlRuntimeResult,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_decision():
    return DecisionIntelligence(
        decision_id="DINT-M34-2",
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-M34-2",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M34-2",
                evidence_type="current_signal",
                source_id="SIG-M34-2",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )


def run_runtime():
    runtime = UnifiedControlRuntime()

    return runtime.analyze(
        make_decision(),
        scheduled_at=NOW + timedelta(hours=1),
        created_at=NOW,
    )


def test_m34_runtime_composes_m31_and_m33():
    result = run_runtime()

    assert isinstance(
        result,
        UnifiedControlRuntimeResult,
    )

    assert isinstance(
        result.control_intelligence,
        ControlIntelligenceResult,
    )

    assert isinstance(
        result.selected_plan,
        ActionPlan,
    )

    assert len(result.orchestration) == 1

    assert (
        result.selected_plan.decision_id
        == result.decision_id
    )

    assert (
        result.selected_orchestration.execution_plan_id
        == result.selected_plan.plan_id
        or result.selected_orchestration.orchestration.decision_id
        == result.selected_plan.decision_id
    )


def test_m34_runtime_preserves_approval_boundary():
    result = run_runtime()

    assert result.requires_human_approval is True
    assert result.control_intelligence.requires_human_approval is True

    assert result.selected_orchestration.requires_human_approval is True
    assert result.selected_orchestration.approval_pending_count >= 1


def test_m34_runtime_is_not_executable():
    result = run_runtime()
    runtime = UnifiedControlRuntime()

    assert runtime.executable is False
    assert runtime.requires_human_approval is True

    assert result.executable is False
    assert result.selected_orchestration.executable is False
    assert result.selected_orchestration.execution_plan.executable is False


def test_m34_runtime_exposes_no_execute_method():
    runtime = UnifiedControlRuntime()
    result = run_runtime()

    assert not hasattr(runtime, "execute")
    assert not hasattr(result, "execute")


def test_m34_runtime_tracks_last_result():
    runtime = UnifiedControlRuntime()

    result = runtime.analyze(
        make_decision(),
        scheduled_at=NOW + timedelta(hours=1),
        created_at=NOW,
    )

    assert runtime.last_result is result


def test_m34_runtime_rejects_naive_schedule_timestamp():
    runtime = UnifiedControlRuntime()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        runtime.analyze(
            make_decision(),
            scheduled_at=datetime.now(),
            created_at=NOW,
        )


def test_m34_runtime_rejects_naive_created_timestamp():
    runtime = UnifiedControlRuntime()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        runtime.analyze(
            make_decision(),
            scheduled_at=NOW + timedelta(hours=1),
            created_at=datetime.now(),
        )


def test_m34_runtime_rejects_invalid_decision():
    runtime = UnifiedControlRuntime()

    with pytest.raises(
        TypeError,
        match="DecisionIntelligence",
    ):
        runtime.analyze(
            object(),
            scheduled_at=NOW + timedelta(hours=1),
            created_at=NOW,
        )


def test_m34_runtime_rejects_invalid_selected_plan():
    runtime = UnifiedControlRuntime()

    with pytest.raises(
        IndexError,
        match="selected_plan_index",
    ):
        runtime.analyze(
            make_decision(),
            scheduled_at=NOW + timedelta(hours=1),
            created_at=NOW,
            selected_plan_index=99,
        )


def test_m34_runtime_preserves_decision_identity():
    result = run_runtime()

    assert result.decision_id == "DINT-M34-2"
    assert result.control_intelligence.decision.decision_id == (
        result.decision_id
    )

    assert result.selected_plan.decision_id == (
        result.decision_id
    )


def test_m34_runtime_creates_pending_orchestration_approval():
    result = run_runtime()

    orchestration = result.selected_orchestration

    assert len(orchestration.approval_items) == 1

    approval = orchestration.approval_items[0]

    assert approval.status == "pending"
    assert approval.requires_human_approval is True
    assert approval.executable is False
