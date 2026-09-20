from datetime import datetime

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.workforce_organization import (
    WorkforceOrganizationContextResolver,
)
from yoma.office.models.attendance import AttendanceEvent
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)
from yoma.office.services.workforce import WorkforceService


def make_graph():
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


def make_events():
    return [
        AttendanceEvent(
            employee_id="EMP-001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 0),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP-001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 20, 0),
            source="biometric",
        ),
    ]


def test_workforce_analysis_can_be_combined_with_organization_context():
    graph = make_graph()
    resolver = WorkforceOrganizationContextResolver(graph)
    service = WorkforceService()

    result = service.analyze_employee(
        "EMP-001",
        make_events(),
        deadline_pressure=0.9,
        meeting_load=0.8,
        consecutive_work_days=7,
    )

    context = resolver.resolve(result["employee_id"])

    assert result["employee_id"] == context.employee_id
    assert context.team.node_id == "TEAM-001"
    assert context.department.node_id == "DEP-001"
    assert context.location.node_id == "LOC-001"
    assert context.organization.node_id == "ORG-001"


def test_workforce_analysis_remains_independent_of_graph():
    service = WorkforceService()

    result = service.analyze_employee(
        "EMP-001",
        make_events(),
        deadline_pressure=0.5,
        meeting_load=0.5,
        consecutive_work_days=3,
    )

    assert result["employee_id"] == "EMP-001"
    assert "sessions" in result
    assert "workload_score" in result
    assert "recommendations" in result
    assert "organization_context" not in result
