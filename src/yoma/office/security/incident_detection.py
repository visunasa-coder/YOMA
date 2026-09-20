from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .incident_events import (
    IncidentSeverity,
    SecurityEvent,
    SecurityEventType,
)


@dataclass(frozen=True)
class IncidentDetection:
    detected: bool
    severity: IncidentSeverity
    confidence: float
    reasons: tuple[str, ...]
    event_ids: tuple[str, ...]


class IncidentDetector:
    def detect(self, events: Iterable[SecurityEvent]) -> IncidentDetection:
        items = tuple(events)

        if not items:
            return IncidentDetection(
                False, IncidentSeverity.INFO, 0.0, (), ()
            )

        reasons: list[str] = []
        severity = IncidentSeverity.INFO

        types = {e.event_type for e in items}

        if SecurityEventType.CONFIGURATION_TAMPER in types:
            severity = IncidentSeverity.HIGH
            reasons.append("configuration tampering detected")

        if SecurityEventType.PRIVILEGE_ATTEMPT in types:
            severity = max(
                severity,
                IncidentSeverity.HIGH,
                key=lambda x: list(IncidentSeverity).index(x),
            )
            reasons.append("privilege escalation attempt detected")

        if SecurityEventType.INTEGRITY_FAILURE in types:
            severity = IncidentSeverity.CRITICAL
            reasons.append("integrity failure detected")

        if SecurityEventType.PROCESS_ANOMALY in types:
            severity = max(
                severity,
                IncidentSeverity.HIGH,
                key=lambda x: list(IncidentSeverity).index(x),
            )
            reasons.append("process anomaly detected")

        if len(items) >= 3:
            severity = max(
                severity,
                IncidentSeverity.MEDIUM,
                key=lambda x: list(IncidentSeverity).index(x),
            )
            reasons.append("multiple security signals observed")

        detected = severity != IncidentSeverity.INFO

        confidence = min(
            0.99,
            0.35 + (len(items) * 0.10) + (0.20 if detected else 0.0),
        )

        return IncidentDetection(
            detected=detected,
            severity=severity,
            confidence=confidence,
            reasons=tuple(reasons),
            event_ids=tuple(e.event_id for e in items),
        )
