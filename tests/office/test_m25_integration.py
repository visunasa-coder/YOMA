from datetime import datetime, timezone

from yoma.office.intelligence import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import (
    Department,
    Employee,
    Organization,
    Team,
)
from yoma.office.operations import OperationalEvent


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


def make_event(
    event_id: str,
    user_id: str,
    score: float,
):
    return OperationalEvent(
        event_id=event_id,
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id=user_id,
        source="integration-test",
        data={"score": score},
    )


def make_runtime():
    engine = OperationalIntelligenceEngine()

    def workload_rule(events):
        from yoma.office.operations import OperationalSignal

        return [
            OperationalSignal(
                signal_id=f"SIG-{event.event_id}",
                signal_type="workload.high",
                detected_at=event.occurred_at,
                organization_id=event.organization_id,
                user_id=event.user_id,
                score=event.data["score"],
                severity="high",
                evidence_event_ids=(event.event_id,),
            )
            for event in events
            if event.event_type == "workload.high"
        ]

    engine.register_rule("workload", workload_rule)

    return OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=make_graph(),
    )


def test_m25_end_to_end_event_to_decision():
    runtime = make_runtime()

    result = runtime.process([
        make_event("EV001", "U001", 0.8),
        make_event("EV002", "U002", 0.9),
    ])

    assert len(result.events) == 2
    assert len(result.signals) == 2
    assert len(result.situations) == 2
    assert len(result.contexts) == 2

    assert any(
        pattern.correlation_dimension == "team"
        and pattern.correlation_id == "TEAM001"
        for pattern in result.patterns
    )

    assert len(result.decisions) >= 1


def test_m25_decisions_remain_human_approved():
    runtime = make_runtime()

    result = runtime.process([
        make_event("EV001", "U001", 0.8),
        make_event("EV002", "U002", 0.9),
    ])

    assert result.decisions

    assert all(
        decision.requires_human_approval is True
        for decision in result.decisions
    )

    assert all(
        decision.actions == ()
        for decision in result.decisions
    )


def test_m25_evidence_chain_is_preserved():
    runtime = make_runtime()

    result = runtime.process([
        make_event("EV001", "U001", 0.8),
        make_event("EV002", "U002", 0.9),
    ])

    assert {
        event.event_id
        for event in result.events
    } == {"EV001", "EV002"}

    assert {
        event_id
        for signal in result.signals
        for event_id in signal.evidence_event_ids
    } == {"EV001", "EV002"}

    assert {
        event_id
        for situation in result.situations
        for event_id in situation.evidence_event_ids
    } == {"EV001", "EV002"}

    assert {
        event_id
        for pattern in result.patterns
        for event_id in pattern.evidence_event_ids
    } == {"EV001", "EV002"}


def test_m25_no_signal_means_no_downstream_intelligence():
    runtime = make_runtime()

    event = OperationalEvent(
        event_id="EV999",
        event_type="attendance.check_in",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="U001",
        source="integration-test",
    )

    result = runtime.process([event])

    assert result.signals == ()
    assert result.situations == ()
    assert result.contexts == ()
    assert result.patterns == ()
    assert result.decisions == ()
