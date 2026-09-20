from yoma.office.models.organization import (
    Organization,
    Location,
    Department,
    Team,
    Employee,
)


def test_organization_model():
    org = Organization(
        organization_id="ORG001",
        name="Test Company",
    )

    assert org.organization_id == "ORG001"
    assert org.name == "Test Company"
    assert org.active is True


def test_organization_hierarchy():
    org = Organization("ORG001", "Test Company")
    location = Location("LOC001", org.organization_id, "Head Office")
    department = Department(
        "DEP001",
        org.organization_id,
        "Engineering",
        location_id=location.location_id,
    )
    team = Team(
        "TEAM001",
        org.organization_id,
        "AI Team",
        department_id=department.department_id,
    )
    employee = Employee(
        employee_id="EMP001",
        name="Test Employee",
        organization_id=org.organization_id,
        department_id=department.department_id,
        team_id=team.team_id,
        location_id=location.location_id,
        role="Engineer",
    )

    assert employee.organization_id == "ORG001"
    assert employee.department_id == "DEP001"
    assert employee.team_id == "TEAM001"
    assert employee.location_id == "LOC001"


def test_employee_external_identity():
    employee = Employee(
        employee_id="EMP001",
        name="External Employee",
        organization_id="ORG001",
        external_id="google-123",
        external_provider="google_workspace",
    )

    assert employee.external_id == "google-123"
    assert employee.external_provider == "google_workspace"
