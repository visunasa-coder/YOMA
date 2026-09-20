from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yoma.office.operational_event_persistence import OperationalEventPersistence
from yoma.office.operational_signal_persistence import OperationalSignalPersistence
from yoma.office.operational_situation_persistence import OperationalSituationPersistence
from yoma.office.operational_timeline import OperationalTimeline, OperationalTimelineEntry
from yoma.office.historical_pattern import HistoricalPattern, HistoricalPatternDetector
from yoma.office.baseline_trend import BaselineTrend, BaselineTrendAnalyzer
from yoma.office.historical_decision_context import (
    HistoricalDecisionContext,
    HistoricalDecisionContextBuilder,
)
from yoma.office.operations.situation import OperationalSituation


@dataclass(frozen=True)
class HistoricalIntelligenceResult:
    timeline: tuple[OperationalTimelineEntry, ...]
    patterns: tuple[HistoricalPattern, ...]
    trends: tuple[BaselineTrend, ...]
    decision_contexts: tuple[HistoricalDecisionContext, ...]


class HistoricalIntelligenceRuntime:
    """
    End-to-end historical intelligence composition layer.

    Existing persistence stores remain the source of truth.
    This runtime adds no database tables and performs no autonomous action.
    """

    def __init__(
        self,
        event_persistence: OperationalEventPersistence,
        signal_persistence: OperationalSignalPersistence,
        situation_persistence: OperationalSituationPersistence,
        *,
        window_days: float = 7.0,
        stable_threshold: float = 0.10,
    ) -> None:
        if not isinstance(
            event_persistence,
            OperationalEventPersistence,
        ):
            raise TypeError(
                "event_persistence must be OperationalEventPersistence"
            )

        if not isinstance(
            signal_persistence,
            OperationalSignalPersistence,
        ):
            raise TypeError(
                "signal_persistence must be OperationalSignalPersistence"
            )

        if not isinstance(
            situation_persistence,
            OperationalSituationPersistence,
        ):
            raise TypeError(
                "situation_persistence must be OperationalSituationPersistence"
            )

        self.event_persistence = event_persistence
        self.signal_persistence = signal_persistence
        self.situation_persistence = situation_persistence

        self.timeline = OperationalTimeline(
            event_persistence=event_persistence,
            signal_persistence=signal_persistence,
            situation_persistence=situation_persistence,
        )

        self.pattern_detector = HistoricalPatternDetector(
            situation_persistence
        )

        self.trend_analyzer = BaselineTrendAnalyzer(
            situation_persistence,
            window_days=window_days,
            stable_threshold=stable_threshold,
        )

    def analyze(self) -> HistoricalIntelligenceResult:
        situations = self.situation_persistence.load_all()

        patterns = self.pattern_detector.detect(situations)
        trends = self.trend_analyzer.analyze(situations)

        builder = HistoricalDecisionContextBuilder(
            patterns,
            trends,
        )

        contexts = [
            builder.build(situation)
            for situation in situations
        ]

        return HistoricalIntelligenceResult(
            timeline=tuple(self.timeline.load_all()),
            patterns=tuple(patterns),
            trends=tuple(trends),
            decision_contexts=tuple(contexts),
        )

    def context_for(
        self,
        situation: OperationalSituation,
    ) -> HistoricalDecisionContext:
        if not isinstance(
            situation,
            OperationalSituation,
        ):
            raise TypeError(
                "situation must be OperationalSituation"
            )

        patterns = self.pattern_detector.detect()
        trends = self.trend_analyzer.analyze()

        return HistoricalDecisionContextBuilder(
            patterns,
            trends,
        ).build(situation)

    def situations(self) -> list[OperationalSituation]:
        return self.situation_persistence.load_all()

    def clear(self) -> None:
        self.situation_persistence.clear()
        self.signal_persistence.clear()
        self.event_persistence.clear()


__all__ = [
    "HistoricalIntelligenceResult",
    "HistoricalIntelligenceRuntime",
]
