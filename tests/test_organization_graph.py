from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


def test_organization_graph_builds_nodes_and_relationships():
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

    graph = OrganizationGraph(
        organizations=[organization],
        locations=[location],
        departments=[department],
        teams=[team],
        employees=[manager, employee],
    )

    assert len(graph.nodes()) == 6

    edges = graph.edges()

    assert any(
        e.source_id == "LOC001"
        and e.relationship == "BELONGS_TO"
        and e.target_id == "ORG001"
        for e in edges
    )

    assert any(
        e.source_id == "DEP001"
        and e.relationship == "BELONGS_TO"
        and e.target_id == "ORG001"
        for e in edges
    )

    assert any(
        e.source_id == "DEP001"
        and e.relationship == "LOCATED_AT"
        and e.target_id == "LOC001"
        for e in edges
    )

    assert any(
        e.source_id == "TEAM001"
        and e.relationship == "PART_OF"
        and e.target_id == "DEP001"
        for e in edges
    )

    assert any(
        e.source_id == "EMP002"
        and e.relationship == "MEMBER_OF"
        and e.target_id == "TEAM001"
        for e in edges
    )

    assert any(
        e.source_id == "EMP002"
        and e.relationship == "REPORTS_TO"
        and e.target_id == "EMP001"
        for e in edges
    )


def test_organization_graph_relationship_filtering():
    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG001",
    )

    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    relationships = graph.relationships(
        node_id="EMP001",
        relationship="BELONGS_TO",
    )

    assert len(relationships) == 1
    assert relationships[0].target_id == "ORG001"


def test_organization_graph_children():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    department = Department(
        department_id="DEP001",
        organization_id="ORG001",
        name="Engineering",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        departments=[department],
    )

    children = graph.children(
        "DEP001",
        relationship="BELONGS_TO",
    )

    assert len(children) == 1
    assert children[0].node_id == "ORG001"


def test_organization_graph_does_not_infer_missing_relationships():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG001",
        department_id="MISSING_DEP",
        team_id="MISSING_TEAM",
        manager_employee_id="MISSING_MANAGER",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    relationships = graph.relationships("EMP001")

    assert len(relationships) == 1
    assert relationships[0].relationship == "BELONGS_TO"
    assert relationships[0].target_id == "ORG001"


def test_organization_graph_snapshot():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    graph = OrganizationGraph(
        organizations=[organization],
    )

    snapshot = graph.snapshot()

    assert "nodes" in snapshot
    assert "edges" in snapshot
    assert snapshot["nodes"] == [
        {
            "node_id": "ORG001",
            "node_type": "organization",
            "name": "Test Company",
        }
    ]
    assert snapshot["edges"] == []
