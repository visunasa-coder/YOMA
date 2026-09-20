from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


def build_graph():
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

    return OrganizationGraph(
        organizations=[organization],
        locations=[location],
        departments=[department],
        teams=[team],
        employees=[employee],
    )


def test_workforce_context_resolves_employee_organization_dimensions():
    graph = build_graph()

    assert graph.team_of("EMP-001").node_id == "TEAM-001"
    assert graph.department_of("EMP-001").node_id == "DEP-001"
    assert graph.location_of("EMP-001").node_id == "LOC-001"
    assert graph.organization_of("EMP-001").node_id == "ORG-001"


def test_workforce_context_does_not_infer_from_employee_name():
    graph = build_graph()

    assert graph.node("Employee One") is None


def test_workforce_context_handles_unknown_employee():
    graph = build_graph()

    assert graph.team_of("UNKNOWN") is None
    assert graph.department_of("UNKNOWN") is None
    assert graph.location_of("UNKNOWN") is None
    assert graph.organization_of("UNKNOWN") is None
