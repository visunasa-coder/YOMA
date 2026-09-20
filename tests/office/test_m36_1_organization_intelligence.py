import pytest

from yoma.office.intelligence.organization_intelligence import (
    OrganizationIntelligenceResult,
    OrganizationIntelligenceRuntime,
    OrganizationMember,
)


def make_members():
    return (
        OrganizationMember(
            member_id="m1",
            organization_id="org-1",
            department="Engineering",
            team="Platform",
            location="Chennai",
        ),
        OrganizationMember(
            member_id="m2",
            organization_id="org-1",
            department="Engineering",
            team="Platform",
            location="Chennai",
            manager_id="m1",
        ),
        OrganizationMember(
            member_id="m3",
            organization_id="org-1",
            department="Sales",
            team="Enterprise",
            location="Coimbatore",
            manager_id="m1",
        ),
        OrganizationMember(
            member_id="m4",
            organization_id="org-1",
            department="Sales",
            team="SMB",
            location="Chennai",
        ),
    )


def test_builds_organization_snapshot():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert isinstance(result, OrganizationIntelligenceResult)
    assert result.organization_id == "org-1"
    assert result.total_members == 4


def test_discovers_departments_deterministically():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.departments == ("Engineering", "Sales")


def test_discovers_teams_deterministically():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.teams == ("Enterprise", "Platform", "SMB")


def test_discovers_locations_deterministically():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.locations == ("Chennai", "Coimbatore")


def test_counts_members_by_department():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.members_by_department == {
        "Engineering": 2,
        "Sales": 2,
    }


def test_counts_members_by_team():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.members_by_team == {
        "Enterprise": 1,
        "Platform": 2,
        "SMB": 1,
    }


def test_counts_members_by_location():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.members_by_location == {
        "Chennai": 3,
        "Coimbatore": 1,
    }


def test_builds_reporting_relationships():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.managers == ("m1",)
    assert result.reporting_relationships == {
        "m1": ("m2", "m3"),
    }


def test_empty_organization_is_supported():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        [],
    )

    assert result.total_members == 0
    assert result.departments == ()
    assert result.teams == ()
    assert result.locations == ()
    assert result.managers == ()
    assert result.reporting_relationships == {}


def test_rejects_members_from_another_organization():
    members = list(make_members())
    members.append(
        OrganizationMember(
            member_id="m5",
            organization_id="org-2",
        )
    )

    with pytest.raises(ValueError, match="requested organization"):
        OrganizationIntelligenceRuntime().analyze(
            "org-1",
            members,
        )


def test_rejects_invalid_member_type():
    with pytest.raises(TypeError, match="OrganizationMember"):
        OrganizationIntelligenceRuntime().analyze(
            "org-1",
            [object()],
        )


def test_read_only_and_non_executable():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.read_only is True
    assert result.executable is False


def test_metadata_declares_m36_1():
    result = OrganizationIntelligenceRuntime().analyze(
        "org-1",
        make_members(),
    )

    assert result.metadata["source"] == "M36.1"
    assert result.metadata["organization_intelligence"] is True
    assert result.metadata["analytics_only"] is True
    assert result.metadata["read_only"] is True
    assert result.metadata["executable"] is False
