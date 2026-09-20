import pytest

from yoma.office.intelligence.organization_intelligence import OrganizationMember
from yoma.office.intelligence.organization_workload_risk import (
    OrganizationalWorkloadRiskResult,
    OrganizationalWorkloadRiskRuntime,
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


def test_calculates_average_workload():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [member("u1"), member("u2"), member("u3")],
        {
            "u1": 2,
            "u2": 4,
            "u3": 6,
        },
        organization_id="org-1",
    )

    assert result.average_workload == 4.0
    assert result.total_workload == 12.0


def test_classifies_high_risk():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [member("u1"), member("u2"), member("u3")],
        {
            "u1": 1,
            "u2": 1,
            "u3": 8,
        },
        organization_id="org-1",
        high_risk_ratio=2.0,
        medium_risk_ratio=1.5,
    )

    signal = next(
        item for item in result.signals
        if item.entity_id == "u3"
    )

    assert signal.risk_level == "high"
    assert "workload_significantly_above_average" in signal.reasons


def test_classifies_medium_risk():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [member("u1"), member("u2"), member("u3")],
        {
            "u1": 2,
            "u2": 2,
            "u3": 5,
        },
        organization_id="org-1",
        high_risk_ratio=3.0,
        medium_risk_ratio=1.5,
    )

    signal = next(
        item for item in result.signals
        if item.entity_id == "u3"
    )

    assert signal.risk_level == "medium"
    assert "workload_above_average" in signal.reasons


def test_classifies_low_risk():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [member("u1"), member("u2")],
        {
            "u1": 4,
            "u2": 4,
        },
        organization_id="org-1",
    )

    assert all(
        signal.risk_level == "low"
        for signal in result.signals
    )


def test_counts_risk_levels():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [
            member("u1"),
            member("u2"),
            member("u3"),
            member("u4"),
        ],
        {
            "u1": 0,
            "u2": 0,
            "u3": 6,
            "u4": 8,
        },
        organization_id="org-1",
        high_risk_ratio=2.0,
        medium_risk_ratio=1.5,
    )

    assert result.high_risk_count == 1
    assert result.medium_risk_count == 1
    assert result.low_risk_count == 2


def test_calculates_risk_rate():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [
            member("u1"),
            member("u2"),
            member("u3"),
            member("u4"),
        ],
        {
            "u1": 0,
            "u2": 0,
            "u3": 6,
            "u4": 8,
        },
        organization_id="org-1",
        high_risk_ratio=2.0,
        medium_risk_ratio=1.5,
    )

    assert result.risk_rate == 0.5


def test_detects_manager_workload_concentration():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [
            member("manager"),
            member("u1", "manager"),
            member("u2", "manager"),
        ],
        {
            "manager": 10,
            "u1": 1,
            "u2": 1,
        },
        organization_id="org-1",
    )

    manager_signal = next(
        item for item in result.signals
        if item.entity_id == "manager"
    )

    employee_signal = next(
        item for item in result.signals
        if item.entity_id == "u1"
    )

    assert manager_signal.risk_level == "high"
    assert employee_signal.risk_level == "low"


def test_zero_average_workload_is_safe():
    result = OrganizationalWorkloadRiskRuntime().analyze(
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

    assert result.average_workload == 0.0
    assert result.risk_rate == 0.0
    assert all(
        signal.risk_level == "low"
        for signal in result.signals
    )


def test_missing_workload_defaults_to_zero():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [
            member("u1"),
            member("u2"),
        ],
        {"u1": 5},
        organization_id="org-1",
    )

    assert len(result.signals) == 2
    assert next(
        signal.workload
        for signal in result.signals
        if signal.entity_id == "u2"
    ) == 0.0


def test_rejects_unknown_member():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRiskRuntime().analyze(
            [member("u1")],
            {"unknown": 5},
            organization_id="org-1",
        )


def test_rejects_negative_workload():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRiskRuntime().analyze(
            [member("u1")],
            {"u1": -1},
            organization_id="org-1",
        )


def test_rejects_invalid_ratios():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRiskRuntime().analyze(
            [member("u1")],
            {"u1": 1},
            organization_id="org-1",
            high_risk_ratio=0,
        )

    with pytest.raises(ValueError):
        OrganizationalWorkloadRiskRuntime().analyze(
            [member("u1")],
            {"u1": 1},
            organization_id="org-1",
            high_risk_ratio=1.0,
            medium_risk_ratio=2.0,
        )


def test_rejects_duplicate_members():
    with pytest.raises(ValueError):
        OrganizationalWorkloadRiskRuntime().analyze(
            [
                member("u1"),
                member("u1"),
            ],
            {"u1": 1},
            organization_id="org-1",
        )


def test_is_read_only_and_non_executable():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [member("u1")],
        {"u1": 1},
        organization_id="org-1",
    )

    assert isinstance(result, OrganizationalWorkloadRiskResult)
    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.5"
    assert result.metadata["analytics_only"] is True


def test_signal_order_is_deterministic():
    runtime = OrganizationalWorkloadRiskRuntime()

    first = runtime.analyze(
        [
            member("b"),
            member("a"),
            member("c"),
        ],
        {
            "a": 1,
            "b": 6,
            "c": 3,
        },
        organization_id="org-1",
    )

    second = runtime.analyze(
        [
            member("c"),
            member("b"),
            member("a"),
        ],
        {
            "c": 3,
            "a": 1,
            "b": 6,
        },
        organization_id="org-1",
    )

    assert first == second


def test_empty_organization_is_supported():
    result = OrganizationalWorkloadRiskRuntime().analyze(
        [],
        {},
        organization_id="org-1",
    )

    assert result.total_members == 0
    assert result.total_workload == 0.0
    assert result.average_workload == 0.0
    assert result.signals == ()
    assert result.risk_rate == 0.0
