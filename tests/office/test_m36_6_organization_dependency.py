import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_dependency import (
    OrganizationalDependencyResult,
    OrganizationalDependencyRuntime,
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


def test_counts_direct_dependents():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("u2", "manager"),
            member("u3", "manager"),
        ],
        {
            "manager": 2,
            "u1": 1,
            "u2": 1,
            "u3": 1,
        },
        organization_id="org-1",
    )

    signal = next(
        item for item in result.dependency_signals
        if item.member_id == "manager"
    )

    assert signal.dependent_member_count == 3


def test_classifies_elevated_dependency():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("u2", "manager"),
        ],
        {
            "manager": 2,
            "u1": 1,
            "u2": 1,
        },
        organization_id="org-1",
        elevated_dependents=2,
        critical_dependents=5,
    )

    signal = next(
        item for item in result.dependency_signals
        if item.member_id == "manager"
    )

    assert signal.dependency_level == "elevated"
    assert "reporting_dependency" in signal.reasons


def test_classifies_critical_dependency():
    members = [member("manager")]
    members.extend(
        member(f"u{i}", "manager")
        for i in range(1, 6)
    )

    workload = {"manager": 2}
    workload.update({f"u{i}": 1 for i in range(1, 6)})

    result = OrganizationalDependencyRuntime().analyze(
        members,
        workload,
        organization_id="org-1",
        elevated_dependents=2,
        critical_dependents=5,
    )

    signal = next(
        item for item in result.dependency_signals
        if item.member_id == "manager"
    )

    assert signal.dependency_level == "critical"
    assert "high_reporting_dependency" in signal.reasons


def test_classifies_normal_dependency():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
        ],
        {
            "manager": 1,
            "u1": 1,
        },
        organization_id="org-1",
    )

    signal = next(
        item for item in result.dependency_signals
        if item.member_id == "manager"
    )

    assert signal.dependency_level == "normal"


def test_detects_high_workload_concentration():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
        ],
        {
            "manager": 10,
            "u1": 1,
        },
        organization_id="org-1",
        high_workload_ratio=1.5,
    )

    signal = next(
        item for item in result.dependency_signals
        if item.member_id == "manager"
    )

    assert "high_workload_concentration" in signal.reasons


def test_counts_dependency_levels():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("m1"),
            member("m2"),
            member("m3"),
            member("a1", "m1"),
            member("a2", "m1"),
            member("b1", "m2"),
            member("b2", "m2"),
            member("b3", "m2"),
            member("c1", "m2"),
            member("c2", "m2"),
        ],
        {
            "m1": 1,
            "m2": 1,
            "m3": 1,
            "a1": 1,
            "a2": 1,
            "b1": 1,
            "b2": 1,
            "b3": 1,
            "c1": 1,
            "c2": 1,
        },
        organization_id="org-1",
        elevated_dependents=2,
        critical_dependents=5,
    )

    assert result.critical_dependency_count == 1
    assert result.elevated_dependency_count == 1
    assert result.normal_dependency_count == 8


def test_calculates_dependency_rate():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("m1"),
            member("m2"),
            member("u1", "m1"),
            member("u2", "m1"),
            member("u3", "m2"),
        ],
        {
            "m1": 1,
            "m2": 1,
            "u1": 1,
            "u2": 1,
            "u3": 1,
        },
        organization_id="org-1",
        elevated_dependents=2,
    )

    assert result.dependency_rate == 0.2


def test_calculates_maximum_dependency():
    result = OrganizationalDependencyRuntime().analyze(
        [
            member("m1"),
            member("u1", "m1"),
            member("u2", "m1"),
            member("u3", "m1"),
        ],
        {
            "m1": 1,
            "u1": 1,
            "u2": 1,
            "u3": 1,
        },
        organization_id="org-1",
    )

    assert result.maximum_dependent_member_count == 3


def test_rejects_unknown_manager():
    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [
                member("u1", "unknown"),
            ],
            {"u1": 1},
            organization_id="org-1",
        )


def test_rejects_unknown_workload_member():
    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [member("u1")],
            {"unknown": 1},
            organization_id="org-1",
        )


def test_rejects_negative_workload():
    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [member("u1")],
            {"u1": -1},
            organization_id="org-1",
        )


def test_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [member("u1")],
            {"u1": 1},
            organization_id="org-1",
            critical_dependents=0,
        )

    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [member("u1")],
            {"u1": 1},
            organization_id="org-1",
            elevated_dependents=6,
            critical_dependents=5,
        )


def test_rejects_duplicate_members():
    with pytest.raises(ValueError):
        OrganizationalDependencyRuntime().analyze(
            [
                member("u1"),
                member("u1"),
            ],
            {"u1": 1},
            organization_id="org-1",
        )


def test_is_read_only_and_non_executable():
    result = OrganizationalDependencyRuntime().analyze(
        [member("u1")],
        {"u1": 1},
        organization_id="org-1",
    )

    assert isinstance(result, OrganizationalDependencyResult)
    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.6"
    assert result.metadata["analytics_only"] is True
    assert result.metadata["automatic_reassignment"] is False


def test_results_are_deterministic():
    runtime = OrganizationalDependencyRuntime()

    first = runtime.analyze(
        [
            member("b"),
            member("a"),
            member("u1", "a"),
        ],
        {
            "a": 5,
            "b": 1,
            "u1": 1,
        },
        organization_id="org-1",
    )

    second = runtime.analyze(
        [
            member("u1", "a"),
            member("b"),
            member("a"),
        ],
        {
            "u1": 1,
            "a": 5,
            "b": 1,
        },
        organization_id="org-1",
    )

    assert first == second


def test_empty_organization_is_supported():
    result = OrganizationalDependencyRuntime().analyze(
        [],
        {},
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.dependency_signals == ()
    assert result.dependency_rate == 0.0
    assert result.maximum_dependent_member_count == 0
