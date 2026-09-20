from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.workforce_organization import (
    WorkforceOrganizationContext,
    WorkforceOrganizationContextResolver,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


def make_resolver():
    organization = Organization(
        organization_id="ORG-001",
        name="Acme",
    )

    location = Location(
        location_id="LOC-001",
        organization_id="ORG-001",
        name="Chennai",
    )

    department = Department(
        department_id="DEP-001",
        organization_id="ORG-001",
        name="Engineering",
        location_id="LOC-001",
    )

    team = Team(
        team_id="TEAM-001",
        organization_id="ORG-001",
        name="Platform",
        department_id="DEP-001",
    )

    employee = Employee(
        employee_id="EMP-001",
        name="Employee One",
        organization_id="ORG-001",
        department_id="DEP-001",
        team_id="TEAM-001",
        location_id="LOC-001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        locations=[location],
        departments=[department],
        teams=[team],
        employees=[employee],
    )

    return WorkforceOrganizationContextResolver(graph)


def test_resolver_returns_workforce_organization_context():
    resolver = make_resolver()

    context = resolver.resolve("EMP-001")

    assert isinstance(context, WorkforceOrganizationContext)
    assert context.employee_id == "EMP-001"
    assert context.team.node_id == "TEAM-001"
    assert context.department.node_id == "DEP-001"
    assert context.location.node_id == "LOC-001"
    assert context.organization.node_id == "ORG-001"


def test_resolver_returns_empty_dimensions_for_unknown_employee():
    resolver = make_resolver()

    context = resolver.resolve("UNKNOWN")

    assert context.employee_id == "UNKNOWN"
    assert context.team is None
    assert context.department is None
    assert context.location is None
    assert context.organization is None


def test_resolver_rejects_invalid_employee_id():
    resolver = make_resolver()

    try:
        resolver.resolve("")
    except ValueError as exc:
        assert str(exc) == "employee_id must be a non-empty string"
    else:
        raise AssertionError("Expected ValueError")


def test_resolver_does_not_mutate_graph():
    resolver = make_resolver()

    before = resolver._graph.snapshot()
    resolver.resolve("EMP-001")
    after = resolver._graph.snapshot()

    assert before == after
