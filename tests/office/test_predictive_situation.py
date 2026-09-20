from datetime import datetime, timedelta

import pytest

from yoma.office.predictive_signal import PredictiveSignal
from yoma.office.risk_forecast import RiskForecast
from yoma.office.recurrence_prediction import RecurrencePrediction
from yoma.office.workload_forecast import WorkloadForecast
from yoma.office.predictive_situation import (
    PredictiveSituation,
    PredictiveSituationDetector,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)
NEXT = BASE + timedelta(days=7)


def make_signal():
    return PredictiveSignal(
        prediction_id="PRED-S1",
        prediction_type="predictive_signal",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        recurrence_likelihood=0.70,
        confidence=0.80,
        predicted_next_occurrence_start=NEXT - timedelta(hours=1),
        predicted_next_occurrence_end=NEXT + timedelta(hours=1),
        historical_occurrences=3,
        baseline_daily_frequency=0.14,
        recent_daily_frequency=0.28,
        previous_daily_frequency=0.14,
        trend_direction="increasing",
        trend_ratio=1.5,
        deviation_from_baseline=0.5,
        average_recurrence_interval_seconds=604800.0,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S1", "S2", "S3"),
        evidence=("historical recurrence",),
    )


def make_risk():
    return RiskForecast(
        forecast_id="RISK-PRED-S1",
        forecast_type="risk_forecast",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        risk_probability=0.80,
        confidence=0.75,
        risk_severity="high",
        forecast_start=NEXT - timedelta(hours=2),
        forecast_end=NEXT + timedelta(hours=2),
        trend_direction="increasing",
        trend_ratio=1.5,
        baseline_deviation=0.5,
        historical_occurrences=3,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S1", "S2"),
        evidence=("risk evidence",),
    )


def make_recurrence():
    return RecurrencePrediction(
        prediction_id="REC-S1",
        prediction_type="recurrence_prediction",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        recurrence_probability=0.70,
        confidence=0.80,
        predicted_next_occurrence_start=NEXT - timedelta(hours=1),
        predicted_next_occurrence_end=NEXT + timedelta(hours=1),
        recurrence_interval_seconds=604800.0,
        historical_occurrences=3,
        trend_direction="increasing",
        trend_ratio=1.5,
        deviation_from_baseline=0.5,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S2", "S3"),
        evidence=("recurrence evidence",),
    )


def make_workload():
    return WorkloadForecast(
        forecast_id="WLF-S1",
        forecast_type="workload_forecast",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        forecast_start=NEXT - timedelta(days=1),
        forecast_end=NEXT + timedelta(days=6),
        baseline_daily_frequency=0.14,
        forecast_daily_frequency=0.42,
        recent_daily_frequency=0.28,
        previous_daily_frequency=0.14,
        frequency_change=0.14,
        deviation_from_baseline=0.50,
        trend_ratio=1.5,
        trend_direction="increasing",
        workload_probability=0.75,
        confidence=0.70,
        historical_occurrences=3,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S3", "S4"),
        evidence=("workload evidence",),
    )


def test_predictive_situation_dataclass_is_advisory():
    result = PredictiveSituation(
        prediction_id="PS1",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        predicted_at=BASE,
        forecast_start=NEXT,
        forecast_end=NEXT + timedelta(hours=1),
        probability=0.70,
        confidence=0.80,
        severity="high",
        prediction_sources=("predictive_signal",),
        evidence_situation_ids=("S1",),
        evidence=("evidence",),
    )

    assert result.requires_human_approval is True
    assert result.elevated is True
    assert result.detection_available is True
    assert result.historical_evidence_available is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("probability", -0.1),
        ("probability", 1.1),
        ("confidence", -0.1),
        ("confidence", 1.1),
    ],
)
def test_probability_and_confidence_are_bounded(field, value):
    kwargs = dict(
        prediction_id="PS1",
        situation_type="x",
        organization_id=None,
        user_id=None,
        system_id=None,
        predicted_at=BASE,
        forecast_start=None,
        forecast_end=None,
        probability=0.5,
        confidence=0.5,
        severity="info",
        prediction_sources=(),
        evidence_situation_ids=(),
        evidence=(),
    )

    kwargs[field] = value

    with pytest.raises(ValueError):
        PredictiveSituation(**kwargs)


def test_detector_combines_all_predictive_sources():
    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(make_signal())

    assert result.situation_type == "workload_pressure"
    assert result.organization_id == "ORG1"
    assert result.user_id == "U1"
    assert result.prediction_sources == (
        "predictive_signal",
        "risk_forecast",
        "recurrence_prediction",
        "workload_forecast",
    )
    assert result.probability == 0.7375
    assert result.confidence == 0.7625
    assert result.severity == "high"


def test_evidence_situation_ids_are_deduplicated():
    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(make_signal())

    assert result.evidence_situation_ids == (
        "S1",
        "S2",
        "S3",
        "S4",
    )


def test_forecast_window_combines_available_predictions():
    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(make_signal())

    assert result.forecast_start == NEXT - timedelta(hours=2)
    assert result.forecast_end == NEXT + timedelta(days=6)


def test_scope_isolation_prevents_cross_entity_prediction_leakage():
    signal = PredictiveSignal(
        prediction_id="PRED-OTHER",
        prediction_type="predictive_signal",
        situation_type="workload_pressure",
        organization_id="ORG2",
        user_id="U2",
        system_id=None,
        recurrence_likelihood=0.60,
        confidence=0.60,
        predicted_next_occurrence_start=NEXT,
        predicted_next_occurrence_end=NEXT + timedelta(hours=1),
        historical_occurrences=2,
        baseline_daily_frequency=0.1,
        recent_daily_frequency=0.2,
        previous_daily_frequency=0.1,
        trend_direction="increasing",
        trend_ratio=1.5,
        deviation_from_baseline=0.3,
        average_recurrence_interval_seconds=604800.0,
        historical_pattern_id="HP2",
        evidence_situation_ids=("OTHER",),
        evidence=("other",),
    )

    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(signal)

    assert result.prediction_sources == ("predictive_signal",)
    assert result.evidence_situation_ids == ("OTHER",)


def test_detector_is_deterministic():
    detector = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    )

    first = detector.detect(make_signal())
    second = detector.detect(make_signal())

    assert first == second


def test_prediction_id_is_deterministic():
    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(make_signal())

    assert result.prediction_id == "PSIT-PRED-S1"


def test_without_secondary_sources_remains_conservative():
    signal = make_signal()

    result = PredictiveSituationDetector(
        [signal],
        [],
        [],
        [],
    ).detect(signal)

    assert result.probability == 0.70
    assert result.confidence == 0.80
    assert result.severity == "high"
    assert result.prediction_sources == ("predictive_signal",)
    assert result.historical_evidence_available is True


def test_detect_many_preserves_order():
    detector = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    )

    results = detector.detect_many(
        [make_signal(), make_signal()]
    )

    assert len(results) == 2
    assert results[0] == results[1]


def test_no_autonomous_action_is_created():
    result = PredictiveSituationDetector(
        [make_signal()],
        [make_risk()],
        [make_recurrence()],
        [make_workload()],
    ).detect(make_signal())

    assert result.requires_human_approval is True
