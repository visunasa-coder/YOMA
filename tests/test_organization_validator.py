from yoma.office.intelligence.organization_validator import (
    OrganizationGraphValidator,
    OrganizationValidationIssue,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


def test_valid_organization_has_no_issues():
    issues = OrganizationGraphValidator(
        organizations=[Organization("org-1", "Acme")],
        locations=[Location("loc-1", "org-1", "HQ")],
        departments=[
            Department(
                "dept-1",
                "org-1",
                "Engineering",
                location_id="loc-1",
                manager_employee_id="emp-1",
            )
        ],
        teams=[
            Team(
                "team-1",
                "org-1",
                "Platform",
                department_id="dept-1",
                manager_employee_id="emp-1",
            )
        ],
        employees=[
            Employee(
                "emp-1",
                "Alice",
                organization_id="org-1",
                department_id="dept-1",
                team_id="team-1",
                location_id="loc-1",
            )
        ],
    ).validate()

    assert issues == []


def test_missing_references_are_reported():
    issues = OrganizationGraphValidator(
        organizations=[Organization("org-1", "Acme")],
        departments=[
            Department(
                "dept-1",
                "org-1",
                "Engineering",
                location_id="loc-missing",
                manager_employee_id="emp-missing",
            )
        ],
        employees=[
            Employee(
                "emp-1",
                "Alice",
                organization_id="org-1",
                department_id="dept-missing",
                team_id="team-missing",
                location_id="loc-missing",
                manager_employee_id="manager-missing",
            )
        ],
    ).validate()

    assert len(issues) == 6
    assert all(
        isinstance(issue, OrganizationValidationIssue)
        for issue in issues
    )
    assert all(issue.issue_type == "missing_reference" for issue in issues)


def test_cross_organization_relationships_are_reported():
    issues = OrganizationGraphValidator(
        organizations=[
            Organization("org-1", "Acme"),
            Organization("org-2", "Beta"),
        ],
        locations=[
            Location("loc-2", "org-2", "Beta HQ"),
        ],
        departments=[
            Department(
                "dept-1",
                "org-1",
                "Engineering",
                location_id="loc-2",
            )
        ],
        teams=[
            Team(
                "team-1",
                "org-1",
                "Platform",
                department_id="dept-2",
            )
        ],
        employees=[
            Employee(
                "emp-1",
                "Alice",
                organization_id="org-1",
                department_id="dept-2",
                team_id="team-2",
                location_id="loc-2",
            )
        ],
    ).validate()

    mismatch_ids = {
        issue.source_id
        for issue in issues
        if issue.issue_type == "organization_mismatch"
    }

    assert "dept-1" in mismatch_ids
    assert "emp-1" in mismatch_ids


def test_duplicate_ids_are_reported():
    issues = OrganizationGraphValidator(
        organizations=[
            Organization("org-1", "Acme"),
            Organization("org-1", "Acme Duplicate"),
        ],
        employees=[
            Employee("emp-1", "Alice"),
            Employee("emp-1", "Alice Duplicate"),
        ],
    ).validate()

    duplicates = {
        (issue.source_id, issue.issue_type)
        for issue in issues
    }

    assert ("org-1", "duplicate_id") in duplicates
    assert ("emp-1", "duplicate_id") in duplicates


def test_empty_validator_is_safe():
    assert OrganizationGraphValidator().validate() == []


def test_validation_does_not_mutate_inputs():
    organization = Organization("org-1", "Acme")
    employee = Employee(
        "emp-1",
        "Alice",
        organization_id="org-1",
    )

    organizations = [organization]
    employees = [employee]

    OrganizationGraphValidator(
        organizations=organizations,
        employees=employees,
    ).validate()

    assert organizations == [organization]
    assert employees == [employee]
