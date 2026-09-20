import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_capacity import (
    OrganizationalCapacityResult,
    OrganizationalCapacityRuntime,
)


def member(member_id: str, manager_id: str = ""):
    return OrganizationMember(
        member_id=member_id,
        organization_id="org-1",
        department="Engineering",
        team="Platform",
        location="Chennai",
        manager_id=manager_id,
        metadata={},
    )


def test_calculates_span_of_control():
    result = OrganizationalCapacityRuntime().analyze(
        [
            member("ceo"),
            member("u1", "ceo"),
            member("u2", "ceo"),
            member("u3", "ceo"),
            member("manager", "ceo"),
            member("u4", "manager"),
        ],
        organization_id="org-1",
    )

    assert result.spans_by_manager == {
        "ceo": 4,
        "manager": 1,
    }


def test_calculates_average_span():
    result = OrganizationalCapacityRuntime().analyze(
        [
            member("manager1"),
            member("manager2"),
            member("u1", "manager1"),
            member("u2", "manager1"),
            member("u3", "manager2"),
        ],
        organization_id="org-1",
    )

    assert result.average_span_of_control == 1.5


def test_calculates_minimum_and_maximum_span():
    result = OrganizationalCapacityRuntime().analyze(
        [
            member("m1"),
            member("m2"),
            member("a", "m1"),
            member("b", "m1"),
            member("c", "m1"),
            member("d", "m2"),
        ],
        organization_id="org-1",
    )

    assert result.minimum_span_of_control == 1
    assert result.maximum_span_of_control == 3


def test_counts_managed_and_unmanaged_members():
    result = OrganizationalCapacityRuntime().analyze(
        [
            member("ceo"),
            member("manager", "ceo"),
            member("employee", "manager"),
            member("independent"),
        ],
        organization_id="org-1",
    )

    assert result.managed_member_count == 2
    assert result.unmanaged_member_count == 2
    assert result.unmanaged_members == ("ceo", "independent")


def test_detects_overloaded_managers():
    members = [member("manager")]
    members.extend(
        member(f"u{i}", "manager")
        for i in range(1, 6)
    )

    result = OrganizationalCapacityRuntime().analyze(
        members,
        organization_id="org-1",
        capacity_threshold=5,
    )

    assert result.overloaded_managers == ("manager",)


def test_threshold_is_inclusive():
    members = [member("manager")]
    members.extend(
        member(f"u{i}", "manager")
        for i in range(1, 4)
    )

    result = OrganizationalCapacityRuntime().analyze(
        members,
        organization_id="org-1",
        capacity_threshold=3,
    )

    assert result.overloaded_managers == ("manager",)


def test_calculates_hierarchy_depth():
    result = OrganizationalCapacityRuntime().analyze(
        [
            member("ceo"),
            member("director", "ceo"),
            member("manager", "director"),
            member("lead", "manager"),
            member("employee", "lead"),
        ],
        organization_id="org-1",
    )

    assert result.hierarchy_depth == 4


def test_detects_reporting_cycle():
    with pytest.raises(ValueError, match="cyclic"):
        OrganizationalCapacityRuntime().analyze(
            [
                member("a", "b"),
                member("b", "a"),
            ],
            organization_id="org-1",
        )


def test_empty_organization_has_zero_capacity_metrics():
    result = OrganizationalCapacityRuntime().analyze(
        [],
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.manager_count == 0
    assert result.managed_member_count == 0
    assert result.unmanaged_member_count == 0
    assert result.average_span_of_control == 0.0
    assert result.minimum_span_of_control == 0
    assert result.maximum_span_of_control == 0
    assert result.hierarchy_depth == 0


def test_rejects_invalid_capacity_threshold():
    with pytest.raises(ValueError):
        OrganizationalCapacityRuntime().analyze(
            [],
            organization_id="org-1",
            capacity_threshold=0,
        )


def test_rejects_wrong_organization():
    with pytest.raises(ValueError):
        OrganizationalCapacityRuntime().analyze(
            [member("u1")],
            organization_id="org-2",
        )


def test_rejects_duplicate_members():
    with pytest.raises(ValueError):
        OrganizationalCapacityRuntime().analyze(
            [
                member("u1"),
                member("u1"),
            ],
            organization_id="org-1",
        )


def test_result_is_read_only_and_non_executable():
    result = OrganizationalCapacityRuntime().analyze(
        [member("u1")],
        organization_id="org-1",
    )

    assert isinstance(result, OrganizationalCapacityResult)
    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.3"
    assert result.metadata["analytics_only"] is True


def test_results_are_deterministic():
    runtime = OrganizationalCapacityRuntime()

    first = runtime.analyze(
        [
            member("z"),
            member("b", "z"),
            member("a", "z"),
        ],
        organization_id="org-1",
    )

    second = runtime.analyze(
        [
            member("a", "z"),
            member("z"),
            member("b", "z"),
        ],
        organization_id="org-1",
    )

    assert first == second
