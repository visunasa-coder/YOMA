"""Defensive request validation and abuse controls."""

from __future__ import annotations

from dataclasses import dataclass
import re
import time


@dataclass(frozen=True)
class RequestGuardResult:
    valid: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "reason": self.reason,
        }


class RequestGuard:
    """Reject malformed, oversized, or obviously unsafe requests."""

    _CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def __init__(
        self,
        *,
        max_body_bytes: int = 10 * 1024 * 1024,
        max_text_length: int = 1_000_000,
    ) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        if max_text_length <= 0:
            raise ValueError("max_text_length must be positive")

        self.max_body_bytes = max_body_bytes
        self.max_text_length = max_text_length

    def validate(
        self,
        *,
        body_size: int,
        text: str | None = None,
    ) -> RequestGuardResult:
        if not isinstance(body_size, int):
            raise TypeError("body_size must be int")

        if body_size < 0:
            return RequestGuardResult(False, "negative body size")

        if body_size > self.max_body_bytes:
            return RequestGuardResult(False, "request body too large")

        if text is not None:
            if not isinstance(text, str):
                return RequestGuardResult(False, "invalid text type")

            if len(text) > self.max_text_length:
                return RequestGuardResult(False, "text payload too large")

            if self._CONTROL_RE.search(text):
                return RequestGuardResult(False, "control characters rejected")

        return RequestGuardResult(True, "request accepted")


class RateLimiter:
    """Small in-process sliding-window limiter."""

    def __init__(
        self,
        *,
        limit: int = 60,
        window_seconds: float = 60.0,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, list[float]] = {}

    def allow(self, identity: str) -> bool:
        identity = identity.strip()
        if not identity:
            return False

        now = time.monotonic()
        events = self._events.setdefault(identity, [])

        cutoff = now - self.window_seconds
        events[:] = [event for event in events if event > cutoff]

        if len(events) >= self.limit:
            return False

        events.append(now)
        return True
