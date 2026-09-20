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
        organization_id="ORG001",
        name="Test Company",
    )

    location = Location(
        location_id="LOC001",
        organization_id="ORG001",
        name="Coimbatore",
    )

    department = Department(
        department_id="DEP001",
        organization_id="ORG001",
        name="Engineering",
        location_id="LOC001",
        manager_employee_id="EMP001",
    )

    team = Team(
        team_id="TEAM001",
        organization_id="ORG001",
        name="Platform",
        department_id="DEP001",
        manager_employee_id="EMP001",
    )

    manager = Employee(
        employee_id="EMP001",
        name="Manager",
        organization_id="ORG001",
        department_id="DEP001",
        team_id="TEAM001",
        location_id="LOC001",
    )

    employee = Employee(
        employee_id="EMP002",
        name="Engineer",
        organization_id="ORG001",
        department_id="DEP001",
        team_id="TEAM001",
        location_id="LOC001",
        manager_employee_id="EMP001",
    )

    return OrganizationGraph(
        organizations=[organization],
        locations=[location],
        departments=[department],
        teams=[team],
        employees=[manager, employee],
    )


def test_members_of_team():
    graph = build_graph()

    members = graph.members_of("TEAM001")

    assert {member.node_id for member in members} == {
        "EMP001",
        "EMP002",
    }


def test_members_of_department():
    graph = build_graph()

    members = graph.members_of("DEP001")

    assert {member.node_id for member in members} == {
        "EMP001",
        "EMP002",
    }


def test_reports_to():
    graph = build_graph()

    manager = graph.reports_to("EMP002")

    assert manager is not None
    assert manager.node_id == "EMP001"


def test_manager_of_department_and_team():
    graph = build_graph()

    department_manager = graph.manager_of("DEP001")
    team_manager = graph.manager_of("TEAM001")

    assert department_manager is not None
    assert department_manager.node_id == "EMP001"

    assert team_manager is not None
    assert team_manager.node_id == "EMP001"


def test_employee_organizational_dimensions():
    graph = build_graph()

    department = graph.department_of("EMP002")
    team = graph.team_of("EMP002")
    location = graph.location_of("EMP002")
    organization = graph.organization_of("EMP002")

    assert department is not None
    assert department.node_id == "DEP001"

    assert team is not None
    assert team.node_id == "TEAM001"

    assert location is not None
    assert location.node_id == "LOC001"

    assert organization is not None
    assert organization.node_id == "ORG001"


def test_organizational_path():
    graph = build_graph()

    path = graph.organizational_path("EMP002")

    assert [node.node_id for node in path] == [
        "EMP002",
        "TEAM001",
        "DEP001",
        "ORG001",
    ]


def test_queries_return_empty_for_unknown_employee():
    graph = build_graph()

    assert graph.reports_to("UNKNOWN") is None
    assert graph.department_of("UNKNOWN") is None
    assert graph.team_of("UNKNOWN") is None
    assert graph.location_of("UNKNOWN") is None
    assert graph.organization_of("UNKNOWN") is None
    assert graph.organizational_path("UNKNOWN") == []
