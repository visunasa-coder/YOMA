import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_coverage import (
    OrganizationalCoverageResult,
    OrganizationalCoverageRuntime,
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


def test_identifies_managers():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("u2", "manager"),
        ],
        organization_id="org-1",
    )

    assert result.managers == ("manager",)


def test_identifies_uncovered_members():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("independent"),
        ],
        organization_id="org-1",
    )

    assert result.uncovered_members == (
        "independent",
        "manager",
    )


def test_identifies_single_point_manager():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
        ],
        organization_id="org-1",
    )

    assert result.single_point_managers == ("manager",)


def test_manager_with_multiple_reports_has_structural_coverage():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("u2", "manager"),
        ],
        organization_id="org-1",
    )

    signal = next(
        item for item in result.signals
        if item.member_id == "manager"
    )

    assert signal.is_manager is True
    assert signal.dependent_member_count == 2
    assert signal.manager_has_backup is True
    assert signal.coverage_level == "covered"


def test_single_report_manager_is_single_point():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
        ],
        organization_id="org-1",
    )

    signal = next(
        item for item in result.signals
        if item.member_id == "manager"
    )

    assert signal.coverage_level == "single_point"
    assert "single_reporting_dependency" in signal.reasons


def test_uncovered_standalone_member():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("u1"),
        ],
        organization_id="org-1",
    )

    signal = result.signals[0]

    assert signal.has_manager is False
    assert signal.is_manager is False
    assert signal.coverage_level == "uncovered"
    assert "no_manager" in signal.reasons


def test_calculates_covered_members():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("ceo"),
            member("manager", "ceo"),
            member("u1", "manager"),
        ],
        organization_id="org-1",
    )

    assert result.covered_members == 1


def test_calculates_coverage_rate():
    result = OrganizationalCoverageRuntime().analyze(
        [
            member("ceo"),
            member("manager", "ceo"),
            member("u1", "manager"),
        ],
        organization_id="org-1",
    )

    assert result.coverage_rate == 1 / 3


def test_rejects_unknown_manager():
    with pytest.raises(ValueError):
        OrganizationalCoverageRuntime().analyze(
            [
                member("u1", "unknown"),
            ],
            organization_id="org-1",
        )


def test_rejects_duplicate_members():
    with pytest.raises(ValueError):
        OrganizationalCoverageRuntime().analyze(
            [
                member("u1"),
                member("u1"),
            ],
            organization_id="org-1",
        )


def test_rejects_empty_organization():
    with pytest.raises(ValueError):
        OrganizationalCoverageRuntime().analyze(
            [],
            organization_id="",
        )


def test_rejects_invalid_member():
    with pytest.raises(TypeError):
        OrganizationalCoverageRuntime().analyze(
            [object()],
            organization_id="org-1",
        )


def test_empty_organization_is_supported():
    result = OrganizationalCoverageRuntime().analyze(
        [],
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.managers == ()
    assert result.uncovered_members == ()
    assert result.single_point_managers == ()
    assert result.covered_members == 0
    assert result.coverage_rate == 0.0
    assert result.signals == ()


def test_signal_order_is_deterministic():
    runtime = OrganizationalCoverageRuntime()

    first = runtime.analyze(
        [
            member("u2"),
            member("manager"),
            member("u1", "manager"),
        ],
        organization_id="org-1",
    )

    second = runtime.analyze(
        [
            member("u1", "manager"),
            member("u2"),
            member("manager"),
        ],
        organization_id="org-1",
    )

    assert first == second


def test_result_is_read_only_and_non_executable():
    result = OrganizationalCoverageRuntime().analyze(
        [member("u1")],
        organization_id="org-1",
    )

    assert isinstance(result, OrganizationalCoverageResult)
    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.7"
    assert result.metadata["analytics_only"] is True
    assert result.metadata["automatic_reassignment"] is False
