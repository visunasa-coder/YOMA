"""Adaptive defensive source blocking.

This is a policy engine, not an offensive network scanner.
It creates temporary restrictions based on repeated security
signals. It never executes firewall commands itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time


class SourceBlockState(str, Enum):
    ALLOWED = "allowed"
    WATCH = "watch"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SecuritySignal:
    source_id: str
    signal: str
    severity: str = "medium"

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id required")


@dataclass(frozen=True)
class SourceReputation:
    source_id: str
    score: int
    state: SourceBlockState
    failures: int
    blocked_until: float | None = None
    reason: str = ""
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "score": self.score,
            "state": self.state.value,
            "failures": self.failures,
            "blocked_until": self.blocked_until,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class AdaptiveAttackDefense:
    """
    Tracks repeated suspicious behavior.

    Policy:
      0-39   -> allowed/watch
      40-69  -> watch
      70+    -> temporary block

    Critical signals immediately move the source to blocking.
    """

    WEIGHTS = {
        "failed_authentication": 15,
        "rate_limit": 20,
        "invalid_request": 15,
        "privilege_attempt": 40,
        "configuration_tamper": 50,
        "suspicious_file": 30,
        "unknown_device": 15,
    }

    def __init__(
        self,
        *,
        block_seconds: int = 900,
    ) -> None:
        if block_seconds <= 0:
            raise ValueError("block_seconds must be positive")

        self.block_seconds = block_seconds
        self._scores: dict[str, int] = {}
        self._failures: dict[str, int] = {}
        self._blocked_until: dict[str, float] = {}

    def observe(self, signal: SecuritySignal) -> SourceReputation:
        now = time.time()
        source = signal.source_id
        weight = self.WEIGHTS.get(signal.signal, 10)

        score = self._scores.get(source, 0) + weight
        failures = self._failures.get(source, 0) + 1

        self._scores[source] = score
        self._failures[source] = failures

        severity = signal.severity.lower()

        if severity == "critical" or score >= 70:
            blocked_until = max(
                self._blocked_until.get(source, 0),
                now + self.block_seconds,
            )
            self._blocked_until[source] = blocked_until

            return SourceReputation(
                source,
                score,
                SourceBlockState.BLOCKED,
                failures,
                blocked_until,
                "temporary security block triggered",
            )

        if score >= 40:
            return SourceReputation(
                source,
                score,
                SourceBlockState.WATCH,
                failures,
                reason="source placed under heightened monitoring",
            )

        return SourceReputation(
            source,
            score,
            SourceBlockState.ALLOWED,
            failures,
            reason="source remains below blocking threshold",
        )

    def check(self, source_id: str) -> SourceReputation:
        now = time.time()
        blocked_until = self._blocked_until.get(source_id)

        if blocked_until and blocked_until > now:
            return SourceReputation(
                source_id,
                self._scores.get(source_id, 0),
                SourceBlockState.BLOCKED,
                self._failures.get(source_id, 0),
                blocked_until,
                "source is temporarily blocked",
            )

        return SourceReputation(
            source_id,
            self._scores.get(source_id, 0),
            SourceBlockState.ALLOWED,
            self._failures.get(source_id, 0),
            reason="source is not currently blocked",
        )

    def clear_after_review(self, source_id: str) -> SourceReputation:
        self._scores.pop(source_id, None)
        self._failures.pop(source_id, None)
        self._blocked_until.pop(source_id, None)

        return SourceReputation(
            source_id,
            0,
            SourceBlockState.ALLOWED,
            0,
            reason="restriction cleared by governed review",
        )
