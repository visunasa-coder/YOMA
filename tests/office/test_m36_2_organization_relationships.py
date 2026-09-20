from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_relationships import (
    WorkforceStructureResult,
    WorkforceStructureRuntime,
)


def member(
    member_id: str,
    *,
    manager_id: str = "",
    department: str = "",
    team: str = "",
    location: str = "",
):
    return OrganizationMember(
        member_id=member_id,
        organization_id="org-1",
        department=department,
        team=team,
        location=location,
        manager_id=manager_id,
        metadata={},
    )


def test_derives_direct_reports():
    result = WorkforceStructureRuntime().analyze(
        [
            member("u1"),
            member("u2", manager_id="u1"),
            member("u3", manager_id="u1"),
            member("u4", manager_id="u2"),
        ],
        organization_id="org-1",
    )

    assert result.direct_reports == {
        "u1": ("u2", "u3"),
        "u2": ("u4",),
    }


def test_derives_manager_mapping():
    result = WorkforceStructureRuntime().analyze(
        [
            member("u1"),
            member("u2", manager_id="u1"),
        ],
        organization_id="org-1",
    )

    assert result.managers_by_member == {"u2": "u1"}


def test_counts_relationships_and_managers():
    result = WorkforceStructureRuntime().analyze(
        [
            member("u1"),
            member("u2", manager_id="u1"),
            member("u3", manager_id="u1"),
            member("u4", manager_id="u2"),
        ],
        organization_id="org-1",
    )

    assert result.manager_count == 2
    assert result.relationship_count == 3


def test_derives_member_attributes():
    result = WorkforceStructureRuntime().analyze(
        [
            member(
                "u1",
                department="Engineering",
                team="Platform",
                location="Chennai",
            )
        ],
        organization_id="org-1",
    )

    assert result.departments_by_member == {"u1": "Engineering"}
    assert result.teams_by_member == {"u1": "Platform"}
    assert result.locations_by_member == {"u1": "Chennai"}


def test_empty_members_are_supported():
    result = WorkforceStructureRuntime().analyze(
        [],
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.direct_reports == {}
    assert result.managers_by_member == {}
    assert result.relationship_count == 0


def test_rejects_empty_organization():
    with pytest.raises(ValueError):
        WorkforceStructureRuntime().analyze(
            [],
            organization_id="",
        )


def test_rejects_wrong_organization():
    with pytest.raises(ValueError):
        WorkforceStructureRuntime().analyze(
            [
                member("u1"),
            ],
            organization_id="org-2",
        )


def test_rejects_duplicate_member_ids():
    with pytest.raises(ValueError):
        WorkforceStructureRuntime().analyze(
            [
                member("u1"),
                member("u1"),
            ],
            organization_id="org-1",
        )


def test_rejects_invalid_member_object():
    with pytest.raises(TypeError):
        WorkforceStructureRuntime().analyze(
            [object()],
            organization_id="org-1",
        )


def test_output_is_deterministic():
    runtime = WorkforceStructureRuntime()

    result_a = runtime.analyze(
        [
            member("u3", manager_id="u1"),
            member("u2", manager_id="u1"),
            member("u1"),
        ],
        organization_id="org-1",
    )

    result_b = runtime.analyze(
        [
            member("u1"),
            member("u2", manager_id="u1"),
            member("u3", manager_id="u1"),
        ],
        organization_id="org-1",
    )

    assert result_a == result_b


def test_is_read_only_and_non_executable():
    result = WorkforceStructureRuntime().analyze(
        [member("u1")],
        organization_id="org-1",
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.2"
    assert result.metadata["analytics_only"] is True


def test_result_type_is_correct():
    result = WorkforceStructureRuntime().analyze(
        [member("u1")],
        organization_id="org-1",
    )

    assert isinstance(result, WorkforceStructureResult)


def test_supports_multi_level_reporting():
    result = WorkforceStructureRuntime().analyze(
        [
            member("ceo"),
            member("manager", manager_id="ceo"),
            member("lead", manager_id="manager"),
            member("employee", manager_id="lead"),
        ],
        organization_id="org-1",
    )

    assert result.direct_reports == {
        "ceo": ("manager",),
        "lead": ("employee",),
        "manager": ("lead",),
    }
    assert result.relationship_count == 3
