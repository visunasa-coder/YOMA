from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.policy_constraints import (
    PolicyCheckResult,
    PolicyConstraint,
    PolicyConstraintEngine,
)


def make_plan():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-4",
        decision_type="workload_review",
        created_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-1",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M31-4",
                evidence_type="current_signal",
                source_id="SIG-M31-4",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    return ActionPlanningEngine().build(decision)


def test_policy_constraint():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-1",
        constraint_type="action_type",
        description="Workload reviews are allowed.",
        allowed=True,
        action_types=("workload_review",),
    )

    assert constraint.constraint_id == "POL-M31-4-1"
    assert constraint.allowed is True


def test_allowed_plan():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-2",
        constraint_type="action_type",
        description="Workload reviews are allowed.",
        allowed=True,
        action_types=("workload_review",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert isinstance(result, PolicyCheckResult)
    assert result.status == "allowed"
    assert result.allowed is True
    assert result.blocked is False
    assert result.passed_count == 1
    assert result.failed_count == 0


def test_blocked_plan():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-3",
        constraint_type="action_type",
        description="Workload reviews are currently restricted.",
        allowed=False,
        action_types=("workload_review",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert result.status == "blocked"
    assert result.blocked is True
    assert result.failed_count == 1
    assert result.failed_constraint_ids == ("POL-M31-4-3",)


def test_priority_constraint():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-4",
        constraint_type="priority",
        description="Only critical actions are allowed.",
        allowed=False,
        priorities=("high",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert result.blocked is True


def test_unmatched_constraint_does_not_block():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-5",
        constraint_type="action_type",
        description="Payroll actions are restricted.",
        allowed=False,
        action_types=("payroll_change",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert result.allowed is True
    assert result.failed_count == 0
    assert result.passed_count == 1


def test_system_constraint():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-6",
        constraint_type="system",
        description="SYS1 actions are restricted.",
        allowed=False,
        system_ids=("SYS1",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert result.blocked is True


def test_multiple_constraints():
    constraints = (
        PolicyConstraint(
            constraint_id="POL-M31-4-7",
            constraint_type="action_type",
            description="Workload review allowed.",
            allowed=True,
            action_types=("workload_review",),
        ),
        PolicyConstraint(
            constraint_id="POL-M31-4-8",
            constraint_type="system",
            description="SYS1 restricted.",
            allowed=False,
            system_ids=("SYS1",),
        ),
    )

    result = PolicyConstraintEngine(constraints).evaluate(make_plan())

    assert result.status == "blocked"
    assert result.passed_count == 1
    assert result.failed_count == 1


def test_human_approval_required():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-9",
        constraint_type="action_type",
        description="Review required.",
        allowed=True,
        action_types=("workload_review",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert result.requires_human_approval is True


def test_policy_check_is_not_execution():
    constraint = PolicyConstraint(
        constraint_id="POL-M31-4-10",
        constraint_type="action_type",
        description="Allowed.",
        allowed=True,
        action_types=("workload_review",),
    )

    result = PolicyConstraintEngine((constraint,)).evaluate(make_plan())

    assert not hasattr(result, "execute")
    assert not hasattr(PolicyConstraintEngine, "execute")


def test_invalid_input():
    with pytest.raises(TypeError):
        PolicyConstraintEngine().evaluate(object())
