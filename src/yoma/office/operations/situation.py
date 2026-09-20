from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from yoma.office.operations import OperationalSignal


_SEVERITY_RANK = {
    "info": 0,
    "warning": 1,
    "high": 2,
    "critical": 3,
}


@dataclass(frozen=True)
class OperationalSituation:
    """
    Correlated operational condition derived from one or more
    OperationalSignal objects.

    Situations are descriptive and advisory. They do not make
    employment, disciplinary, financial, or security decisions.
    """

    situation_id: str
    situation_type: str
    detected_at: datetime
    organization_id: str | None = None
    user_id: str | None = None
    system_id: str | None = None
    severity: str = "info"
    score: float = 0.0
    signal_ids: tuple[str, ...] = ()
    evidence_event_ids: tuple[str, ...] = ()
    data: dict = None

    def __post_init__(self) -> None:
        if self.data is None:
            object.__setattr__(self, "data", {})


class OperationalSituationCorrelator:
    """
    Deterministically correlates related OperationalSignal objects.

    Signals are correlated only when they share the same explicit
    entity scope and belong to the supported workload-pressure
    signal family.
    """

    _WORKLOAD_SIGNAL_TYPES = frozenset(
        {
            "workload.high",
            "meeting_load.high",
            "deadline_pressure.high",
        }
    )

    def correlate(
        self,
        signals: list[OperationalSignal],
    ) -> list[OperationalSituation]:
        if not signals:
            return []

        groups: dict[tuple, list[OperationalSignal]] = {}

        ordered_signals = sorted(
            signals,
            key=lambda signal: (
                signal.signal_type,
                signal.organization_id or "",
                signal.user_id or "",
                signal.system_id or "",
                signal.signal_id,
            ),
        )

        for signal in ordered_signals:
            key = self._correlation_key(signal)

            if key is None:
                key = (
                    "singleton",
                    signal.organization_id,
                    signal.user_id,
                    signal.system_id,
                    signal.signal_id,
                )

            groups.setdefault(key, []).append(signal)

        situations = [
            self._build_situation(group)
            for group in groups.values()
        ]

        return sorted(
            situations,
            key=lambda situation: (
                situation.situation_type,
                situation.organization_id or "",
                situation.user_id or "",
                situation.system_id or "",
                situation.signal_ids,
            ),
        )

    def _correlation_key(
        self,
        signal: OperationalSignal,
    ) -> tuple | None:
        if signal.signal_type not in self._WORKLOAD_SIGNAL_TYPES:
            return None

        return (
            "workload_pressure",
            signal.organization_id,
            signal.user_id,
            signal.system_id,
        )

    @staticmethod
    def _build_situation(
        signals: list[OperationalSignal],
    ) -> OperationalSituation:
        ordered = sorted(
            signals,
            key=lambda signal: signal.signal_id,
        )

        first = ordered[0]

        severity = max(
            (signal.severity for signal in ordered),
            key=lambda value: _SEVERITY_RANK.get(value, -1),
        )

        score = sum(signal.score for signal in ordered) / len(ordered)

        evidence: list[str] = []

        for signal in ordered:
            for event_id in signal.evidence_event_ids:
                if event_id not in evidence:
                    evidence.append(event_id)

        signal_ids = tuple(signal.signal_id for signal in ordered)

        situation_id = (
            f"SIT-{first.organization_id or 'GLOBAL'}-"
            f"{first.user_id or first.system_id or 'GLOBAL'}-"
            f"{'-'.join(signal_ids)}"
        )

        return OperationalSituation(
            situation_id=situation_id,
            situation_type="workload_pressure",
            detected_at=max(
                signal.detected_at
                for signal in ordered
            ),
            organization_id=first.organization_id,
            user_id=first.user_id,
            system_id=first.system_id,
            severity=severity,
            score=score,
            signal_ids=signal_ids,
            evidence_event_ids=tuple(evidence),
            data={
                "signal_count": len(ordered),
                "signal_types": tuple(
                    signal.signal_type
                    for signal in ordered
                ),
            },
        )
