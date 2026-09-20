"""M37.1 Background Embedded Intelligence.

Provides the read-only background event monitoring foundation for YOMA.

This layer:
- receives operational events
- maintains background monitoring state
- converts eligible events into deterministic intelligence work items
- never executes actions
- never creates or bypasses human approval
- does not replace the canonical YOMA event bus
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class BackgroundIntelligenceState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"


@dataclass(frozen=True)
class BackgroundEvent:
    """Normalized event presented to the background intelligence layer."""

    event_id: str
    event_type: str
    occurred_at: datetime
    source_system: str
    entity_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntelligenceWorkItem:
    """Read-only work item produced from a background event."""

    event_id: str
    event_type: str
    source_system: str
    entity_id: str | None
    detected_at: datetime
    reason: str
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundIntelligenceResult:
    """Deterministic result of one background monitoring cycle."""

    processed_events: int
    detected_events: int
    work_items: tuple[IntelligenceWorkItem, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundIntelligenceRuntime:
    """M37.1 background event-monitoring runtime.

    This runtime intentionally stops at detection/intelligence generation.
    Any downstream action remains subject to the existing YOMA control,
    governance, and human-approval architecture.
    """

    def __init__(
        self,
        *,
        event_types: Optional[set[str] | frozenset[str]] = None,
    ) -> None:
        self._event_types = (
            frozenset(event_types)
            if event_types is not None
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
        """Start background monitoring."""
        if self._state == BackgroundIntelligenceState.RUNNING:
            return

        self._state = BackgroundIntelligenceState.RUNNING

    def stop(self) -> None:
        """Stop background monitoring."""
        if self._state == BackgroundIntelligenceState.STOPPED:
            return

        self._state = BackgroundIntelligenceState.STOPPED

    def reset(self) -> None:
        """Reset runtime-local event processing state."""
        self._processed_event_ids.clear()

    def process(
        self,
        events: tuple[BackgroundEvent, ...] | list[BackgroundEvent],
        *,
        detected_at: datetime | None = None,
    ) -> BackgroundIntelligenceResult:
        """Process a deterministic batch of background events.

        Events are observed only while the runtime is running.
        Duplicate event IDs are ignored within this runtime instance.
        """

        if not self.running:
            raise RuntimeError(
                "background intelligence runtime is not running"
            )

        if detected_at is None:
            detected_at = datetime.now(timezone.utc)

        if detected_at.tzinfo is None or detected_at.utcoffset() is None:
            raise ValueError("detected_at must be timezone-aware")

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
                continue

            work_items.append(
                IntelligenceWorkItem(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    source_system=event.source_system,
                    entity_id=event.entity_id,
                    detected_at=detected_at,
                    reason=(
                        "background_event_detected"
                    ),
                    requires_human_approval=True,
                    executable=False,
                    metadata={
                        "source": "M37.1",
                        "background_intelligence": True,
                        "analytics_only": False,
                        "detection_only": True,
                        "read_only": True,
                        "executable": False,
                    },
                )
            )

        return BackgroundIntelligenceResult(
            processed_events=len(normalized),
            detected_events=len(work_items),
            work_items=tuple(work_items),
            state=self._state,
            read_only=True,
            executable=False,
            metadata={
                "source": "M37.1",
                "background_monitoring": True,
                "continuous_worker_foundation": True,
                "detection_only": True,
                "read_only": True,
                "executable": False,
            },
        )
