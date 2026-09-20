"""M37.2 Background Intelligence Trigger & Eligibility.

Evaluates background events for intelligence eligibility.

This layer:
- consumes normalized background events
- evaluates deterministic eligibility rules
- produces background intelligence work items only for eligible events
- never executes actions
- never bypasses human approval
- reuses the existing M37.1 event model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from .background_intelligence import (
    BackgroundEvent,
    BackgroundIntelligenceState,
    IntelligenceWorkItem,
)


class TriggerEligibility(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True)
class BackgroundTriggerDecision:
    """Deterministic eligibility decision for one background event."""

    event_id: str
    event_type: str
    source_system: str
    eligibility: TriggerEligibility
    reason: str
    evaluated_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def eligible(self) -> bool:
        return self.eligibility == TriggerEligibility.ELIGIBLE


@dataclass(frozen=True)
class BackgroundTriggerResult:
    """Result of a background trigger evaluation cycle."""

    processed_events: int
    eligible_events: int
    ineligible_events: int
    decisions: tuple[BackgroundTriggerDecision, ...]
    work_items: tuple[IntelligenceWorkItem, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundTriggerRuntime:
    """M37.2 deterministic background trigger runtime."""

    def __init__(
        self,
        *,
        event_types: Optional[set[str] | frozenset[str]] = None,
        source_systems: Optional[set[str] | frozenset[str]] = None,
    ) -> None:
        self._event_types = (
            frozenset(event_types)
            if event_types is not None
            else None
        )
        self._source_systems = (
            frozenset(source_systems)
            if source_systems is not None
            else None
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

    def evaluate(
        self,
        events: tuple[BackgroundEvent, ...] | list[BackgroundEvent],
        *,
        evaluated_at: datetime | None = None,
    ) -> BackgroundTriggerResult:
        """Evaluate events and create intelligence work only when eligible."""

        if not self.running:
            raise RuntimeError(
                "background trigger runtime is not running"
            )

        if evaluated_at is None:
            evaluated_at = datetime.now(timezone.utc)

        if (
            evaluated_at.tzinfo is None
            or evaluated_at.utcoffset() is None
        ):
            raise ValueError("evaluated_at must be timezone-aware")

        normalized = tuple(events)

        for event in normalized:
            if not isinstance(event, BackgroundEvent):
                raise TypeError(
                    "events must contain BackgroundEvent instances"
                )

            if not event.event_id.strip():
                raise ValueError("event_id must be non-empty")

            if not event.event_type.strip():
                raise ValueError("event_type must be non-empty")

            if not event.source_system.strip():
                raise ValueError("source_system must be non-empty")

            if (
                event.occurred_at.tzinfo is None
                or event.occurred_at.utcoffset() is None
            ):
                raise ValueError(
                    "event occurred_at must be timezone-aware"
                )

        decisions: list[BackgroundTriggerDecision] = []
        work_items: list[IntelligenceWorkItem] = []

        for event in sorted(
            normalized,
            key=lambda item: (
                item.occurred_at,
                item.event_id,
            ),
        ):
            if event.event_id in self._processed_event_ids:
                continue

            self._processed_event_ids.add(event.event_id)

            if (
                self._event_types is not None
                and event.event_type not in self._event_types
            ):
                decision = BackgroundTriggerDecision(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    source_system=event.source_system,
                    eligibility=TriggerEligibility.INELIGIBLE,
                    reason="event_type_not_eligible",
                    evaluated_at=evaluated_at,
                    metadata={
                        "source": "M37.2",
                        "read_only": True,
                        "executable": False,
                    },
                )
                decisions.append(decision)
                continue

            if (
                self._source_systems is not None
                and event.source_system not in self._source_systems
            ):
                decision = BackgroundTriggerDecision(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    source_system=event.source_system,
                    eligibility=TriggerEligibility.INELIGIBLE,
                    reason="source_system_not_eligible",
                    evaluated_at=evaluated_at,
                    metadata={
                        "source": "M37.2",
                        "read_only": True,
                        "executable": False,
                    },
                )
                decisions.append(decision)
                continue

            decision = BackgroundTriggerDecision(
                event_id=event.event_id,
                event_type=event.event_type,
                source_system=event.source_system,
                eligibility=TriggerEligibility.ELIGIBLE,
                reason="background_intelligence_trigger",
                evaluated_at=evaluated_at,
                metadata={
                    "source": "M37.2",
                    "read_only": True,
                    "executable": False,
                },
            )

            decisions.append(decision)

            work_items.append(
                IntelligenceWorkItem(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    source_system=event.source_system,
                    entity_id=event.entity_id,
                    detected_at=evaluated_at,
                    reason="background_intelligence_trigger",
                    requires_human_approval=True,
                    executable=False,
                    metadata={
                        "source": "M37.2",
                        "background_trigger": True,
                        "eligibility": TriggerEligibility.ELIGIBLE.value,
                        "detection_only": True,
                        "read_only": True,
                        "executable": False,
                    },
                )
            )

        eligible_count = sum(
            decision.eligible
            for decision in decisions
        )

        return BackgroundTriggerResult(
            processed_events=len(decisions),
            eligible_events=eligible_count,
            ineligible_events=len(decisions) - eligible_count,
            decisions=tuple(decisions),
            work_items=tuple(work_items),
            state=self._state,
            read_only=True,
            executable=False,
            metadata={
                "source": "M37.2",
                "background_trigger": True,
                "eligibility_layer": True,
                "read_only": True,
                "executable": False,
            },
        )
