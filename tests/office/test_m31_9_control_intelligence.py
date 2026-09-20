from datetime import datetime, timezone

from yoma.office.control_intelligence import (
    ControlIntelligenceResult,
    ControlIntelligenceRuntime,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_decision():
    return DecisionIntelligence(
        decision_id="DINT-M31-9",
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-M31-9",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M31-9",
                evidence_type="current_signal",
                source_id="SIG-M31-9",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )


def test_full_control_pipeline():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    assert isinstance(result, ControlIntelligenceResult)

    assert result.plan_count == 1
    assert result.simulation_count == 1
    assert result.what_if.alternative_count == 1
    assert result.policy_check_count == 1
    assert result.dependency_map_count == 1
    assert result.approval_count == 1

    assert result.approval_workflows[0].pending is True
    assert result.requires_human_approval is True
    assert result.executable is False


def test_policy_and_dependencies_are_connected():
    result = ControlIntelligenceRuntime().analyze(
        make_decision()
    )

    assert result.policy_checks[0].plan_id == (
        result.plans[0].plan_id
    )

    assert result.dependencies[0].plan_id == (
        result.plans[0].plan_id
    )

    assert result.dependencies[0].dependency_count >= 2


def test_approval_then_observation_then_learning():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    result = runtime.approve_plan(
        result,
        plan_index=0,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
        comment="Approved for pilot.",
    )

    assert result.approval_workflows[0].approved is True

    result = runtime.observe(
        result,
        plan_index=0,
        observed_at=NOW,
        outcome_status="observed",
        description="Workload response observed.",
        event_ids=("EV-M31-9",),
    )

    assert result.observation_count == 1
    assert result.observations[0].complete is True

    result = runtime.learn(
        result,
        plan_index=0,
    )

    assert result.learning_count == 1
    assert result.learning_results[0].learning_available is True


def test_learning_uses_matching_plan():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    result = runtime.approve_plan(
        result,
        0,
        "MANAGER-1",
        NOW,
    )

    result = runtime.observe(
        result,
        0,
        NOW,
        "observed",
        "Observed.",
        ("EV-M31-9B",),
    )

    result = runtime.learn(result, 0)

    learning = result.learning_results[0]

    assert learning.plan_id == result.plans[0].plan_id
    assert learning.decision_id == result.decision.decision_id


def test_last_result_tracks_pipeline():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    assert runtime.last_result is result

    result = runtime.approve_plan(
        result,
        0,
        "MANAGER-1",
        NOW,
    )

    assert runtime.last_result is result


def test_no_execution_surface():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    assert result.executable is False
    assert not hasattr(runtime, "execute")
    assert not hasattr(result, "execute")


def test_human_approval_remains_required():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    assert result.requires_human_approval is True

    result = runtime.approve_plan(
        result,
        0,
        "MANAGER-1",
        NOW,
    )

    assert result.requires_human_approval is True


def test_unapproved_plan_cannot_be_observed():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    try:
        runtime.observe(
            result,
            0,
            NOW,
            "observed",
            "Should fail.",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "unapproved plan was allowed into observation"
        )


def test_learning_requires_observation():
    runtime = ControlIntelligenceRuntime()

    result = runtime.analyze(make_decision())

    try:
        runtime.learn(result, 0)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "learning occurred without observation"
        )


def test_pipeline_is_deterministic():
    runtime = ControlIntelligenceRuntime()

    first = runtime.analyze(make_decision())
    second = runtime.analyze(make_decision())

    assert first.plans == second.plans
    assert first.simulations == second.simulations
    assert first.what_if == second.what_if
    assert first.dependencies == second.dependencies
