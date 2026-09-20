from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from yoma.office.actions import ActionRequest, ActionResult


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    event_type: str
    timestamp: datetime
    actor: str
    request_id: str
    action_type: str
    status: str
    reason: str | None = None
    metadata: dict[str, Any] | None = None


Policy = Callable[[ActionRequest], PolicyDecision]


class PolicyEngine:
    """Central policy evaluation layer for controlled actions."""

    def __init__(self) -> None:
        self._policies: list[tuple[str, Policy]] = []

    def register(
        self,
        name: str,
        policy: Policy,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("Policy name is required")

        if any(existing == name for existing, _ in self._policies):
            raise ValueError(f"Policy already registered: {name}")

        self._policies.append((name, policy))

    def evaluate(
        self,
        request: ActionRequest,
    ) -> PolicyDecision:
        for name, policy in self._policies:
            decision = policy(request)

            if not isinstance(decision, PolicyDecision):
                raise TypeError(
                    f"Policy '{name}' must return PolicyDecision"
                )

            if not decision.allowed:
                return decision

        return PolicyDecision(
            allowed=True,
            reason="all_policies_allowed",
        )

    def list_policies(self) -> list[str]:
        return [name for name, _ in self._policies]


class AuditLog:
    """
    In-process audit sink.

    Production persistence can later be connected to YOMA's
    existing audit_events database without changing callers.
    """

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record(
        self,
        *,
        audit_id: str,
        event_type: str,
        actor: str,
        request_id: str,
        action_type: str,
        status: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        safe_metadata = dict(metadata or {})

        # Never persist credential/token fields.
        for key in list(safe_metadata):
            if any(
                secret in key.lower()
                for secret in (
                    "token",
                    "secret",
                    "password",
                    "credential",
                    "authorization",
                )
            ):
                safe_metadata.pop(key)

        record = AuditRecord(
            audit_id=audit_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            request_id=request_id,
            action_type=action_type,
            status=status,
            reason=reason,
            metadata=safe_metadata,
        )

        self._records.append(record)

        return record

    def list(self) -> list[AuditRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)
