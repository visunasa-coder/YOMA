from datetime import datetime, timezone

import pytest

from yoma.office.decision.orchestrator import (
    DecisionContext,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
)
from yoma.office.historical_decision_context import (
    HistoricalDecisionContext,
)
from yoma.office.operations.model import (
    OperationalSignal,
)
from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
    PredictiveDecisionRecommendation,
)
from yoma.office.predictive_decision_fusion import (
    PredictiveDecisionFusion,
)


NOW = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_current(
    *,
    score=0.80,
    organization_id="ORG1",
    user_id="U1",
    system_id=None,
):
    signal = OperationalSignal(
        signal_id="SIG-1",
        signal_type="workload.high",
        detected_at=NOW,
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        score=score,
        severity="high",
        evidence_event_ids=("EV-1",),
        data={},
    )

    return DecisionContext(
        signal=signal,
        recommendations=(
            {
                "type": "workload_review",
                "reason": (
                    "Operational workload signal "
                    "requires human review."
                ),
                "employee_id": user_id,
                "score": score,
            },
        ),
        actions=(),
        requires_human_approval=True,
    )


def make_historical(
    *,
    occurrence_count=3,
    organization_id="ORG1",
    user_id="U1",
    system_id=None,
):
    return HistoricalDecisionContext(
        situation_id="SIT-HIST-1",
        situation_type="workload.high",
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        occurrence_count=occurrence_count,
        historical_pattern_id="HPAT-1",
        baseline_daily_frequency=0.40,
        recent_daily_frequency=0.70,
        previous_daily_frequency=0.50,
        deviation_from_baseline=0.30,
        frequency_change=0.20,
        trend_ratio=1.40,
        trend_direction="rising",
        average_recurrence_interval_seconds=86400.0,
        historical_situation_ids=(
            "SIT-OLD-1",
            "SIT-OLD-2",
            "SIT-OLD-3",
        ),
        evidence=(
            "Repeated workload pressure.",
        ),
        requires_human_approval=True,
    )


def make_predictive(
    *,
    probability=0.80,
    confidence=0.75,
    organization_id="ORG1",
    user_id="U1",
    system_id=None,
):
    recommendation = PredictiveDecisionRecommendation(
        recommendation_id="PREC-REC-1",
        recommendation_type=(
            "predictive_workload_review"
        ),
        reason=(
            "Predicted workload pressure "
            "requires human review."
        ),
        priority="high",
        target_user_id=user_id,
        target_system_id=system_id,
        evidence=(
            "Historical recurrence supports "
            "future workload risk.",
        ),
        requires_human_approval=True,
    )

    return PredictiveDecisionContext(
        context_id="PCTX-1",
        prediction_id="PRED-1",
        situation_type="workload.high",
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        created_at=NOW,
        probability=probability,
        confidence=confidence,
        severity="high",
        forecast_start=NOW,
        forecast_end=(
            NOW.replace(day=6)
        ),
        recommendation=recommendation,
        evidence_situation_ids=(
            "SIT-1",
            "SIT-2",
        ),
        evidence=(
            "Predicted recurrence.",
        ),
        actions=(),
        requires_human_approval=True,
    )


def test_fuses_current_historical_and_predictive():
    current = make_current()
    historical = make_historical()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (historical,),
        (predictive,),
    ).fuse(current)

    assert isinstance(
        result,
        DecisionIntelligence,
    )
    assert result.current_intelligence_available is True
    assert result.historical_intelligence_available is True
    assert result.predictive_intelligence_available is True


def test_predictive_context_is_preserved():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.predictive_context_ids == (
        "PCTX-1",
    )


def test_predictive_evidence_is_added():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert any(
        item.evidence_id == "PRED-PRED-1"
        for item in result.evidence
    )


def test_current_evidence_is_preserved():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert any(
        item.evidence_id == "CURRENT-SIG-1"
        for item in result.evidence
    )


def test_historical_evidence_is_preserved():
    current = make_current()
    historical = make_historical()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (historical,),
        (predictive,),
    ).fuse(current)

    assert any(
        item.evidence_id == "HIST-SIT-HIST-1"
        for item in result.evidence
    )


