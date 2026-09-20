from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import (
    ActionPlan,
    ActionPlanEvidence,
    ActionPlanStep,
    ActionPlanningEngine,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


def make_decision():
    return DecisionIntelligence(
        decision_id="DINT-M31-1",
        decision_type="workload_review",
        created_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.85,
        current_intelligence_available=True,
        current_decision_ids=("DEC-1",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-1",
                evidence_type="current_signal",
                source_id="SIG-1",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.85},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )


def test_build_action_plan():
    plan = ActionPlanningEngine().build(make_decision())

    assert isinstance(plan, ActionPlan)
    assert plan.plan_id == "APLAN-DINT-M31-1"
    assert plan.decision_id == "DINT-M31-1"
    assert plan.priority == "high"
    assert plan.step_count == 1
    assert plan.requires_human_approval is True
    assert plan.executable is False


def test_step_is_deterministic():
    plan = ActionPlanningEngine().build(make_decision())

    step = plan.steps[0]

    assert step.step_id == "ASTEP-DINT-M31-1-1"
    assert step.sequence == 1
    assert step.action_type == "workload_review"
    assert step.target_user_id == "U1"
    assert step.target_system_id == "SYS1"
    assert step.requires_human_approval is True


def test_evidence_is_preserved():
    plan = ActionPlanningEngine().build(make_decision())

    assert plan.evidence_count == 1
    assert plan.evidence[0].evidence_id == "EVID-1"
    assert plan.evidence[0].source_id == "SIG-1"
    assert plan.steps[0].evidence_ids == ("EVID-1",)


def test_affected_entities_are_tracked():
    plan = ActionPlanningEngine().build(make_decision())

    assert plan.affected_user_ids == ("U1",)
    assert plan.affected_system_ids == ("SYS1",)


def test_priority_and_reason_are_preserved():
    plan = ActionPlanningEngine().build(make_decision())

    assert plan.priority == "high"
    assert plan.reason == "Review workload allocation."


def test_build_many():
    engine = ActionPlanningEngine()
    decisions = (make_decision(),)

    plans = engine.build_many(decisions)

    assert len(plans) == 1
    assert plans[0].decision_id == "DINT-M31-1"


def test_invalid_decision_type():
    with pytest.raises(TypeError):
        ActionPlanningEngine().build(object())


def test_plan_requires_approval():
    with pytest.raises(ValueError):
        ActionPlan(
            plan_id="APLAN-X",
            decision_id="DINT-X",
            created_at=datetime.now(timezone.utc),
            decision_type="test",
            priority="normal",
            reason="test",
            requires_human_approval=False,
        )


def test_step_requires_approval():
    with pytest.raises(ValueError):
        ActionPlanStep(
            step_id="ASTEP-X",
            sequence=1,
            action_type="test",
            description="test",
            requires_human_approval=False,
        )


def test_plan_has_no_execution_surface():
    plan = ActionPlanningEngine().build(make_decision())

    assert not hasattr(plan, "execute")
    assert not hasattr(ActionPlanningEngine, "execute")
    assert plan.executable is False
