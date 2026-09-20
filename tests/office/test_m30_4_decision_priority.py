from datetime import datetime, timezone

import pytest

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.decision_priority import (
    DecisionPriorityRanker,
    DecisionPriorityRanking,
    DecisionPriorityScore,
    RankedDecision,
)


NOW = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_decision(
    decision_id="DINT-1",
    priority="normal",
    confidence=0.50,
    current=True,
    historical=False,
    predictive=False,
    evidence=(),
    approval=True,
):
    return DecisionIntelligence(
        decision_id=decision_id,
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        situation_type="workload.high",
        priority=priority,
        confidence=confidence,
        current_intelligence_available=current,
        historical_intelligence_available=historical,
        predictive_intelligence_available=predictive,
        current_decision_ids=(
            "DEC-1",
        )
        if current
        else (),
        historical_context_ids=(
            "HIST-1",
        )
        if historical
        else (),
        predictive_context_ids=(
            "PRED-1",
        )
        if predictive
        else (),
        evidence=tuple(evidence),
        recommendation_type="workload_review",
        recommendation_reason="Review workload.",
        requires_human_approval=approval,
    )


def evidence(
    evidence_id,
    weight,
):
    return DecisionIntelligenceEvidence(
        evidence_id=evidence_id,
        evidence_type="test",
        source_id=evidence_id,
        description="Test evidence.",
        weight=weight,
        data={},
    )


def test_score_returns_decision_priority_score():
    decision = make_decision(
        priority="high",
        confidence=0.80,
    )

    result = DecisionPriorityRanker.score(
        decision
    )

    assert isinstance(
        result,
        DecisionPriorityScore,
    )
    assert result.decision_id == "DINT-1"


def test_priority_weight_is_deterministic():
    low = DecisionPriorityRanker.score(
        make_decision(priority="low")
    )
    normal = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-2",
            priority="normal",
        )
    )
    high = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-3",
            priority="high",
        )
    )
    critical = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-4",
            priority="critical",
        )
    )

    assert (
        low.priority_score
        < normal.priority_score
        < high.priority_score
        < critical.priority_score
    )


def test_confidence_is_bounded():
    decision = make_decision(
        confidence=1.0
    )

    result = DecisionPriorityRanker.score(
        decision
    )

    assert 0.0 <= result.confidence_score <= 1.0


def test_intelligence_score_counts_available_layers():
    decision = make_decision(
        current=True,
        historical=True,
        predictive=True,
    )

    result = DecisionPriorityRanker.score(
        decision
    )

    assert result.intelligence_score == 1.0


def test_intelligence_score_for_current_only():
    decision = make_decision(
        current=True,
        historical=False,
        predictive=False,
    )

    result = DecisionPriorityRanker.score(
        decision
    )

    assert result.intelligence_score == pytest.approx(
        1.0 / 3.0
    )


def test_evidence_score_increases_with_evidence():
    no_evidence = DecisionPriorityRanker.score(
        make_decision()
    )

    with_evidence = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-2",
            evidence=(
                evidence("E1", 0.80),
                evidence("E2", 0.90),
                evidence("E3", 1.00),
            ),
        )
    )

    assert (
        with_evidence.evidence_score
        > no_evidence.evidence_score
    )


def test_predictive_intelligence_increases_urgency():
    current = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-1",
            predictive=False,
        )
    )

    predictive = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-2",
            predictive=True,
        )
    )

    assert predictive.urgency_score > (
        current.urgency_score
    )


def test_historical_intelligence_has_intermediate_urgency():
    historical = DecisionPriorityRanker.score(
        make_decision(
            historical=True,
        )
    )

    current = DecisionPriorityRanker.score(
        make_decision(
            decision_id="DINT-2",
        )
    )

    assert historical.urgency_score > (
        current.urgency_score
    )


def test_rank_returns_ranking_object():
    result = DecisionPriorityRanker.rank(
        (
            make_decision(
                decision_id="DINT-1",
            ),
            make_decision(
                decision_id="DINT-2",
                priority="high",
            ),
        )
    )

    assert isinstance(
        result,
        DecisionPriorityRanking,
    )


