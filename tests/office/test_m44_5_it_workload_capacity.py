from yoma.office.it.it_workload_capacity import (
    ITCapacity,
    ITWorkload,
    ITWorkloadCapacityAnalysis,
    ITWorkloadCapacityIntelligence,
    ITWorkloadCapacityPortfolio,
    analyze_it_workload_capacity,
)


def test_workload_creation():
    item = ITWorkload(
        "w1",
        "org-1",
        member_id="u1",
        team_id="team-1",
        title="Build API",
        estimated_hours=10,
    )

    assert item.workload_id == "w1"
    assert item.member_id == "u1"
    assert item.estimated_hours == 10


def test_capacity_creation():
    capacity = ITCapacity(
        "u1",
        "org-1",
        team_id="team-1",
        available_hours=40,
    )

    assert capacity.member_id == "u1"
    assert capacity.available_hours == 40


def test_invalid_workload_hours():
    try:
        ITWorkload("w1", "org-1", estimated_hours=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative workload hours must fail")


def test_invalid_capacity_hours():
    try:
        ITCapacity("u1", "org-1", available_hours=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative capacity must fail")


def test_invalid_priority():
    try:
        ITWorkload(
            "w1",
            "org-1",
            priority="urgent",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid priority must fail")


def test_invalid_status():
    try:
        ITWorkload(
            "w1",
            "org-1",
            status="unknown",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid status must fail")


def test_portfolio_organization_consistency():
    try:
        ITWorkloadCapacityPortfolio(
            "org-1",
            workloads=(
                ITWorkload("w1", "org-2"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("organization mismatch must fail")


def test_capacity_organization_consistency():
    try:
        ITWorkloadCapacityPortfolio(
            "org-1",
            capacities=(
                ITCapacity("u1", "org-2"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("capacity organization mismatch must fail")


def test_workload_counts():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=8,
                status="in_progress",
            ),
            ITWorkload(
                "w2",
                "org-1",
                member_id="u1",
                estimated_hours=4,
                status="completed",
            ),
            ITWorkload(
                "w3",
                "org-1",
                status="backlog",
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.workload_count == 3
    assert result.active_workload_count == 2
    assert result.completed_workload_count == 1
    assert result.unassigned_workload_count == 1


def test_blocked_workload_count():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                status="blocked",
            ),
            ITWorkload(
                "w2",
                "org-1",
                member_id="u2",
                status="in_progress",
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.blocked_workload_count == 1


def test_high_priority_count():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                priority="high",
            ),
            ITWorkload(
                "w2",
                "org-1",
                member_id="u2",
                priority="critical",
            ),
            ITWorkload(
                "w3",
                "org-1",
                member_id="u3",
                priority="normal",
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.high_priority_workload_count == 2


def test_capacity_shortfall():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=30,
            ),
            ITWorkload(
                "w2",
                "org-1",
                member_id="u1",
                estimated_hours=25,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=40,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.total_available_hours == 40
    assert result.total_assigned_hours == 55
    assert result.capacity_shortfall_hours == 15


def test_overloaded_member():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=50,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=40,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.overloaded_member_count == 1


def test_underutilized_member():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=10,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=40,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.underutilized_member_count == 1


def test_unassigned_workload():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                estimated_hours=8,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.unassigned_workload_count == 1
    assert any("no assigned owner" in issue for issue in result.issues)


def test_workload_concentration():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=60,
            ),
            ITWorkload(
                "w2",
                "org-1",
                member_id="u2",
                estimated_hours=20,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.workload_concentration_member_id == "u1"
    assert result.workload_concentration_hours == 60
    assert any("concentrated" in issue for issue in result.issues)


def test_zero_capacity_with_workload_is_overloaded():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=4,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=0,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.overloaded_member_count == 1


def test_deterministic_analysis():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w2",
                "org-1",
                member_id="u2",
                estimated_hours=10,
            ),
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=30,
            ),
        ),
        capacities=(
            ITCapacity("u2", "org-1", available_hours=20),
            ITCapacity("u1", "org-1", available_hours=40),
        ),
    )

    intelligence = ITWorkloadCapacityIntelligence()

    first = intelligence.analyze(portfolio)
    second = intelligence.analyze(portfolio)

    assert first == second


def test_helper_function():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=5,
            ),
        ),
    )

    result = analyze_it_workload_capacity(portfolio)

    assert isinstance(result, ITWorkloadCapacityAnalysis)
    assert result.workload_count == 1


def test_safety_boundary():
    portfolio = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=50,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=40,
            ),
        ),
    )

    result = ITWorkloadCapacityIntelligence().analyze(portfolio)

    assert result.requires_human_approval is True
    assert result.executable is False


def test_invalid_portfolio_type():
    try:
        ITWorkloadCapacityIntelligence().analyze(None)
    except TypeError:
        pass
    else:
        raise AssertionError("invalid portfolio type must fail")
