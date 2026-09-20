from yoma.office.it.it_organization import (
    ITMember,
    ITOrganization,
    ITOrganizationIntelligence,
    ITService,
    ITTeam,
)


def test_member_requires_identity():
    try:
        ITMember("", "org-1", "Alice", "developer")
        assert False
    except ValueError:
        assert True


def test_supported_it_role():
    member = ITMember("m1", "org-1", "Alice", "developer")
    assert member.role == "developer"


def test_unsupported_role_rejected():
    try:
        ITMember("m1", "org-1", "Alice", "astronaut")
        assert False
    except ValueError:
        assert True


def test_team_creation():
    team = ITTeam("t1", "org-1", "Platform", "engineering")
    assert team.name == "Platform"


def test_service_creation():
    service = ITService(
        "svc-1",
        "org-1",
        "Production API",
        criticality="critical",
    )
    assert service.criticality == "critical"


def test_organization_accepts_matching_entities():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(ITMember("m1", "org-1", "Alice", "developer"),),
        teams=(ITTeam("t1", "org-1", "Engineering", "engineering"),),
    )
    assert organization.organization_id == "org-1"


def test_mismatched_member_rejected():
    try:
        ITOrganization(
            "org-1",
            "Example IT",
            members=(ITMember("m1", "org-2", "Alice", "developer"),),
        )
        assert False
    except ValueError:
        assert True


def test_active_collections():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember("m1", "org-1", "Alice", "developer"),
            ITMember("m2", "org-1", "Bob", "developer", active=False),
        ),
        teams=(
            ITTeam("t1", "org-1", "Engineering", "engineering"),
        ),
        services=(
            ITService("s1", "org-1", "API"),
        ),
    )

    assert len(organization.active_members) == 1
    assert len(organization.active_teams) == 1
    assert len(organization.active_services) == 1


def test_team_members():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember("m1", "org-1", "Alice", "developer", team_id="t1"),
            ITMember("m2", "org-1", "Bob", "qa", team_id="t2"),
        ),
    )

    assert [m.member_id for m in organization.team_members("t1")] == ["m1"]


def test_analysis_counts_members_and_teams():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember("m1", "org-1", "Alice", "developer", team_id="t1"),
            ITMember("m2", "org-1", "Bob", "qa", team_id="t1"),
        ),
        teams=(
            ITTeam("t1", "org-1", "Engineering", "engineering"),
        ),
    )

    result = ITOrganizationIntelligence().analyze(organization)

    assert result.member_count == 2
    assert result.active_member_count == 2
    assert result.team_count == 1
    assert result.active_team_count == 1


def test_analysis_detects_unassigned_members():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember("m1", "org-1", "Alice", "developer"),
        ),
    )

    result = ITOrganizationIntelligence().analyze(organization)

    assert result.unassigned_members == 1
    assert "active members without team assignment" in result.issues


def test_analysis_detects_unmanaged_members():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember(
                "m1",
                "org-1",
                "Alice",
                "developer",
                team_id="t1",
            ),
        ),
    )

    result = ITOrganizationIntelligence().analyze(organization)

    assert result.unmanaged_members == 1


def test_critical_services_are_detected():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        services=(
            ITService(
                "svc-1",
                "org-1",
                "Production API",
                criticality="critical",
            ),
        ),
    )

    result = ITOrganizationIntelligence().analyze(organization)

    assert result.critical_service_count == 1
    assert result.requires_human_approval is True
    assert result.executable is False


def test_analysis_is_deterministic():
    organization = ITOrganization(
        "org-1",
        "Example IT",
        members=(
            ITMember("m1", "org-1", "Alice", "developer"),
        ),
    )

    intelligence = ITOrganizationIntelligence()

    assert intelligence.analyze(organization) == intelligence.analyze(organization)


def test_invalid_input_type_rejected():
    try:
        ITOrganizationIntelligence().analyze("not-an-organization")
        assert False
    except TypeError:
        assert True


def test_helper_function_matches_runtime():
    organization = ITOrganization("org-1", "Example IT")

    result = ITOrganizationIntelligence().analyze(organization)

    assert result.organization_id == "org-1"
    assert result.member_count == 0
    assert result.team_count == 0
