"""M35.5 — Cross-System Correlation.

Read-only correlation of operational activity across systems.
No execution, authorization, approval, policy mutation, or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Mapping

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


@dataclass(frozen=True)
class CrossSystemCorrelation:
    """A deterministic temporal relationship between two systems."""

    source_system: str
    related_system: str
    source_record_count: int
    related_record_count: int
    related_pair_count: int
    correlation_rate: float


@dataclass(frozen=True)
class CrossSystemCorrelationResult:
    """Read-only cross-system correlation result."""

    total_records: int
    correlation_window_seconds: float
    correlations: tuple[CrossSystemCorrelation, ...]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] | None = None


class CrossSystemCorrelationRuntime:
    """Detect temporal relationships between operational systems."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        window_seconds: float = 300.0,
        metadata: Mapping[str, object] | None = None,
    ) -> CrossSystemCorrelationResult:
        if window_seconds < 0:
            raise ValueError("window_seconds must not be negative")

        records = tuple(records)

        for record in records:
            if not isinstance(record, AnalyticsRecord):
                raise TypeError("records must contain AnalyticsRecord instances")
            if record.observed_at.tzinfo is None:
                raise ValueError("record timestamps must be timezone-aware")

        ordered = tuple(
            sorted(
                records,
                key=lambda record: (
                    record.observed_at,
                    record.record_id,
                    record.source_system,
                ),
            )
        )

        systems = tuple(sorted({record.source_system for record in ordered}))
        correlations: list[CrossSystemCorrelation] = []

        window = timedelta(seconds=window_seconds)

        for index, source_system in enumerate(systems):
            source_records = tuple(
                record
                for record in ordered
                if record.source_system == source_system
            )

            for related_system in systems[index + 1:]:
                related_records = tuple(
                    record
                    for record in ordered
                    if record.source_system == related_system
                )

                pair_count = sum(
                    1
                    for source_record in source_records
                    if any(
                        abs(
                            related_record.observed_at
                            - source_record.observed_at
                        )
                        <= window
                        for related_record in related_records
                    )
                )

                if pair_count:
                    rate = pair_count / len(source_records)
                    correlations.append(
                        CrossSystemCorrelation(
                            source_system=source_system,
                            related_system=related_system,
                            source_record_count=len(source_records),
                            related_record_count=len(related_records),
                            related_pair_count=pair_count,
                            correlation_rate=rate,
                        )
                    )

        correlations.sort(
            key=lambda item: (
                -item.correlation_rate,
                item.source_system,
                item.related_system,
            )
        )

        return CrossSystemCorrelationResult(
            total_records=len(ordered),
            correlation_window_seconds=window_seconds,
            correlations=tuple(correlations),
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.5",
                "analytics_only": True,
                "composition_only": True,
                **dict(metadata or {}),
            },
        )


__all__ = [
    "CrossSystemCorrelation",
    "CrossSystemCorrelationResult",
    "CrossSystemCorrelationRuntime",
]
