from datetime import datetime, timezone

import pytest

from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Organization,
    Team,
)
from yoma.office.operations import OperationalEvent
from yoma.office.intelligence.organization_graph import OrganizationGraph


def event(
    event_id: str,
    event_type: str,
    user_id: str,
    score: float,
):
    return OperationalEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id=user_id,
        source="test",
        data={"score": score},
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


def make_runtime():
    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    return OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=make_graph(),
    )


def test_unified_runtime_processes_event_to_signal():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.9,
        )
    ])

    assert len(result.events) == 1
    assert len(result.signals) == 1


def test_unified_runtime_processes_event_to_situation():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.9,
        )
    ])

    assert len(result.situations) == 1
    assert result.situations[0].user_id == "U001"


def test_unified_runtime_resolves_context():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.9,
        )
    ])

    assert len(result.contexts) == 1
    assert result.contexts[0].employee_id == "U001"
    assert result.contexts[0].team.node_id == "TEAM001"


def test_unified_runtime_handles_multiple_users():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.8,
        ),
        event(
            "EV002",
            "workload.high",
            "U002",
            0.9,
        ),
    ])

    assert len(result.signals) == 2
    assert len(result.situations) == 2
    assert len(result.contexts) == 2


def test_unified_runtime_creates_cross_situation_pattern():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.8,
        ),
        event(
            "EV002",
            "workload.high",
            "U002",
            0.9,
        ),
    ])

    assert len(result.patterns) >= 1
    assert any(
        pattern.correlation_dimension == "team"
        and pattern.correlation_id == "TEAM001"
        for pattern in result.patterns
    )


def test_unified_runtime_creates_advisory_decision():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.8,
        ),
        event(
            "EV002",
            "workload.high",
            "U002",
            0.9,
        ),
    ])

    assert len(result.decisions) >= 1
    assert all(
        decision.requires_human_approval
        for decision in result.decisions
    )


def test_unified_runtime_preserves_evidence_chain():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.9,
        )
    ])

    assert result.events[0].event_id == "EV001"
    assert result.signals[0].evidence_event_ids == ("EV001",)
    assert result.situations[0].evidence_event_ids == ("EV001",)


def test_unified_runtime_handles_no_signal_events():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "attendance.check_in",
            "U001",
            0.0,
        )
    ])

    assert result.signals == ()
    assert result.situations == ()
    assert result.contexts == ()
    assert result.patterns == ()
    assert result.decisions == ()


def test_unified_runtime_rejects_invalid_events():
    runtime = make_runtime()

    with pytest.raises(TypeError):
        runtime.process(["invalid"])


def test_unified_runtime_tracks_last_result():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            "U001",
            0.9,
        )
    ])

    assert runtime.last_result is result