def test_high_priority_ranks_above_normal():
    normal = make_decision(
        decision_id="DINT-NORMAL",
        priority="normal",
        confidence=0.50,
    )

    high = make_decision(
        decision_id="DINT-HIGH",
        priority="high",
        confidence=0.50,
    )

    result = DecisionPriorityRanker.rank(
        (normal, high)
    )

    assert (
        result.ranked_decisions[0].decision
        == high
    )
    assert (
        result.ranked_decisions[0].score.rank
        == 1
    )


def test_ranking_is_deterministic_on_ties():
    first = make_decision(
        decision_id="DINT-A",
    )
    second = make_decision(
        decision_id="DINT-B",
    )

    result = DecisionPriorityRanker.rank(
        (second, first)
    )

    assert [
        item.decision.decision_id
        for item in result.ranked_decisions
    ] == [
        "DINT-A",
        "DINT-B",
    ]


def test_top_decision():
    first = make_decision(
        decision_id="DINT-A",
        priority="normal",
    )
    second = make_decision(
        decision_id="DINT-B",
        priority="critical",
    )

    result = DecisionPriorityRanker.rank(
        (first, second)
    )

    assert result.top_decision == second


def test_rank_count():
    result = DecisionPriorityRanker.rank(
        (
            make_decision(
                decision_id="DINT-A",
            ),
            make_decision(
                decision_id="DINT-B",
            ),
            make_decision(
                decision_id="DINT-C",
            ),
        )
    )

    assert result.count == 3


def test_decisions_property_preserves_rank_order():
    first = make_decision(
        decision_id="DINT-A",
        priority="critical",
    )
    second = make_decision(
        decision_id="DINT-B",
        priority="low",
    )

    result = DecisionPriorityRanker.rank(
        (second, first)
    )

    assert tuple(
        item.decision_id
        for item in result.decisions
    ) == (
        "DINT-A",
        "DINT-B",
    )


def test_scores_property_matches_ranked_items():
    result = DecisionPriorityRanker.rank(
        (
            make_decision(
                decision_id="DINT-A",
            ),
            make_decision(
                decision_id="DINT-B",
                priority="high",
            ),
        )
    )

    assert len(result.scores) == 2
    assert result.scores[0].rank == 1
    assert result.scores[1].rank == 2


def test_human_review_is_preserved():
    result = DecisionPriorityRanker.rank(
        (
            make_decision(
                decision_id="DINT-A",
                approval=True,
            ),
        )
    )

    assert result.requires_human_review is True


def test_empty_ranking_is_safe():
    result = DecisionPriorityRanker.rank(())

    assert result.count == 0
    assert result.top_decision is None
    assert result.decisions == ()


def test_invalid_decision_type():
    with pytest.raises(TypeError):
        DecisionPriorityRanker.score(
            object()
        )


def test_score_components_are_bounded():
    decision = make_decision(
        priority="critical",
        confidence=1.0,
        current=True,
        historical=True,
        predictive=True,
        evidence=(
            evidence("E1", 1.0),
            evidence("E2", 1.0),
            evidence("E3", 1.0),
            evidence("E4", 1.0),
            evidence("E5", 1.0),
        ),
    )

    result = DecisionPriorityRanker.score(
        decision
    )

    assert 0.0 <= result.total_score <= 1.0
    assert 0.0 <= result.priority_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0
    assert 0.0 <= result.intelligence_score <= 1.0
    assert 0.0 <= result.evidence_score <= 1.0
    assert 0.0 <= result.urgency_score <= 1.0


def test_no_autonomous_actions_are_created():
    result = DecisionPriorityRanker.rank(
        (
            make_decision(
                decision_id="DINT-A",
            ),
        )
    )

    assert result.top_decision is not None
    assert (
        result.top_decision.requires_human_approval
        is True
    )
