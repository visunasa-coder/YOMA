from datetime import datetime, timezone

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)
from yoma.office.operations.situation import OperationalSituation
from yoma.office.operations.situation_context import (
    OperationalSituationContext,
    OperationalSituationContextResolver,
)


def make_situation(
    *,
    situation_id="SIT-001",
    user_id="EMP001",
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
        organization_id="ORG001",
        user_id=user_id,
        severity="high",
        score=0.85,
        signal_ids=("SIG001",),
        evidence_event_ids=("EV001",),
    )


def make_graph():
    return OrganizationGraph(
        organizations=[
            Organization(
                organization_id="ORG001",
                name="YOMA Technologies",
            ),
        ],
        locations=[
            Location(
                location_id="LOC001",
                organization_id="ORG001",
                name="Chennai",
            ),
        ],
        departments=[
            Department(
                department_id="DEP001",
                organization_id="ORG001",
                name="Engineering",
                location_id="LOC001",
            ),
        ],
        teams=[
            Team(
                team_id="TEAM001",
                organization_id="ORG001",
                name="Platform",
                department_id="DEP001",
            ),
        ],
        employees=[
            Employee(
                employee_id="EMP001",
                name="Employee One",
                organization_id="ORG001",
                department_id="DEP001",
                team_id="TEAM001",
                location_id="LOC001",
            ),
        ],
    )


def test_resolves_full_organization_context():
    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    context = resolver.resolve(
        make_situation()
    )

    assert isinstance(context, OperationalSituationContext)
    assert context.situation_id == "SIT-001"
    assert context.employee_id == "EMP001"
    assert context.team.node_id == "TEAM001"
    assert context.department.node_id == "DEP001"
    assert context.location.node_id == "LOC001"
    assert context.organization.node_id == "ORG001"


def test_preserves_situation():
    situation = make_situation()

    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    context = resolver.resolve(situation)

    assert context.situation is situation


def test_missing_relationships_remain_none():
    graph = OrganizationGraph(
        organizations=[
            Organization(
                organization_id="ORG001",
                name="YOMA Technologies",
            ),
        ],
        employees=[
            Employee(
                employee_id="EMP001",
                name="Employee One",
                organization_id="ORG001",
            ),
        ],
    )

    resolver = OperationalSituationContextResolver(graph)

    context = resolver.resolve(
        make_situation()
    )

    assert context.team is None
    assert context.department is None
    assert context.location is None
    assert context.organization.node_id == "ORG001"


def test_unknown_employee_does_not_infer_context():
    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    context = resolver.resolve(
        make_situation(user_id="UNKNOWN")
    )

    assert context.employee_id == "UNKNOWN"
    assert context.team is None
    assert context.department is None
    assert context.location is None
    assert context.organization is None


def test_system_situation_has_no_employee_context():
    situation = OperationalSituation(
        situation_id="SIT-SYS-001",
        situation_type="system_incident",
        detected_at=datetime(
            2026,
            9,
            5,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        organization_id="ORG001",
        system_id="SYS001",
        severity="critical",
        score=0.95,
        signal_ids=("SIG100",),
        evidence_event_ids=("EV100",),
    )

    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    context = resolver.resolve(situation)

    assert context.employee_id is None
    assert context.team is None
    assert context.department is None
    assert context.location is None
    assert context.organization.node_id == "ORG001"


def test_resolver_requires_situation():
    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    try:
        resolver.resolve(None)
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError")


def test_resolution_is_deterministic():
    situation = make_situation()

    resolver = OperationalSituationContextResolver(
        make_graph()
    )

    first = resolver.resolve(situation)
    second = resolver.resolve(situation)

    assert first == second
