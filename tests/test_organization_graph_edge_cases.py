from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


def test_duplicate_relationships_are_deduplicated():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee, employee],
    )

    edges = graph.relationships(
        "EMP001",
        "BELONGS_TO",
    )

    assert len(edges) == 1


def test_missing_manager_is_ignored():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG001",
        manager_employee_id="MISSING_MANAGER",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    assert graph.reports_to("EMP001") is None


def test_missing_department_and_team_are_ignored():
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
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    assert graph.department_of("EMP001") is None
    assert graph.team_of("EMP001") is None


def test_inactive_entities_remain_represented():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
        active=False,
    )

    employee = Employee(
        employee_id="EMP001",
        name="Inactive Employee",
        organization_id="ORG001",
        active=False,
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    assert graph.node("ORG001") is not None
    assert graph.node("EMP001") is not None

    assert any(
        edge.source_id == "EMP001"
        and edge.target_id == "ORG001"
        and edge.relationship == "BELONGS_TO"
        for edge in graph.edges()
    )


def test_cross_organization_explicit_reference_is_not_inferred_away():
    org_a = Organization(
        organization_id="ORG_A",
        name="Company A",
    )

    org_b = Organization(
        organization_id="ORG_B",
        name="Company B",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG_A",
        department_id="DEP_B",
    )

    department = Department(
        department_id="DEP_B",
        organization_id="ORG_B",
        name="Department B",
    )

    graph = OrganizationGraph(
        organizations=[org_a, org_b],
        departments=[department],
        employees=[employee],
    )

    assert graph.organization_of("EMP001").node_id == "ORG_A"
    assert graph.department_of("EMP001").node_id == "DEP_B"


def test_self_reporting_relationship_is_preserved_as_explicit_data():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Employee",
        organization_id="ORG001",
        manager_employee_id="EMP001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    manager = graph.reports_to("EMP001")

    assert manager is not None
    assert manager.node_id == "EMP001"


def test_manager_relationship_requires_existing_manager_node():
    organization = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    department = Department(
        department_id="DEP001",
        organization_id="ORG001",
        name="Engineering",
        manager_employee_id="EMP001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        departments=[department],
    )

    assert graph.manager_of("DEP001") is None


def test_empty_graph_is_safe():
    graph = OrganizationGraph()

    assert graph.nodes() == []
    assert graph.edges() == []
    assert graph.snapshot() == {
        "nodes": [],
        "edges": [],
    }
