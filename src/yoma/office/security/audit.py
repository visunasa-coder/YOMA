"""Tamper-evident security event chain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class SecurityAuditEvent:
    sequence: int
    timestamp: str
    event_type: str
    actor: str
    resource: str
    status: str
    previous_hash: str
    event_hash: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "resource": self.resource,
            "status": self.status,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
            "metadata": dict(self.metadata),
        }


class SecurityAuditChain:
    """In-memory tamper-evident event chain."""

    def __init__(self) -> None:
        self._events: list[SecurityAuditEvent] = []

    @staticmethod
    def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
        result = dict(metadata or {})
        secret_words = (
            "token",
            "secret",
            "password",
            "credential",
            "authorization",
            "api_key",
            "apikey",
        )

        for key in list(result):
            if any(word in key.lower() for word in secret_words):
                result.pop(key)

        return result

    def record(
        self,
        *,
        event_type: str,
        actor: str,
        resource: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityAuditEvent:

        sequence = len(self._events) + 1
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = (
            self._events[-1].event_hash
            if self._events
            else "GENESIS"
        )
        safe_metadata = self._safe_metadata(metadata)

        payload = {
            "sequence": sequence,
            "timestamp": timestamp,
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "status": status,
            "previous_hash": previous_hash,
            "metadata": safe_metadata,
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

        event_hash = hashlib.sha256(encoded).hexdigest()

        event = SecurityAuditEvent(
            sequence=sequence,
            timestamp=timestamp,
            event_type=event_type,
            actor=actor,
            resource=resource,
            status=status,
            previous_hash=previous_hash,
            event_hash=event_hash,
            metadata=safe_metadata,
        )

        self._events.append(event)
        return event

    def list(self) -> list[SecurityAuditEvent]:
        return list(self._events)

    def verify(self) -> bool:
        previous = "GENESIS"

        for event in self._events:
            payload = {
                "sequence": event.sequence,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "actor": event.actor,
                "resource": event.resource,
                "status": event.status,
                "previous_hash": event.previous_hash,
                "metadata": event.metadata,
            }

            encoded = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")

            expected = hashlib.sha256(encoded).hexdigest()

            if event.previous_hash != previous:
                return False

            if event.event_hash != expected:
                return False

            previous = event.event_hash

        return True
