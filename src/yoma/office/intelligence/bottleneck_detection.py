"""M35.4 — Cross-System Bottleneck Detection.

Read-only detection of operational concentration/bottleneck candidates.
No execution, authorization, approval, policy mutation, or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


@dataclass(frozen=True)
class BottleneckCandidate:
    """A system whose observed load exceeds the configured threshold."""

    source_system: str
    record_count: int
    share_of_total: float
    excess_over_average: float


@dataclass(frozen=True)
class BottleneckDetectionResult:
    """Deterministic read-only bottleneck analysis."""

    total_records: int
    system_count: int
    average_records_per_system: float
    threshold_multiplier: float
    candidates: tuple[BottleneckCandidate, ...]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] | None = None


class BottleneckDetectionRuntime:
    """Detect operational concentration without taking corrective action."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        threshold_multiplier: float = 1.5,
        metadata: Mapping[str, object] | None = None,
    ) -> BottleneckDetectionResult:
        if threshold_multiplier <= 0:
            raise ValueError("threshold_multiplier must be greater than zero")

        records = tuple(records)

        for record in records:
            if not isinstance(record, AnalyticsRecord):
                raise TypeError("records must contain AnalyticsRecord instances")
            if record.observed_at.tzinfo is None:
                raise ValueError("record timestamps must be timezone-aware")

        by_system: dict[str, int] = {}

        for record in records:
            by_system[record.source_system] = (
                by_system.get(record.source_system, 0) + 1
            )

        total = len(records)
        system_count = len(by_system)

        if system_count == 0:
            average = 0.0
        else:
            average = total / system_count

        threshold = average * threshold_multiplier

        candidates = tuple(
            BottleneckCandidate(
                source_system=system,
                record_count=count,
                share_of_total=count / total if total else 0.0,
                excess_over_average=count - average,
            )
            for system, count in sorted(
                by_system.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if count >= threshold
        )

        return BottleneckDetectionResult(
            total_records=total,
            system_count=system_count,
            average_records_per_system=average,
            threshold_multiplier=threshold_multiplier,
            candidates=candidates,
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.4",
                "analytics_only": True,
                "composition_only": True,
                **dict(metadata or {}),
            },
        )


__all__ = [
    "BottleneckCandidate",
    "BottleneckDetectionResult",
    "BottleneckDetectionRuntime",
]
