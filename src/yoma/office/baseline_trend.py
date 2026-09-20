from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

from yoma.office.operations.situation import OperationalSituation
from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)


@dataclass(frozen=True)
class BaselineTrend:
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]

    total_occurrences: int
    historical_days: float
    baseline_daily_frequency: float

    recent_occurrences: int
    previous_occurrences: int
    window_days: float

    recent_daily_frequency: float
    previous_daily_frequency: float

    frequency_change: float
    deviation_from_baseline: float
    trend_ratio: float
    trend_direction: str

    first_occurred_at: datetime
    last_occurred_at: datetime

    average_recurrence_interval_seconds: Optional[float]

    situation_ids: tuple[str, ...]

    @property
    def above_baseline(self) -> bool:
        return self.deviation_from_baseline > 0.0

    @property
    def below_baseline(self) -> bool:
        return self.deviation_from_baseline < 0.0


class BaselineTrendAnalyzer:
    """
    Deterministic baseline and trend analysis over historical situations.

    Recent frequency is compared with an equally sized immediately
    preceding window.

    No persistence/schema mutation.
    No autonomous actions.
    """

    def __init__(
        self,
        persistence: OperationalSituationPersistence,
        *,
        window_days: float = 7.0,
        stable_threshold: float = 0.10,
    ) -> None:
        if not isinstance(
            persistence,
            OperationalSituationPersistence,
        ):
            raise TypeError(
                "persistence must be OperationalSituationPersistence"
            )

        if window_days <= 0:
            raise ValueError("window_days must be greater than zero")

        if stable_threshold < 0:
            raise ValueError(
                "stable_threshold must be non-negative"
            )

        self.persistence = persistence
        self.window_days = float(window_days)
        self.stable_threshold = float(stable_threshold)

    def analyze(
        self,
        situations: Optional[Iterable[OperationalSituation]] = None,
    ) -> list[BaselineTrend]:
        if situations is None:
            situations = self.persistence.load_all()

        items = list(situations)

        for situation in items:
            if not isinstance(situation, OperationalSituation):
                raise TypeError(
                    "situations must contain OperationalSituation objects"
                )

        if not items:
            return []

        items.sort(
            key=lambda item: (
                item.detected_at,
                item.situation_id,
            )
        )

        groups: dict[
            tuple[
                str,
                Optional[str],
                Optional[str],
                Optional[str],
            ],
            list[OperationalSituation],
        ] = {}

        for situation in items:
            key = (
                situation.situation_type,
                situation.organization_id,
                situation.user_id,
                situation.system_id,
            )

            groups.setdefault(key, []).append(situation)

        results: list[BaselineTrend] = []

        for key, group in sorted(
            groups.items(),
            key=lambda item: self._group_sort_key(item[0]),
        ):
            if not group:
                continue

            results.append(
                self._analyze_group(
                    key,
                    group,
                )
            )

        return results

    def analyze_by_type(
        self,
        situation_type: str,
    ) -> list[BaselineTrend]:
        if not isinstance(situation_type, str) or not situation_type:
            raise ValueError(
                "situation_type must be a non-empty string"
            )

        return [
            result
            for result in self.analyze()
            if result.situation_type == situation_type
        ]

    def analyze_by_organization(
        self,
        organization_id: str,
    ) -> list[BaselineTrend]:
        if not isinstance(organization_id, str) or not organization_id:
            raise ValueError(
                "organization_id must be a non-empty string"
            )

        return [
            result
            for result in self.analyze()
            if result.organization_id == organization_id
        ]

    def analyze_by_user(
        self,
        user_id: str,
    ) -> list[BaselineTrend]:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError(
                "user_id must be a non-empty string"
            )

        return [
            result
            for result in self.analyze()
            if result.user_id == user_id
        ]

    def analyze_by_system(
        self,
        system_id: str,
    ) -> list[BaselineTrend]:
        if not isinstance(system_id, str) or not system_id:
            raise ValueError(
                "system_id must be a non-empty string"
            )

        return [
            result
            for result in self.analyze()
            if result.system_id == system_id
        ]

    def _analyze_group(
        self,
        key: tuple[
            str,
            Optional[str],
            Optional[str],
            Optional[str],
        ],
        group: list[OperationalSituation],
    ) -> BaselineTrend:
        situation_type, organization_id, user_id, system_id = key

        ordered = sorted(
            group,
            key=lambda item: (
                item.detected_at,
                item.situation_id,
            ),
        )

        first = ordered[0].detected_at
        last = ordered[-1].detected_at

        observed_seconds = max(
            (last - first).total_seconds(),
            0.0,
        )

        historical_days = max(
            observed_seconds / 86400.0,
            self.window_days,
        )

        total_occurrences = len(ordered)

        baseline_daily_frequency = (
            total_occurrences / historical_days
        )

        recent_window = timedelta(
            days=self.window_days
        )

        recent_start = last - recent_window
        previous_start = recent_start - recent_window

        recent_items = [
            situation
            for situation in ordered
            if recent_start <= situation.detected_at <= last
        ]

        previous_items = [
            situation
            for situation in ordered
            if previous_start <= situation.detected_at < recent_start
        ]

        recent_occurrences = len(recent_items)
        previous_occurrences = len(previous_items)

        window_days = self.window_days

        recent_daily_frequency = (
            recent_occurrences / window_days
        )

        previous_daily_frequency = (
            previous_occurrences / window_days
        )

        frequency_change = (
            recent_daily_frequency
            - previous_daily_frequency
        )

        if previous_daily_frequency > 0:
            trend_ratio = (
                recent_daily_frequency
                / previous_daily_frequency
            )
        elif recent_daily_frequency > 0:
            trend_ratio = float("inf")
        else:
            trend_ratio = 1.0

        if baseline_daily_frequency > 0:
            deviation_from_baseline = (
                recent_daily_frequency
                - baseline_daily_frequency
            ) / baseline_daily_frequency
        else:
            deviation_from_baseline = 0.0

        if previous_daily_frequency == 0:
            if recent_daily_frequency == 0:
                trend_direction = "stable"
            else:
                trend_direction = "increasing"
        else:
            relative_change = (
                frequency_change
                / previous_daily_frequency
            )

            if relative_change > self.stable_threshold:
                trend_direction = "increasing"
            elif relative_change < -self.stable_threshold:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"

        intervals: list[float] = []

        for previous, current in zip(
            ordered,
            ordered[1:],
        ):
            intervals.append(
                (
                    current.detected_at
                    - previous.detected_at
                ).total_seconds()
            )

        average_interval = (
            sum(intervals) / len(intervals)
            if intervals
            else None
        )

        return BaselineTrend(
            situation_type=situation_type,
            organization_id=organization_id,
            user_id=user_id,
            system_id=system_id,
            total_occurrences=total_occurrences,
            historical_days=historical_days,
            baseline_daily_frequency=baseline_daily_frequency,
            recent_occurrences=recent_occurrences,
            previous_occurrences=previous_occurrences,
            window_days=window_days,
            recent_daily_frequency=recent_daily_frequency,
            previous_daily_frequency=previous_daily_frequency,
            frequency_change=frequency_change,
            deviation_from_baseline=deviation_from_baseline,
            trend_ratio=trend_ratio,
            trend_direction=trend_direction,
            first_occurred_at=first,
            last_occurred_at=last,
            average_recurrence_interval_seconds=average_interval,
            situation_ids=tuple(
                situation.situation_id
                for situation in ordered
            ),
        )

    @staticmethod
    def _group_sort_key(
        key: tuple[
            str,
            Optional[str],
            Optional[str],
            Optional[str],
        ],
    ) -> tuple[str, str, str, str]:
        situation_type, organization_id, user_id, system_id = key

        return (
            situation_type,
            organization_id or "",
            user_id or "",
            system_id or "",
        )


__all__ = [
    "BaselineTrend",
    "BaselineTrendAnalyzer",
]
