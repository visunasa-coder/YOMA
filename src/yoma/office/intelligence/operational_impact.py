"""M35.6 — Operational Impact / Time-Saved Estimation.

Read-only estimation of manual effort and potential time savings from
observed operational records.

This module does not execute actions, authorize actions, mutate policy,
or claim that estimated savings actually occurred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


@dataclass(frozen=True)
class OperationalImpactEstimate:
    """Estimated impact for one operational system."""

    source_system: str
    record_count: int
    estimated_manual_minutes: float
    estimated_time_saved_minutes: float
    estimated_time_saved_hours: float
    savings_rate: float


@dataclass(frozen=True)
class OperationalImpactResult:
    """Read-only aggregate operational impact estimate."""

    total_records: int
    estimated_manual_minutes: float
    estimated_time_saved_minutes: float
    estimated_time_saved_hours: float
    estimated_savings_rate: float
    system_impacts: tuple[OperationalImpactEstimate, ...]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] | None = None


class OperationalImpactRuntime:
    """Estimate operational impact from observed records."""

    def analyze(
        self,
        records: Iterable[AnalyticsRecord],
        *,
        manual_minutes_per_record: float = 5.0,
        automation_savings_rate: float = 0.50,
        metadata: Mapping[str, object] | None = None,
    ) -> OperationalImpactResult:
        if manual_minutes_per_record < 0:
            raise ValueError(
                "manual_minutes_per_record must not be negative"
            )

        if not 0 <= automation_savings_rate <= 1:
            raise ValueError(
                "automation_savings_rate must be between 0 and 1"
            )

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

        system_impacts = tuple(
            OperationalImpactEstimate(
                source_system=system,
                record_count=count,
                estimated_manual_minutes=count * manual_minutes_per_record,
                estimated_time_saved_minutes=(
                    count
                    * manual_minutes_per_record
                    * automation_savings_rate
                ),
                estimated_time_saved_hours=(
                    count
                    * manual_minutes_per_record
                    * automation_savings_rate
                    / 60.0
                ),
                savings_rate=automation_savings_rate,
            )
            for system, count in sorted(by_system.items())
        )

        total_manual = (
            len(records) * manual_minutes_per_record
        )
        total_saved = total_manual * automation_savings_rate

        return OperationalImpactResult(
            total_records=len(records),
            estimated_manual_minutes=total_manual,
            estimated_time_saved_minutes=total_saved,
            estimated_time_saved_hours=total_saved / 60.0,
            estimated_savings_rate=automation_savings_rate,
            system_impacts=system_impacts,
            read_only=True,
            executable=False,
            metadata={
                "source": "M35.6",
                "analytics_only": True,
                "estimate_only": True,
                "observed_savings_not_claimed": True,
                "manual_minutes_per_record": manual_minutes_per_record,
                **dict(metadata or {}),
            },
        )


__all__ = [
    "OperationalImpactEstimate",
    "OperationalImpactResult",
    "OperationalImpactRuntime",
]
