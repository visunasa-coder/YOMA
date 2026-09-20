"""Tests for M30.2 current + historical decision fusion."""

from datetime import datetime

import pytest

from yoma.office.current_historical_decision_fusion import (
    CurrentHistoricalDecisionFusion,
)
from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision.rules import workload_decision
from yoma.office.historical_decision_context import (
    HistoricalDecisionContext,
)
from yoma.office.operations.model import OperationalSignal


BASE = datetime(2026, 9, 5, 12, 0, 0)


def make_signal(
    signal_id="SIG-1",
    signal_type="workload.high",
    score=0.80,
):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=BASE,
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        score=score,
        severity="high",
        evidence_event_ids=("EV1",),
    )


def make_current(signal=None):
    signal = signal or make_signal()

    return DecisionContext(
        signal=signal,
        recommendations=({
            "type": "workload_review",
            "reason": (
                "Operational workload signal requires human review."
            ),
        },),
        actions=(),
        requires_human_approval=True,
    )


def make_historical(
    situation_id="SIT-1",
    occurrence_count=4,
):
    return HistoricalDecisionContext(
        situation_id=situation_id,
        situation_type="workload.high",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        occurrence_count=occurrence_count,
        historical_pattern_id="HPAT-1",
        baseline_daily_frequency=0.13,
        recent_daily_frequency=0.29,
        previous_daily_frequency=0.14,
        deviation_from_baseline=0.80,
        frequency_change=0.15,
        trend_ratio=2.07,
        trend_direction="increasing",
        average_recurrence_interval_seconds=604800.0,
        historical_situation_ids=("S1", "S2", "S3", "S4"),
        evidence=(
            "historical workload pressure",
        ),
        requires_human_approval=True,
    )


def test_fuses_current_and_historical():
    current = make_current()
    historical = make_historical()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert result.current_intelligence_available is True
    assert result.historical_intelligence_available is True
    assert result.current_decision_ids == ("DEC-SIG-1",)
    assert result.historical_context_ids == ("SIT-1",)


def test_current_evidence_preserved():
    current = make_current()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (),
    ).fuse(current)

    assert any(
        evidence.evidence_type == "current"
        for evidence in result.evidence
    )


def test_historical_evidence_added():
    current = make_current()
    historical = make_historical()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert any(
        evidence.evidence_type == "historical"
        for evidence in result.evidence
    )


def test_no_historical_match_is_safe():
    current = make_current()

    historical = make_historical()
    historical = HistoricalDecisionContext(
        situation_id=historical.situation_id,
        situation_type=historical.situation_type,
        organization_id="OTHER",
        user_id=historical.user_id,
        system_id=historical.system_id,
        occurrence_count=historical.occurrence_count,
        historical_pattern_id=historical.historical_pattern_id,
        baseline_daily_frequency=historical.baseline_daily_frequency,
        recent_daily_frequency=historical.recent_daily_frequency,
        previous_daily_frequency=historical.previous_daily_frequency,
        deviation_from_baseline=historical.deviation_from_baseline,
        frequency_change=historical.frequency_change,
        trend_ratio=historical.trend_ratio,
        trend_direction=historical.trend_direction,
        average_recurrence_interval_seconds=(
            historical.average_recurrence_interval_seconds
        ),
        historical_situation_ids=historical.historical_situation_ids,
        evidence=historical.evidence,
        requires_human_approval=True,
    )

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert result.historical_intelligence_available is False
    assert result.historical_context_ids == ()


def test_insufficient_historical_occurrences_are_not_used():
    current = make_current()
    historical = make_historical(occurrence_count=1)

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert result.historical_intelligence_available is False
    assert result.historical_context_ids == ()


def test_scope_is_explicit():
    current = make_current()
    historical = make_historical()

    historical = HistoricalDecisionContext(
        situation_id=historical.situation_id,
        situation_type=historical.situation_type,
        organization_id=historical.organization_id,
        user_id="OTHER",
        system_id=historical.system_id,
        occurrence_count=historical.occurrence_count,
        historical_pattern_id=historical.historical_pattern_id,
        baseline_daily_frequency=historical.baseline_daily_frequency,
        recent_daily_frequency=historical.recent_daily_frequency,
        previous_daily_frequency=historical.previous_daily_frequency,
        deviation_from_baseline=historical.deviation_from_baseline,
        frequency_change=historical.frequency_change,
        trend_ratio=historical.trend_ratio,
        trend_direction=historical.trend_direction,
        average_recurrence_interval_seconds=(
            historical.average_recurrence_interval_seconds
        ),
        historical_situation_ids=historical.historical_situation_ids,
        evidence=historical.evidence,
        requires_human_approval=True,
    )

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert result.historical_context_ids == ()


def test_confidence_is_bounded():
    current = make_current(make_signal(score=0.95))
    historical = make_historical()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert 0.0 <= result.confidence <= 1.0


def test_priority_is_deterministic():
    current = make_current()
    historical = make_historical()

    fusion = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    )

    first = fusion.fuse(current)
    second = fusion.fuse(current)

    assert first.priority == second.priority
    assert first.confidence == second.confidence
    assert first.decision_id == second.decision_id


def test_recommendation_is_preserved():
    current = make_current()
    historical = make_historical()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert result.recommendation_type == "workload_review"


def test_human_approval_remains_required():
    current = make_current()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (),
    ).fuse(current)

    assert result.requires_human_approval is True
    assert result.requires_review is True


def test_no_predictive_context_in_m30_2():
    current = make_current()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (),
    ).fuse(current)

    assert result.predictive_intelligence_available is False
    assert result.predictive_context_ids == ()


def test_fusion_metadata():
    current = make_current()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (),
    ).fuse(current)

    assert result.metadata["fusion"] == "current_historical"
    assert result.metadata["historical_match"] is False


def test_fuse_many_is_deterministic():
    first = make_current(make_signal("SIG-B", score=0.70))
    second = make_current(make_signal("SIG-A", score=0.80))

    fusion = CurrentHistoricalDecisionFusion()

    results = fusion.fuse_many((first, second))

    assert [item.decision_id for item in results] == [
        "DINT-ORG1-U1-GLOBAL-SIG-A",
        "DINT-ORG1-U1-GLOBAL-SIG-B",
    ]


def test_type_validation():
    fusion = CurrentHistoricalDecisionFusion()

    with pytest.raises(TypeError):
        fusion.fuse("not-a-decision")


def test_advisory_only():
    current = make_current()
    historical = make_historical()

    result = CurrentHistoricalDecisionFusion(
        (current,),
        (historical,),
    ).fuse(current)

    assert not hasattr(result, "actions")
    assert result.requires_human_approval is True
