from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from yoma.office.operations.situation import OperationalSituation
from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)


@dataclass(frozen=True)
class HistoricalPattern:
    pattern_id: str
    pattern_type: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    occurrence_count: int
    first_occurred_at: datetime
    last_occurred_at: datetime
    recurrence_intervals_seconds: tuple[float, ...]
    signal_combinations: tuple[tuple[str, ...], ...]
    situation_ids: tuple[str, ...]

    @property
    def recurring(self) -> bool:
        return self.occurrence_count >= 2

    @property
    def average_recurrence_interval_seconds(self) -> Optional[float]:
        if not self.recurrence_intervals_seconds:
            return None
        return sum(self.recurrence_intervals_seconds) / len(
            self.recurrence_intervals_seconds
        )


class HistoricalPatternDetector:
    """
    Deterministic historical pattern detector.

    Responsibilities:
    - detect repeated situation types
    - detect recurrence by organization/user/system
    - calculate recurrence intervals
    - preserve repeated signal combinations
    - produce deterministic pattern IDs

    This layer is advisory only. It does not execute actions and does not
    modify persistence models or database schema.
    """

    def __init__(
        self,
        persistence: OperationalSituationPersistence,
    ) -> None:
        if not isinstance(
            persistence,
            OperationalSituationPersistence,
        ):
            raise TypeError(
                "persistence must be OperationalSituationPersistence"
            )

        self.persistence = persistence

    def detect(
        self,
        situations: Optional[Iterable[OperationalSituation]] = None,
    ) -> list[HistoricalPattern]:
        if situations is None:
            situations = self.persistence.load_all()

        items = list(situations)

        for situation in items:
            if not isinstance(situation, OperationalSituation):
                raise TypeError(
                    "situations must contain OperationalSituation objects"
                )

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

        patterns: list[HistoricalPattern] = []

        for key, group in sorted(
            groups.items(),
            key=lambda item: self._group_sort_key(item[0]),
        ):
            if len(group) < 2:
                continue

            situation_type, organization_id, user_id, system_id = key

            ordered = sorted(
                group,
                key=lambda item: (
                    item.detected_at,
                    item.situation_id,
                ),
            )

            intervals: list[float] = []

            for previous, current in zip(
                ordered,
                ordered[1:],
            ):
                interval = (
                    current.detected_at - previous.detected_at
                ).total_seconds()
                intervals.append(interval)

            combinations = tuple(
                sorted(
                    {
                        tuple(sorted(signal_id for signal_id in situation.signal_ids))
                        for situation in ordered
                    }
                )
            )

            situation_ids = tuple(
                situation.situation_id
                for situation in ordered
            )

            pattern_id = self._pattern_id(
                situation_type=situation_type,
                organization_id=organization_id,
                user_id=user_id,
                system_id=system_id,
                situation_ids=situation_ids,
            )

            patterns.append(
                HistoricalPattern(
                    pattern_id=pattern_id,
                    pattern_type="historical_recurrence",
                    situation_type=situation_type,
                    organization_id=organization_id,
                    user_id=user_id,
                    system_id=system_id,
                    occurrence_count=len(ordered),
                    first_occurred_at=ordered[0].detected_at,
                    last_occurred_at=ordered[-1].detected_at,
                    recurrence_intervals_seconds=tuple(intervals),
                    signal_combinations=combinations,
                    situation_ids=situation_ids,
                )
            )

        return patterns

    def detect_by_type(
        self,
        situation_type: str,
    ) -> list[HistoricalPattern]:
        if not isinstance(situation_type, str) or not situation_type:
            raise ValueError("situation_type must be a non-empty string")

        return [
            pattern
            for pattern in self.detect()
            if pattern.situation_type == situation_type
        ]

    def detect_by_organization(
        self,
        organization_id: str,
    ) -> list[HistoricalPattern]:
        if not isinstance(organization_id, str) or not organization_id:
            raise ValueError("organization_id must be a non-empty string")

        return [
            pattern
            for pattern in self.detect()
            if pattern.organization_id == organization_id
        ]

    def detect_by_user(
        self,
        user_id: str,
    ) -> list[HistoricalPattern]:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id must be a non-empty string")

        return [
            pattern
            for pattern in self.detect()
            if pattern.user_id == user_id
        ]

    def detect_by_system(
        self,
        system_id: str,
    ) -> list[HistoricalPattern]:
        if not isinstance(system_id, str) or not system_id:
            raise ValueError("system_id must be a non-empty string")

        return [
            pattern
            for pattern in self.detect()
            if pattern.system_id == system_id
        ]

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

    @staticmethod
    def _pattern_id(
        *,
        situation_type: str,
        organization_id: Optional[str],
        user_id: Optional[str],
        system_id: Optional[str],
        situation_ids: tuple[str, ...],
    ) -> str:
        scope = "-".join(
            (
                organization_id or "GLOBAL",
                user_id or "GLOBAL",
                system_id or "GLOBAL",
            )
        )

        return (
            "HPAT-"
            f"{situation_type}-"
            f"{scope}-"
            f"{'-'.join(situation_ids)}"
        )


__all__ = [
    "HistoricalPattern",
    "HistoricalPatternDetector",
]
