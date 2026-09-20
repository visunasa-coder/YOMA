from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .incident_events import SecurityEvent


@dataclass(frozen=True)
class IncidentTimeline:
    events: tuple[SecurityEvent, ...]
    evidence_count: int
    chronologically_ordered: bool

    def as_dict(self) -> dict:
        return {
            "events": [e.as_dict() for e in self.events],
            "evidence_count": self.evidence_count,
            "chronologically_ordered": self.chronologically_ordered,
        }


class IncidentEvidenceTimeline:
    def build(self, events: Iterable[SecurityEvent]) -> IncidentTimeline:
        ordered = tuple(sorted(events, key=lambda e: e.timestamp))

        return IncidentTimeline(
            events=ordered,
            evidence_count=len(ordered),
            chronologically_ordered=True,
        )
