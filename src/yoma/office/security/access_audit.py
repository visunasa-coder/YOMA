from dataclasses import dataclass
import hashlib
import json
import time


@dataclass(frozen=True)
class AccessAuditEvent:
    event_id: str
    identity_id: str
    resource: str
    decision: str
    reason: str
    timestamp: float


class AccessAuditChain:
    def __init__(self):
        self._events = []
        self._hashes = []

    def append(self, event: AccessAuditEvent):
        previous = self._hashes[-1] if self._hashes else "GENESIS"
        payload = {
            "event": event.__dict__,
            "previous": previous,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        self._events.append(event)
        self._hashes.append(digest)
        return digest

    def verify(self):
        previous = "GENESIS"

        for event, expected in zip(self._events, self._hashes):
            payload = {
                "event": event.__dict__,
                "previous": previous,
            }
            actual = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()

            if actual != expected:
                return False

            previous = actual

        return True

    @property
    def events(self):
        return tuple(self._events)


class AccessAnomalyDetector:
    def assess(self, failed_attempts: int, privilege_attempts: int):
        score = failed_attempts * 10 + privilege_attempts * 25

        if privilege_attempts > 0 or score >= 50:
            severity = "high"
        elif score >= 20:
            severity = "medium"
        else:
            severity = "low"

        return {
            "score": score,
            "severity": severity,
            "suspicious": score >= 20,
            "requires_human_approval": True,
            "executable": False,
        }
