from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.predictive_signal import PredictiveSignal
from yoma.office.risk_forecast import (
    RiskForecast,
    RiskForecaster,
)


def prediction(
    likelihood=0.80,
    confidence=0.90,
    trend_direction="increasing",
):
    base = datetime(
        2026,
        1,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )

    return PredictiveSignal(
        prediction_id="PRED-workload_pressure-org-1-user-1-GLOBAL-test",
        prediction_type="recurrence_prediction",
        situation_type="workload_pressure",
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        recurrence_likelihood=likelihood,
        confidence=confidence,
        predicted_next_occurrence_start=(
            base + timedelta(days=1)
        ),
        predicted_next_occurrence_end=(
            base + timedelta(days=2)
        ),
        historical_occurrences=5,
        baseline_daily_frequency=0.5,
        recent_daily_frequency=0.8,
        previous_daily_frequency=0.2,
        trend_direction=trend_direction,
        trend_ratio=4.0,
        deviation_from_baseline=0.6,
        average_recurrence_interval_seconds=86400.0,
        historical_pattern_id="HPAT-test",
        evidence_situation_ids=(
            "s1",
            "s2",
            "s3",
        ),
        evidence=(
            "historical_occurrences:5",
            "trend_direction:increasing",
        ),
        requires_human_approval=True,
    )


def test_builds_risk_forecast():
    result = RiskForecaster().forecast(
        prediction()
    )

    assert isinstance(
        result,
        RiskForecast,
    )

    assert result.forecast_type == (
        "operational_risk_forecast"
    )

    assert result.situation_type == (
        "workload_pressure"
    )


def test_risk_probability_is_bounded():
    result = RiskForecaster().forecast(
        prediction(
            likelihood=1.0,
            confidence=1.0,
        )
    )

    assert 0.0 <= result.risk_probability <= 1.0


def test_confidence_is_preserved():
    result = RiskForecaster().forecast(
        prediction(
            confidence=0.73
        )
    )

    assert result.confidence == 0.73


def test_high_probability_produces_high_risk():
    result = RiskForecaster().forecast(
        prediction(
            likelihood=0.95,
            confidence=1.0,
        )
    )

    assert result.risk_probability == 0.95
    assert result.risk_severity == "critical"
    assert result.high_risk is True
    assert result.elevated is True


def test_medium_probability_produces_warning():
    result = RiskForecaster().forecast(
        prediction(
            likelihood=0.60,
            confidence=0.50,
        )
    )

    assert result.risk_probability == 0.45
    assert result.risk_severity == "warning"


def test_low_probability_produces_info():
    result = RiskForecaster().forecast(
        prediction(
            likelihood=0.20,
            confidence=0.50,
        )
    )

    assert result.risk_probability == 0.15
    assert result.risk_severity == "info"


def test_forecast_window_is_preserved():
    original = prediction()

    result = RiskForecaster().forecast(
        original
    )

    assert (
        result.forecast_start
        == original.predicted_next_occurrence_start
    )

    assert (
        result.forecast_end
        == original.predicted_next_occurrence_end
    )

    assert result.forecast_available is True


def test_scope_is_preserved():
    result = RiskForecaster().forecast(
        prediction()
    )

    assert result.organization_id == "org-1"
    assert result.user_id == "user-1"
    assert result.system_id is None


def test_historical_evidence_is_preserved():
    result = RiskForecaster().forecast(
        prediction()
    )

    assert result.historical_pattern_id == "HPAT-test"

    assert result.evidence_situation_ids == (
        "s1",
        "s2",
        "s3",
    )


def test_trend_information_is_preserved():
    result = RiskForecaster().forecast(
        prediction(
            trend_direction="decreasing"
        )
    )

    assert result.trend_direction == "decreasing"
    assert result.trend_ratio == 4.0
    assert result.baseline_deviation == 0.6


def test_forecast_id_is_deterministic():
    forecaster = RiskForecaster()

    first = forecaster.forecast(
        prediction()
    )

    second = forecaster.forecast(
        prediction()
    )

    assert first.forecast_id == second.forecast_id


def test_evidence_contains_risk_result():
    result = RiskForecaster().forecast(
        prediction()
    )

    assert any(
        item.startswith("risk_probability:")
        for item in result.evidence
    )

    assert any(
        item.startswith("risk_severity:")
        for item in result.evidence
    )


def test_no_prediction_risk_is_safe():
    result = RiskForecaster().forecast(
        prediction(
            likelihood=0.0,
            confidence=0.0,
        )
    )

    assert result.risk_probability == 0.0
    assert result.risk_severity == "info"
    assert result.elevated is False
    assert result.high_risk is False


def test_forecast_many():
    forecaster = RiskForecaster()

    results = forecaster.forecast_many(
        [
            prediction(0.8),
            prediction(0.4),
        ]
    )

    assert len(results) == 2
    assert (
        results[0].forecast_id
        == results[1].forecast_id
    )


def test_human_approval_is_required():
    result = RiskForecaster().forecast(
        prediction()
    )

    assert result.requires_human_approval is True


def test_invalid_prediction_rejected():
    with pytest.raises(TypeError):
        RiskForecaster().forecast(
            object()
        )
