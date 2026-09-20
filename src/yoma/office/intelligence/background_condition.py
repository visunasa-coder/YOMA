"""M37.3 Background Intelligence Condition Detection.

Detects meaningful operational conditions from eligible background
intelligence triggers.

This layer:
- consumes M37.2 eligibility decisions
- detects deterministic operational conditions
- produces explainable findings
- never executes actions
- never creates or bypasses human approval
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from .background_intelligence import BackgroundIntelligenceState
from .background_trigger import (
    BackgroundTriggerDecision,
    TriggerEligibility,
)


class ConditionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class BackgroundCondition:
    """Detected operational condition."""

    event_id: str
    event_type: str
    source_system: str
    condition: str
    severity: ConditionSeverity
    reason: str
    detected_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundConditionResult:
    """Result of one condition-detection cycle."""

    processed_events: int
    detected_conditions: int
    conditions: tuple[BackgroundCondition, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundConditionRuntime:
    """Deterministic M37.3 condition detector."""

    def __init__(
        self,
        *,
        warning_event_types: Optional[
            set[str] | frozenset[str]
        ] = None,
        critical_event_types: Optional[
            set[str] | frozenset[str]
        ] = None,
    ) -> None:
        self._warning_event_types = (
            frozenset(warning_event_types)
            if warning_event_types is not None
            else frozenset(
                {
                    "incident.created",
                    "ticket.escalated",
                    "sla.warning",
                    "capacity.warning",
                }
            )
        )

        self._critical_event_types = (
            frozenset(critical_event_types)
            if critical_event_types is not None
            else frozenset(
                {
                    "incident.critical",
                    "service.outage",
                    "sla.breached",
                    "security.alert",
                }
            )
        )

        self._state = BackgroundIntelligenceState.STOPPED
        self._processed_event_ids: set[str] = set()

    @property
    def state(self) -> BackgroundIntelligenceState:
        return self._state

    @property
    def running(self) -> bool:
        return self._state == BackgroundIntelligenceState.RUNNING

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True

    def start(self) -> None:
        if self._state == BackgroundIntelligenceState.RUNNING:
            return

        self._state = BackgroundIntelligenceState.RUNNING

    def stop(self) -> None:
        if self._state == BackgroundIntelligenceState.STOPPED:
            return

        self._state = BackgroundIntelligenceState.STOPPED

    def reset(self) -> None:
        self._processed_event_ids.clear()

    def detect(
        self,
        decisions: tuple[
            BackgroundTriggerDecision, ...
        ] | list[BackgroundTriggerDecision],
        *,
        detected_at: datetime | None = None,
    ) -> BackgroundConditionResult:
        """Detect meaningful conditions from eligible trigger decisions."""

        if not self.running:
            raise RuntimeError(
                "background condition runtime is not running"
            )

        if detected_at is None:
            detected_at = datetime.now(timezone.utc)

        if (
            detected_at.tzinfo is None
            or detected_at.utcoffset() is None
        ):
            raise ValueError(
                "detected_at must be timezone-aware"
            )

        normalized = tuple(decisions)

        for decision in normalized:
            if not isinstance(
                decision,
                BackgroundTriggerDecision,
            ):
                raise TypeError(
                    "decisions must contain "
                    "BackgroundTriggerDecision instances"
                )

            if not decision.event_id.strip():
                raise ValueError(
                    "event_id must be non-empty"
                )

            if not decision.event_type.strip():
                raise ValueError(
                    "event_type must be non-empty"
                )

            if not decision.source_system.strip():
                raise ValueError(
                    "source_system must be non-empty"
                )

            if (
                decision.evaluated_at.tzinfo is None
                or decision.evaluated_at.utcoffset() is None
            ):
                raise ValueError(
                    "decision evaluated_at must be timezone-aware"
                )

        conditions: list[BackgroundCondition] = []

        for decision in sorted(
            normalized,
            key=lambda item: (
                item.evaluated_at,
                item.event_id,
            ),
        ):
            if decision.event_id in self._processed_event_ids:
                continue

            self._processed_event_ids.add(
                decision.event_id
            )

            if (
                decision.eligibility
                != TriggerEligibility.ELIGIBLE
            ):
                continue

            severity: ConditionSeverity | None = None
            condition: str | None = None
            reason: str | None = None

            if decision.event_type in self._critical_event_types:
                severity = ConditionSeverity.CRITICAL
                condition = "critical_operational_condition"
                reason = (
                    "eligible event matches a critical "
                    "background condition"
                )

            elif decision.event_type in self._warning_event_types:
                severity = ConditionSeverity.WARNING
                condition = "warning_operational_condition"
                reason = (
                    "eligible event matches a warning "
                    "background condition"
                )

            else:
                severity = ConditionSeverity.INFO
                condition = "operational_event_detected"
                reason = (
                    "eligible event represents an observable "
                    "operational condition"
                )

            conditions.append(
                BackgroundCondition(
                    event_id=decision.event_id,
                    event_type=decision.event_type,
                    source_system=decision.source_system,
                    condition=condition,
                    severity=severity,
                    reason=reason,
                    detected_at=detected_at,
                    metadata={
                        "source": "M37.3",
                        "eligibility": (
                            decision.eligibility.value
                        ),
                        "read_only": True,
                        "executable": False,
                        "requires_human_approval": True,
                    },
                )
            )

        return BackgroundConditionResult(
            processed_events=len(normalized),
            detected_conditions=len(conditions),
            conditions=tuple(conditions),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.3",
                "condition_detection": True,
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
