from yoma.office.it.it_risk_escalation import (
    ITRiskEscalationAnalysis,
    ITRiskEscalationIntelligence,
    ITRiskPortfolio,
    ITRiskSignal,
    ITRecommendation,
    analyze_it_risks,
)


def signal(
    signal_id,
    risk_type="project",
    level="normal",
    title="Risk",
    owner_id="u1",
    escalation_required=False,
    description="Observed IT risk",
):
    return ITRiskSignal(
        signal_id,
        "org-1",
        risk_type,
        level,
        title,
        description=description,
        owner_id=owner_id,
        escalation_required=escalation_required,
    )


def test_risk_signal_creation():
    item = signal(
        "r1",
        risk_type="project",
        level="high",
        title="Project delay",
    )

    assert item.signal_id == "r1"
    assert item.level == "high"
    assert item.risk_type == "project"


def test_invalid_risk_type():
    try:
        signal(
            "r1",
            risk_type="unknown",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid risk type must fail")


def test_invalid_risk_level():
    try:
        signal(
            "r1",
            level="urgent",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid risk level must fail")


def test_empty_title_rejected():
    try:
        ITRiskSignal(
            "r1",
            "org-1",
            "project",
            "high",
            "",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("empty title must fail")


def test_portfolio_organization_consistency():
    try:
        ITRiskPortfolio(
            "org-1",
            signals=(
                ITRiskSignal(
                    "r1",
                    "org-2",
                    "project",
                    "high",
                    "Risk",
                ),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("organization mismatch must fail")


def test_duplicate_signal_rejected():
    try:
        ITRiskPortfolio(
            "org-1",
            signals=(
                signal("r1"),
                signal("r1"),
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate signal must fail")


def test_risk_counts():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal("r1", level="low"),
            signal("r2", level="normal"),
            signal("r3", level="high"),
            signal("r4", level="critical"),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.signal_count == 4
    assert result.low_risk_count == 1
    assert result.normal_risk_count == 1
    assert result.high_risk_count == 1
    assert result.critical_risk_count == 1


def test_escalation_candidate_from_high_risk():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal("r1", level="high"),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.escalation_candidate_count == 1


def test_escalation_candidate_from_explicit_flag():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="normal",
                escalation_required=True,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.escalation_candidate_count == 1


def test_ownerless_high_risk():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="high",
                owner_id=None,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.ownerless_risk_count == 1


def test_ownerless_normal_risk_not_counted():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="normal",
                owner_id=None,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.ownerless_risk_count == 0


def test_top_risk_is_critical():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal("r1", level="high"),
            signal("r2", level="critical"),
            signal("r3", level="normal"),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.top_risk_signal_id == "r2"
    assert result.top_risk_level == "critical"


def test_top_risk_is_deterministic_for_same_level():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal("r2", level="high"),
            signal("r1", level="high"),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.top_risk_signal_id == "r2"


def test_recommendation_creation():
    item = ITRecommendation(
        "REC-r1",
        "r1",
        "org-1",
        "high",
        "Review risk",
        "High risk requires attention",
        "Request human review.",
    )

    assert item.recommendation_id == "REC-r1"
    assert item.requires_human_approval is True
    assert item.executable is False


def test_high_risk_generates_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                risk_type="project",
                level="high",
                title="Project delay",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.recommendation_count == 1
    assert result.recommendations[0].recommendation_id == "REC-r1"


def test_critical_recommendation_priority():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="critical",
                title="Production incident",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    recommendation = result.recommendations[0]

    assert recommendation.priority == "critical"
    assert "Escalate" in recommendation.recommended_action


def test_workload_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                risk_type="workload",
                level="high",
                title="Engineer overload",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert "workload" in result.recommendations[0].recommended_action.lower()


def test_dependency_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                risk_type="dependency",
                level="high",
                title="Blocked dependency",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert "dependency" in result.recommendations[0].recommended_action.lower()


def test_deployment_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                risk_type="deployment",
                level="critical",
                title="Failed production deployment",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert "deployment" in result.recommendations[0].recommended_action.lower()


def test_ticket_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                risk_type="ticket",
                level="high",
                title="SLA risk",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert "ticket" in result.recommendations[0].recommended_action.lower()


def test_low_risk_does_not_generate_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="low",
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.recommendation_count == 0


def test_normal_risk_without_escalation_does_not_generate_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="normal",
                escalation_required=False,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.recommendation_count == 0


def test_normal_risk_with_escalation_generates_recommendation():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="normal",
                escalation_required=True,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.recommendation_count == 1
    assert result.recommendations[0].priority == "normal"


def test_deterministic_analysis():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal("r3", level="high"),
            signal("r1", level="critical"),
            signal("r2", level="high"),
        ),
    )

    intelligence = ITRiskEscalationIntelligence()

    first = intelligence.analyze(portfolio)
    second = intelligence.analyze(portfolio)

    assert first == second


def test_helper_function():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="critical",
            ),
        ),
    )

    result = analyze_it_risks(portfolio)

    assert isinstance(result, ITRiskEscalationAnalysis)
    assert result.recommendation_count == 1


def test_safety_boundary():
    portfolio = ITRiskPortfolio(
        "org-1",
        signals=(
            signal(
                "r1",
                level="critical",
                escalation_required=True,
            ),
        ),
    )

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.requires_human_approval is True
    assert result.executable is False

    for recommendation in result.recommendations:
        assert recommendation.requires_human_approval is True
        assert recommendation.executable is False


def test_empty_portfolio():
    portfolio = ITRiskPortfolio("org-1")

    result = ITRiskEscalationIntelligence().analyze(portfolio)

    assert result.signal_count == 0
    assert result.recommendation_count == 0
    assert result.top_risk_signal_id is None
    assert result.top_risk_level is None
    assert result.issues


def test_invalid_portfolio_type():
    try:
        ITRiskEscalationIntelligence().analyze(None)
    except TypeError:
        pass
    else:
        raise AssertionError("invalid portfolio type must fail")


def test_recommendation_rejects_executable():
    try:
        ITRecommendation(
            "REC-r1",
            "r1",
            "org-1",
            "high",
            "Risk",
            "Reason",
            "Action",
            executable=True,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "executable recommendation must fail"
        )


def test_recommendation_requires_human_approval():
    try:
        ITRecommendation(
            "REC-r1",
            "r1",
            "org-1",
            "high",
            "Risk",
            "Reason",
            "Action",
            requires_human_approval=False,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "recommendation without human approval must fail"
        )
