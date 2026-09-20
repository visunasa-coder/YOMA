import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_workload import (
    OrganizationalWorkloadRuntime,
    WorkloadDistribution,
)


def member(
    member_id: str,
    *,
    manager_id: str = "",
    department: str = "",
    team: str = "",
):
    return OrganizationMember(
        member_id=member_id,
        organization_id="org-1",
        department=department,
        team=team,
        location="Chennai",
        manager_id=manager_id,
        metadata={},
    )


def test_calculates_member_workload():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
        ],
        {
            "u1": 4,
            "u2": 6,
        },
        organization_id="org-1",
    )

    assert result.workload_by_member == {
        "u1": 4.0,
        "u2": 6.0,
    }


def test_missing_workload_observation_defaults_to_zero():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
        ],
        {"u1": 5},
        organization_id="org-1",
    )

    assert result.workload_by_member == {
        "u1": 5.0,
        "u2": 0.0,
    }


def test_calculates_average_minimum_and_maximum():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
            member("u3"),
        ],
        {
            "u1": 2,
            "u2": 4,
            "u3": 6,
        },
        organization_id="org-1",
    )

    assert result.average_member_workload == 4.0
    assert result.minimum_member_workload == 2.0
    assert result.maximum_member_workload == 6.0


def test_aggregates_by_department():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1", department="Engineering"),
            member("u2", department="Engineering"),
            member("u3", department="Sales"),
        ],
        {
            "u1": 2,
            "u2": 3,
            "u3": 7,
        },
        organization_id="org-1",
    )

    assert result.workload_by_department == {
        "Engineering": 5.0,
        "Sales": 7.0,
    }


def test_aggregates_by_team():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1", team="Platform"),
            member("u2", team="Platform"),
            member("u3", team="Growth"),
        ],
        {
            "u1": 2,
            "u2": 3,
            "u3": 7,
        },
        organization_id="org-1",
    )

    assert result.workload_by_team == {
        "Growth": 7.0,
        "Platform": 5.0,
    }


def test_aggregates_by_manager():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("manager"),
            member("u1", manager_id="manager"),
            member("u2", manager_id="manager"),
        ],
        {
            "manager": 1,
            "u1": 4,
            "u2": 5,
        },
        organization_id="org-1",
    )

    assert result.workload_by_manager == {
        "manager": 9.0,
    }


def test_detects_overloaded_members():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
            member("u3"),
        ],
        {
            "u1": 3,
            "u2": 5,
            "u3": 8,
        },
        organization_id="org-1",
        workload_threshold=5,
    )

    assert result.overloaded_members == ("u2", "u3")


def test_threshold_is_inclusive():
    result = OrganizationalWorkloadRuntime().analyze(
        [member("u1")],
        {"u1": 5},
        organization_id="org-1",
        workload_threshold=5,
    )

    assert result.overloaded_members == ("u1",)


def test_calculates_workload_concentration():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
            member("u3"),
        ],
        {
            "u1": 2,
            "u2": 3,
            "u3": 5,
        },
        organization_id="org-1",
    )

    assert result.workload_concentration_rate == 0.5


def test_zero_total_workload_has_zero_concentration():
    result = OrganizationalWorkloadRuntime().analyze(
        [
            member("u1"),
            member("u2"),
        ],
        {
            "u1": 0,
            "u2": 0,
        },
        organization_id="org-1",
    )

    assert result.workload_concentration_rate == 0.0


def test_rejects_unknown_member_workload():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRuntime().analyze(
            [member("u1")],
            {"unknown": 5},
            organization_id="org-1",
        )


def test_rejects_negative_workload():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRuntime().analyze(
            [member("u1")],
            {"u1": -1},
            organization_id="org-1",
        )


def test_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRuntime().analyze(
            [member("u1")],
            {"u1": 1},
            organization_id="org-1",
            workload_threshold=-1,
        )


def test_is_read_only_and_non_executable():
    result = OrganizationalWorkloadRuntime().analyze(
        [member("u1")],
        {"u1": 1},
        organization_id="org-1",
    )

    assert isinstance(result, WorkloadDistribution)
    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.4"
    assert result.metadata["analytics_only"] is True


def test_results_are_deterministic():
    runtime = OrganizationalWorkloadRuntime()

    first = runtime.analyze(
        [
            member("b", department="Sales"),
            member("a", department="Engineering"),
        ],
        {
            "b": 4,
            "a": 2,
        },
        organization_id="org-1",
    )

    second = runtime.analyze(
        [
            member("a", department="Engineering"),
            member("b", department="Sales"),
        ],
        {
            "a": 2,
            "b": 4,
        },
        organization_id="org-1",
    )

    assert first == second


def test_empty_members_are_supported():
    result = OrganizationalWorkloadRuntime().analyze(
        [],
        {},
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.average_member_workload == 0.0
    assert result.maximum_member_workload == 0.0
    assert result.minimum_member_workload == 0.0
    assert result.overloaded_members == ()
