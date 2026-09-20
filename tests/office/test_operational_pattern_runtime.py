from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.operational_situation_context_runtime import (
    OperationalSituationContextResult,
)
from yoma.office.intelligence.operational_pattern_runtime import (
    OperationalPatternRuntime,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Organization,
    Team,
)
from yoma.office.operations import (
    OperationalSituation,
    OperationalSituationContext,
    OperationalPattern,
)


def make_graph():
    return OrganizationGraph(
        organizations=[
            Organization(
                organization_id="ORG001",
                name="YOMA Corp",
            )
        ],
        departments=[
            Department(
                department_id="DEP001",
                organization_id="ORG001",
                name="Engineering",
            )
        ],
        teams=[
            Team(
                team_id="TEAM001",
                organization_id="ORG001",
                name="AI Team",
                department_id="DEP001",
            )
        ],
        employees=[
            Employee(
                employee_id="U001",
                name="Employee One",
                organization_id="ORG001",
                department_id="DEP001",
                team_id="TEAM001",
            ),
            Employee(
                employee_id="U002",
                name="Employee Two",
                organization_id="ORG001",
                department_id="DEP001",
                team_id="TEAM001",
            ),
        ],
    )


def make_situation(
    situation_id: str,
    user_id: str,
    score: float = 0.8,
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id=user_id,
        severity="high",
        score=score,
        signal_ids=(f"SIG-{situation_id}",),
        evidence_event_ids=(f"EV-{situation_id}",),
    )


def make_context(
    situation_id: str,
    user_id: str,
    score: float = 0.8,
):
    situation = make_situation(
        situation_id,
        user_id,
        score,
    )

    return OperationalSituationContext(
        situation=situation,
        employee_id=user_id,
        team=make_graph().node("TEAM001"),
        department=make_graph().node("DEP001"),
        organization=make_graph().node("ORG001"),
    )


def make_result(contexts):
    return OperationalSituationContextResult(
        situations=tuple(
            context.situation
            for context in contexts
        ),
        contexts=tuple(contexts),
    )


def test_pattern_runtime_correlates_shared_team():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
        make_context("SIT002", "U002"),
    ]

    result = runtime.process(make_result(contexts))

    assert len(result.contexts) == 2
    assert any(pattern.correlation_dimension == "team" and pattern.correlation_id == "TEAM001" for pattern in result.patterns)

    pattern = result.patterns[0]

    assert pattern.pattern_type == "cross_situation"
    assert pattern.correlation_dimension == "team"
    assert pattern.correlation_id == "TEAM001"


def test_pattern_runtime_preserves_contexts():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
        make_context("SIT002", "U002"),
    ]

    result = runtime.process(make_result(contexts))

    assert result.contexts == tuple(contexts)


def test_pattern_runtime_preserves_situation_ids():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
        make_context("SIT002", "U002"),
    ]

    result = runtime.process(make_result(contexts))

    assert result.patterns[0].situation_ids == (
        "SIT001",
        "SIT002",
    )


def test_pattern_runtime_preserves_signal_and_event_evidence():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
        make_context("SIT002", "U002"),
    ]

    result = runtime.process(make_result(contexts))

    pattern = result.patterns[0]

    assert pattern.signal_ids == (
        "SIG-SIT001",
        "SIG-SIT002",
    )
    assert pattern.evidence_event_ids == (
        "EV-SIT001",
        "EV-SIT002",
    )


def test_pattern_runtime_does_not_create_pattern_for_single_context():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
    ]

    result = runtime.process(make_result(contexts))

    assert result.patterns == ()


def test_pattern_runtime_handles_empty_result():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    result = runtime.process(make_result([]))

    assert result.contexts == ()
    assert result.patterns == ()


def test_pattern_runtime_rejects_invalid_input():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    with pytest.raises(TypeError):
        runtime.process("invalid")


def test_pattern_runtime_rejects_invalid_graph():
    with pytest.raises(TypeError):
        OperationalPatternRuntime(
            graph="invalid"
        )


def test_pattern_runtime_tracks_last_result():
    runtime = OperationalPatternRuntime(
        graph=make_graph()
    )

    contexts = [
        make_context("SIT001", "U001"),
        make_context("SIT002", "U002"),
    ]

    result = runtime.process(make_result(contexts))

    assert runtime.last_result is result
