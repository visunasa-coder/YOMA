from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .incident_events import SecurityEvent


@dataclass(frozen=True)
class InvestigationResult:
    incident_id: str
    primary_sources: tuple[str, ...]
    affected_layers: tuple[str, ...]
    findings: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    confidence: float
    read_only: bool = True
    executable: bool = False


class SecurityInvestigationEngine:
    def investigate(
        self,
        *,
        incident_id: str,
        events: Iterable[SecurityEvent],
    ) -> InvestigationResult:
        items = tuple(events)

        sources = tuple(sorted({e.source for e in items}))
        layers = tuple(sorted({e.source for e in items}))

        findings: list[str] = []

        types = {e.event_type.value for e in items}

        if "authentication_failure" in types:
            findings.append("authentication failures observed")

        if "privilege_attempt" in types:
            findings.append("privilege boundary was targeted")

        if "configuration_tamper" in types:
            findings.append("configuration integrity was targeted")

        if "suspicious_file" in types:
            findings.append("suspicious filesystem activity observed")

        if "process_anomaly" in types:
            findings.append("process anomaly observed")

        return InvestigationResult(
            incident_id=incident_id,
            primary_sources=sources,
            affected_layers=layers,
            findings=tuple(findings),
            evidence_event_ids=tuple(e.event_id for e in items),
            confidence=min(0.99, 0.40 + len(items) * 0.10),
        )
