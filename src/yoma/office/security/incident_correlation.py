from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .incident_events import (
    IncidentSeverity,
    SecurityEvent,
)


@dataclass(frozen=True)
class CorrelationResult:
    correlated: bool
    event_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    reason: str
    score: int


class SecurityEventCorrelator:
    def correlate(self, events: Iterable[SecurityEvent]) -> CorrelationResult:
        items = tuple(events)

        if not items:
            return CorrelationResult(
                correlated=False,
                event_ids=(),
                source_ids=(),
                reason="no events",
                score=0,
            )

        source_ids = tuple(sorted({e.source_id for e in items}))
        event_ids = tuple(e.event_id for e in items)

        score = 0
        types = {e.event_type.value for e in items}

        if len(items) >= 2:
            score += 20

        if len(source_ids) == 1:
            score += 20

        if "authentication_failure" in types:
            score += 15

        if "privilege_attempt" in types:
            score += 30

        if "configuration_tamper" in types:
            score += 30

        if "integrity_failure" in types:
            score += 30

        if "suspicious_file" in types or "filesystem_anomaly" in types:
            score += 15

        score = min(score, 100)

        return CorrelationResult(
            correlated=score >= 30,
            event_ids=event_ids,
            source_ids=source_ids,
            reason="cross-layer security signals correlated",
            score=score,
        )
