"""M35.2 — Operational Metrics.

Deterministic, read-only metrics over M35.1 analytics records.
No execution, authorization, approval, policy mutation, or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Mapping

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


@dataclass(frozen=True)
class OperationalMetricsResult:
    """Read-only operational metrics."""

    total_records: int
    active_systems: int
    active_record_types: int
    average_records_per_system: float
    first_observed_at: object | None
    last_observed_at: object | None
    observation_span_seconds: float
    records_per_hour: float
    records_by_system: Mapping[str, int]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] | None = None


class OperationalMetricsRuntime:
    """Calculate deterministic operational metrics without side effects."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> OperationalMetricsResult:
        records = tuple(records)

        for record in records:
            if not isinstance(record, AnalyticsRecord):
                raise TypeError("records must contain AnalyticsRecord instances")
            if record.observed_at.tzinfo is None:
                raise ValueError("record timestamps must be timezone-aware")

        if not records:
            return OperationalMetricsResult(
                total_records=0,
                active_systems=0,
                active_record_types=0,
                average_records_per_system=0.0,
                first_observed_at=None,
                last_observed_at=None,
                observation_span_seconds=0.0,
                records_per_hour=0.0,
                records_by_system={},
                read_only=True,
                executable=False,
                metadata={
                    "source": "M35.2",
                    "analytics_only": True,
                    **dict(metadata or {}),
                },
            )

        ordered = tuple(sorted(records, key=lambda record: record.observed_at))
        systems = {record.source_system for record in ordered}
        record_types = {record.record_type for record in ordered}

        first = ordered[0].observed_at
        last = ordered[-1].observed_at
        span = last - first
        span_seconds = span.total_seconds()

        # For a zero-length observation window, avoid division by zero.
        if span_seconds > 0:
            records_per_hour = len(ordered) / (span_seconds / 3600)
        else:
            records_per_hour = 0.0

        by_system: dict[str, int] = {}
        for record in ordered:
            by_system[record.source_system] = (
                by_system.get(record.source_system, 0) + 1
            )

        return OperationalMetricsResult(
            total_records=len(ordered),
            active_systems=len(systems),
            active_record_types=len(record_types),
            average_records_per_system=len(ordered) / len(systems),
            first_observed_at=first,
            last_observed_at=last,
            observation_span_seconds=span_seconds,
            records_per_hour=records_per_hour,
            records_by_system=dict(sorted(by_system.items())),
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.2",
                "analytics_only": True,
                **dict(metadata or {}),
            },
        )


__all__ = [
    "OperationalMetricsResult",
    "OperationalMetricsRuntime",
]
