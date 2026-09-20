from yoma.office.it.it_dependencies import (
    ITDependency,
    ITDependencyAnalysis,
    ITDependencyIntelligence,
    ITDependencyNode,
    ITDependencyPortfolio,
    analyze_it_dependencies,
)


def node(
    node_id,
    status="open",
    node_type="task",
    owner_id="u1",
):
    return ITDependencyNode(
        node_id,
        "org-1",
        node_type,
        status=status,
        owner_id=owner_id,
    )


def dependency(
    dependency_id,
    source,
    target,
):
    return ITDependency(
        dependency_id,
        "org-1",
        source,
        target,
    )


def test_node_creation():
    item = node("n1")

    assert item.node_id == "n1"
    assert item.organization_id == "org-1"
    assert item.node_type == "task"


def test_dependency_creation():
    item = dependency("d1", "n1", "n2")

    assert item.dependency_id == "d1"
    assert item.source_node_id == "n1"
    assert item.target_node_id == "n2"


def test_self_dependency_rejected():
    try:
        ITDependency(
            "d1",
            "org-1",
            "n1",
            "n1",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("self dependency must fail")


def test_invalid_node_type():
    try:
        ITDependencyNode(
            "n1",
            "org-1",
            "invalid",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid node type must fail")


def test_invalid_status():
    try:
        ITDependencyNode(
            "n1",
            "org-1",
            "task",
            status="invalid",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid status must fail")


def test_portfolio_rejects_duplicate_nodes():
    try:
        ITDependencyPortfolio(
            "org-1",
            nodes=(
                node("n1"),
                node("n1"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate node must fail")


def test_portfolio_rejects_unknown_source():
    try:
        ITDependencyPortfolio(
            "org-1",
            nodes=(node("n1"),),
            dependencies=(
                dependency("d1", "missing", "n1"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown source must fail")


def test_portfolio_rejects_unknown_target():
    try:
        ITDependencyPortfolio(
            "org-1",
            nodes=(node("n1"),),
            dependencies=(
                dependency("d1", "n1", "missing"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown target must fail")


def test_basic_dependency_counts():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n2", "n3"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.node_count == 3
    assert result.dependency_count == 2


def test_blocked_dependency_detection():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1", status="blocked"),
            node("n2"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.blocked_dependency_count == 1


def test_critical_dependency_detection():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1", status="in_progress"),
            node("n2", status="open"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.critical_dependency_count == 1


def test_dependency_hotspot():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
            node("n4"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n1", "n3"),
            dependency("d3", "n4", "n1"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.dependency_hotspot_node_id == "n1"
    assert result.dependency_hotspot_count == 3


def test_bottleneck_count():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
            node("n4"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n1", "n3"),
            dependency("d3", "n4", "n1"),
        ),
    )

    result = ITDependencyIntelligence(
        bottleneck_threshold=3
    ).analyze(portfolio)

    assert result.bottleneck_node_count == 1


def test_cycle_detection():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n2", "n3"),
            dependency("d3", "n3", "n1"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.cycle_count == 1


def test_multiple_cycles_detection():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
            node("n4"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n2", "n1"),
            dependency("d3", "n3", "n4"),
            dependency("d4", "n4", "n3"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.cycle_count == 2


def test_missing_owner_detection():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1", owner_id=None),
            node("n2"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.missing_owner_node_count == 1


def test_completed_and_cancelled_nodes_are_not_missing_owner():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1", status="completed", owner_id=None),
            node("n2", status="cancelled", owner_id=None),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.missing_owner_node_count == 0


def test_upstream_impact():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3", status="blocked"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n2", "n3"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.upstream_impact_node_count == 2


def test_deterministic_analysis():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n2"),
            node("n1"),
            node("n3"),
        ),
        dependencies=(
            dependency("d2", "n2", "n3"),
            dependency("d1", "n1", "n2"),
        ),
    )

    intelligence = ITDependencyIntelligence()

    first = intelligence.analyze(portfolio)
    second = intelligence.analyze(portfolio)

    assert first == second


def test_helper_function():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
        ),
    )

    result = analyze_it_dependencies(portfolio)

    assert isinstance(result, ITDependencyAnalysis)
    assert result.dependency_count == 1


def test_custom_bottleneck_threshold():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1"),
            node("n2"),
            node("n3"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
            dependency("d2", "n1", "n3"),
        ),
    )

    result = ITDependencyIntelligence(
        bottleneck_threshold=2
    ).analyze(portfolio)

    assert result.bottleneck_node_count == 1


def test_safety_boundary():
    portfolio = ITDependencyPortfolio(
        "org-1",
        nodes=(
            node("n1", status="blocked"),
            node("n2"),
        ),
        dependencies=(
            dependency("d1", "n1", "n2"),
        ),
    )

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.requires_human_approval is True
    assert result.executable is False


def test_invalid_portfolio_type():
    try:
        ITDependencyIntelligence().analyze(None)
    except TypeError:
        pass
    else:
        raise AssertionError("invalid portfolio type must fail")


def test_empty_portfolio():
    portfolio = ITDependencyPortfolio("org-1")

    result = ITDependencyIntelligence().analyze(portfolio)

    assert result.node_count == 0
    assert result.dependency_count == 0
    assert result.cycle_count == 0
    assert result.dependency_hotspot_node_id is None


def test_organization_mismatch_rejected():
    try:
        ITDependencyPortfolio(
            "org-1",
            nodes=(
                ITDependencyNode(
                    "n1",
                    "org-2",
                    "task",
                ),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("organization mismatch must fail")
