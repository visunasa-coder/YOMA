"""M29.8 unified predictive intelligence runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation
from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
    PredictiveDecisionContextBuilder,
)
from yoma.office.predictive_signal import (
    PredictiveSignal,
    PredictiveSignalEngine,
)
from yoma.office.predictive_situation import (
    PredictiveSituation,
    PredictiveSituationDetector,
)
from yoma.office.prediction_explainability import (
    PredictionExplainability,
    PredictionExplainabilityEngine,
)
from yoma.office.recurrence_prediction import (
    RecurrencePrediction,
    RecurrencePredictionEngine,
)
from yoma.office.risk_forecast import (
    RiskForecast,
    RiskForecaster,
)
from yoma.office.workload_forecast import (
    WorkloadForecast,
    WorkloadForecastEngine,
)


@dataclass(frozen=True)
class PredictiveIntelligenceResult:
    """Complete M29 predictive intelligence output."""

    predictive_signals: tuple[PredictiveSignal, ...]
    risk_forecasts: tuple[RiskForecast, ...]
    recurrence_predictions: tuple[RecurrencePrediction, ...]
    workload_forecasts: tuple[WorkloadForecast, ...]
    predictive_situations: tuple[PredictiveSituation, ...]
    decision_contexts: tuple[PredictiveDecisionContext, ...]
    explanations: tuple[PredictionExplainability, ...]

    @property
    def prediction_count(self) -> int:
        return len(self.predictive_signals)

    @property
    def elevated_predictions(
        self,
    ) -> tuple[PredictiveSignal, ...]:
        return tuple(
            signal
            for signal in self.predictive_signals
            if signal.elevated
        )

    @property
    def elevated_situations(
        self,
    ) -> tuple[PredictiveSituation, ...]:
        return tuple(
            situation
            for situation in self.predictive_situations
            if situation.elevated
        )

    @property
    def requires_human_review(self) -> bool:
        return any(
            context.requires_human_approval
            for context in self.decision_contexts
        )


class PredictiveIntelligenceRuntime:
    """
    Unified M29 predictive intelligence pipeline.

    Existing M29 engines remain the source of prediction logic.
    This runtime only composes their outputs.

    No persistence or autonomous action execution occurs here.
    """

    def __init__(
        self,
        historical_patterns: Sequence[HistoricalPattern] = (),
        baseline_trends: Sequence[BaselineTrend] = (),
        *,
        prediction_engine: Optional[PredictiveSignalEngine] = None,
        risk_forecaster: Optional[RiskForecaster] = None,
        recurrence_engine: Optional[
            RecurrencePredictionEngine
        ] = None,
        workload_engine: Optional[
            WorkloadForecastEngine
        ] = None,
        situation_detector: Optional[
            PredictiveSituationDetector
        ] = None,
        decision_builder: Optional[
            PredictiveDecisionContextBuilder
        ] = None,
        explainability_engine: Optional[
            PredictionExplainabilityEngine
        ] = None,
    ) -> None:
        self.historical_patterns = tuple(
            historical_patterns
        )
        self.baseline_trends = tuple(
            baseline_trends
        )

        self.prediction_engine = (
            prediction_engine
            or PredictiveSignalEngine(
                self.historical_patterns,
                self.baseline_trends,
            )
        )

        self.risk_forecaster = (
            risk_forecaster
            or RiskForecaster()
        )

        self.recurrence_engine = (
            recurrence_engine
            or RecurrencePredictionEngine(
                self.historical_patterns,
                self.baseline_trends,
            )
        )

        self.workload_engine = (
            workload_engine
            or WorkloadForecastEngine(
                self.historical_patterns,
                self.baseline_trends,
            )
        )

        self.situation_detector = situation_detector

        self.decision_builder = (
            decision_builder
            or PredictiveDecisionContextBuilder()
        )

        self.explainability_engine = (
            explainability_engine
            or PredictionExplainabilityEngine()
        )

        self._last_result: Optional[
            PredictiveIntelligenceResult
        ] = None

    @property
    def last_result(
        self,
    ) -> Optional[PredictiveIntelligenceResult]:
        return self._last_result

    def analyze(
        self,
        situations: Iterable[OperationalSituation],
    ) -> PredictiveIntelligenceResult:
        current_situations = tuple(situations)

        predictive_signals = tuple(
            self.prediction_engine.predict(
                situation
            )
            for situation in current_situations
        )

        risk_forecasts = tuple(
            self.risk_forecaster.forecast(
                prediction
            )
            for prediction in predictive_signals
        )

        recurrence_predictions = tuple(
            self.recurrence_engine.predict(
                situation
            )
            for situation in current_situations
        )

        workload_forecasts = tuple(
            self.workload_engine.forecast(
                situation
            )
            for situation in current_situations
        )

        detector = self.situation_detector

        if detector is None:
            detector = PredictiveSituationDetector(
                predictive_signals=predictive_signals,
                risk_forecasts=risk_forecasts,
                recurrence_predictions=(
                    recurrence_predictions
                ),
                workload_forecasts=(
                    workload_forecasts
                ),
            )

        predictive_situations = tuple(
            detector.detect(signal)
            for signal in predictive_signals
        )

        decision_contexts = tuple(
            self.decision_builder.build(
                prediction
            )
            for prediction in predictive_situations
        )

        explanations = tuple(
            self.explainability_engine.explain(
                context
            )
            for context in decision_contexts
        )

        result = PredictiveIntelligenceResult(
            predictive_signals=predictive_signals,
            risk_forecasts=risk_forecasts,
            recurrence_predictions=(
                recurrence_predictions
            ),
            workload_forecasts=(
                workload_forecasts
            ),
            predictive_situations=(
                predictive_situations
            ),
            decision_contexts=decision_contexts,
            explanations=explanations,
        )

        self._last_result = result
        return result

    def clear_last_result(self) -> None:
        self._last_result = None