def test_predictive_scope_is_explicit():
    current = make_current(
        organization_id="ORG1",
        user_id="U1",
    )
    predictive = make_predictive(
        organization_id="ORG2",
        user_id="U1",
    )

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.predictive_intelligence_available is False
    assert result.predictive_context_ids == ()


def test_predictive_user_scope_is_explicit():
    current = make_current(
        organization_id="ORG1",
        user_id="U1",
    )
    predictive = make_predictive(
        organization_id="ORG1",
        user_id="U2",
    )

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.predictive_intelligence_available is False


def test_predictive_system_scope_is_explicit():
    current = make_current(
        system_id="SYS1",
    )
    predictive = make_predictive(
        system_id="SYS2",
    )

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.predictive_intelligence_available is False


def test_situation_type_must_match():
    current = make_current()
    predictive = make_predictive()

    predictive = PredictiveDecisionContext(
        context_id=predictive.context_id,
        prediction_id=predictive.prediction_id,
        situation_type="meeting_load.high",
        organization_id=predictive.organization_id,
        user_id=predictive.user_id,
        system_id=predictive.system_id,
        created_at=predictive.created_at,
        probability=predictive.probability,
        confidence=predictive.confidence,
        severity=predictive.severity,
        forecast_start=predictive.forecast_start,
        forecast_end=predictive.forecast_end,
        recommendation=predictive.recommendation,
        evidence_situation_ids=predictive.evidence_situation_ids,
        evidence=predictive.evidence,
        actions=predictive.actions,
        requires_human_approval=True,
    )

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.predictive_intelligence_available is False


def test_predictive_recommendation_can_enrich_current_recommendation():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.recommendation_type == (
        "workload_review"
    )
    assert result.recommendation_reason == (
        "Operational workload signal "
        "requires human review."
    )


def test_confidence_is_bounded():
    current = make_current(score=1.0)
    predictive = make_predictive(
        probability=1.0,
        confidence=1.0,
    )

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert 0.0 <= result.confidence <= 1.0


def test_predictive_priority_is_deterministic():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.priority == "high"


def test_single_historical_occurrence_is_not_used():
    current = make_current()
    historical = make_historical(
        occurrence_count=1,
    )
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (historical,),
        (predictive,),
    ).fuse(current)

    assert result.historical_intelligence_available is False
    assert result.predictive_intelligence_available is True


def test_no_predictive_match_is_safe():
    current = make_current()
    historical = make_historical()

    result = PredictiveDecisionFusion(
        (current,),
        (historical,),
        (),
    ).fuse(current)

    assert result.current_intelligence_available is True
    assert result.historical_intelligence_available is True
    assert result.predictive_intelligence_available is False
    assert result.predictive_context_ids == ()


def test_human_approval_remains_required():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.requires_human_approval is True


def test_predictive_actions_are_never_added():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert predictive.actions == ()
    assert result.requires_human_approval is True


def test_fusion_metadata():
    current = make_current()
    historical = make_historical()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (historical,),
        (predictive,),
    ).fuse(current)

    assert (
        result.metadata["fusion"]
        == "current_historical_predictive"
    )
    assert (
        result.metadata["historical_match"]
        is True
    )
    assert (
        result.metadata["predictive_match"]
        is True
    )
    assert (
        result.metadata["prediction_id"]
        == "PRED-1"
    )


def test_fuse_many_is_deterministic():
    current_a = make_current()
    current_b = make_current(
        user_id="U2",
    )

    predictive_a = make_predictive()
    predictive_b = make_predictive(
        user_id="U2",
    )

    fusion = PredictiveDecisionFusion(
        (current_b, current_a),
        (),
        (predictive_b, predictive_a),
    )

    results = fusion.fuse_many()

    assert tuple(
        item.decision_id
        for item in results
    ) == tuple(
        sorted(
            item.decision_id
            for item in results
        )
    )


def test_type_validation():
    with pytest.raises(TypeError):
        PredictiveDecisionFusion().fuse(
            object(),
        )


def test_result_has_no_autonomous_action_contract():
    current = make_current()
    predictive = make_predictive()

    result = PredictiveDecisionFusion(
        (current,),
        (),
        (predictive,),
    ).fuse(current)

    assert result.requires_human_approval is True
