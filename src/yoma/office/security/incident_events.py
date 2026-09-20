from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class IncidentSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentState(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    PENDING_APPROVAL = "pending_approval"
    CONTAINED = "contained"
    RECOVERING = "recovering"
    RESOLVED = "resolved"


class SecurityEventType(str, Enum):
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    PRIVILEGE_ATTEMPT = "privilege_attempt"
    CONFIGURATION_TAMPER = "configuration_tamper"
    SUSPICIOUS_FILE = "suspicious_file"
    UNKNOWN_DEVICE = "unknown_device"
    PROCESS_ANOMALY = "process_anomaly"
    FILESYSTEM_ANOMALY = "filesystem_anomaly"
    INTEGRITY_FAILURE = "integrity_failure"
    CONTAINMENT = "containment"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    event_type: SecurityEventType
    severity: IncidentSeverity
    source: str
    source_id: str
    timestamp: str
    description: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        event_type: SecurityEventType,
        severity: IncidentSeverity,
        source: str,
        source_id: str,
        description: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> "SecurityEvent":
        return cls(
            event_id=uuid4().hex,
            event_type=event_type,
            severity=severity,
            source=source,
            source_id=source_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description,
            metadata=dict(metadata or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


class SecurityEventNormalizer:
    def normalize(self, event: SecurityEvent | Mapping[str, Any]) -> SecurityEvent:
        if isinstance(event, SecurityEvent):
            return event

        if not isinstance(event, Mapping):
            raise TypeError("security event must be a mapping or SecurityEvent")

        event_type = SecurityEventType(str(event["event_type"]))
        severity = IncidentSeverity(str(event.get("severity", "info")))

        source = str(event.get("source", "unknown"))
        source_id = str(event.get("source_id", "unknown"))
        description = str(event.get("description", ""))

        metadata = event.get("metadata", {})
        if not isinstance(metadata, Mapping):
            metadata = {}

        return SecurityEvent(
            event_id=str(event.get("event_id") or uuid4().hex),
            event_type=event_type,
            severity=severity,
            source=source,
            source_id=source_id,
            timestamp=str(
                event.get("timestamp")
                or datetime.now(timezone.utc).isoformat()
            ),
            description=description,
            metadata=dict(metadata),
        )
