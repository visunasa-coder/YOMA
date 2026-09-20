"""M35.3 — Operational Trend Analysis.

Read-only deterministic trend analysis for existing operational records.
No execution, authorization, approval, policy mutation, or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


@dataclass(frozen=True)
class TrendPoint:
    """Aggregated metric for one observation period."""

    period: str
    value: float


@dataclass(frozen=True)
class TrendAnalysis:
    """Deterministic comparison between consecutive periods."""

    metric: str
    points: tuple[TrendPoint, ...]
    direction: str
    absolute_change: float
    percentage_change: float | None


@dataclass(frozen=True)
class OperationalTrendResult:
    """Read-only operational trend result."""

    trends: tuple[TrendAnalysis, ...]
    period_count: int
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] | None = None


class OperationalTrendRuntime:
    """Calculate deterministic trends from existing operational records."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        period: str = "day",
        metadata: Mapping[str, object] | None = None,
    ) -> OperationalTrendResult:
        if period not in {"hour", "day", "week"}:
            raise ValueError("period must be one of: hour, day, week")

        records = tuple(records)

        for record in records:
            if not isinstance(record, AnalyticsRecord):
                raise TypeError("records must contain AnalyticsRecord instances")
            if record.observed_at.tzinfo is None:
                raise ValueError("record timestamps must be timezone-aware")

        buckets: dict[str, int] = {}

        for record in records:
            key = self._period_key(record.observed_at, period)
            buckets[key] = buckets.get(key, 0) + 1

        points = tuple(
            TrendPoint(period=key, value=float(buckets[key]))
            for key in sorted(buckets)
        )

        trend = self._build_trend("record_count", points)

        return OperationalTrendResult(
            trends=(trend,) if trend is not None else (),
            period_count=len(points),
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.3",
                "analytics_only": True,
                "composition_only": True,
                **dict(metadata or {}),
            },
        )

    @staticmethod
    def _period_key(timestamp: datetime, period: str) -> str:
        if period == "hour":
            return timestamp.strftime("%Y-%m-%dT%H:00:00%z")

        if period == "day":
            return timestamp.strftime("%Y-%m-%d")

        iso = timestamp.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    @staticmethod
    def _build_trend(
        metric: str,
        points: tuple[TrendPoint, ...],
    ) -> TrendAnalysis | None:
        if not points:
            return None

        if len(points) == 1:
            return TrendAnalysis(
                metric=metric,
                points=points,
                direction="stable",
                absolute_change=0.0,
                percentage_change=None,
            )

        previous = points[-2].value
        current = points[-1].value
        change = current - previous

        if change > 0:
            direction = "increasing"
        elif change < 0:
            direction = "decreasing"
        else:
            direction = "stable"

        percentage = None
        if previous != 0:
            percentage = (change / previous) * 100.0

        return TrendAnalysis(
            metric=metric,
            points=points,
            direction=direction,
            absolute_change=change,
            percentage_change=percentage,
        )


__all__ = [
    "TrendPoint",
    "TrendAnalysis",
    "OperationalTrendResult",
    "OperationalTrendRuntime",
]
