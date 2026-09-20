"""M35.1 — Cross-System Analytics Foundation.

Read-only aggregation of existing operational records.

This module intentionally has no execution, approval, policy mutation,
scheduling, retry, or repair authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class AnalyticsRecord:
    """Normalized read-only representation of an operational record."""

    record_id: str
    source_system: str
    record_type: str
    observed_at: datetime
    organization_id: str | None = None
    user_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossSystemAnalyticsResult:
    """Deterministic analytics result produced by M35.1."""

    total_records: int
    systems: tuple[str, ...]
    record_types: tuple[str, ...]
    records_by_system: Mapping[str, int]
    records_by_type: Mapping[str, int]
    records_by_system_and_type: Mapping[str, int]
    window_start: datetime | None
    window_end: datetime | None
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


class CrossSystemAnalyticsRuntime:
    """M35.1 read-only cross-system analytics runtime."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CrossSystemAnalyticsResult:
        """Aggregate existing operational records without side effects."""

        if window_start is not None and window_end is not None:
            if window_start.tzinfo is None or window_end.tzinfo is None:
                raise ValueError("analytics window timestamps must be timezone-aware")
            if window_start > window_end:
                raise ValueError("window_start must not be after window_end")
        elif window_start is not None and window_start.tzinfo is None:
            raise ValueError("window_start must be timezone-aware")
        elif window_end is not None and window_end.tzinfo is None:
            raise ValueError("window_end must be timezone-aware")

        normalized = tuple(records)

        for record in normalized:
            if not isinstance(record, AnalyticsRecord):
                raise TypeError("records must contain AnalyticsRecord instances")
            if record.observed_at.tzinfo is None:
                raise ValueError("record timestamps must be timezone-aware")

        filtered = tuple(
            record
            for record in normalized
            if (window_start is None or record.observed_at >= window_start)
            and (window_end is None or record.observed_at <= window_end)
        )

        systems = tuple(sorted({record.source_system for record in filtered}))
        record_types = tuple(sorted({record.record_type for record in filtered}))

        by_system = Counter(record.source_system for record in filtered)
        by_type = Counter(record.record_type for record in filtered)
        by_system_type = Counter(
            f"{record.source_system}:{record.record_type}"
            for record in filtered
        )

        return CrossSystemAnalyticsResult(
            total_records=len(filtered),
            systems=systems,
            record_types=record_types,
            records_by_system=dict(sorted(by_system.items())),
            records_by_type=dict(sorted(by_type.items())),
            records_by_system_and_type=dict(sorted(by_system_type.items())),
            window_start=window_start,
            window_end=window_end,
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.1",
                "analytics_only": True,
                "composition_only": True,
                **dict(metadata or {}),
            },
        )


__all__ = [
    "AnalyticsRecord",
    "CrossSystemAnalyticsResult",
    "CrossSystemAnalyticsRuntime",
]
