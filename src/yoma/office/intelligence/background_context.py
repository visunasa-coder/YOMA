"""M37.4 Background Intelligence State & Context Accumulation.

Maintains bounded operational context for background intelligence.

This layer:
- consumes M37.3 detected conditions
- maintains recent context per operational entity
- keeps context bounded
- preserves deterministic ordering
- never executes actions
- never bypasses human approval
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .background_condition import (
    BackgroundCondition,
    ConditionSeverity,
)
from .background_intelligence import BackgroundIntelligenceState


@dataclass(frozen=True)
class ContextObservation:
    """One immutable observation retained in background context."""

    event_id: str
    event_type: str
    source_system: str
    entity_id: str | None
    condition: str
    severity: ConditionSeverity
    observed_at: datetime
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundContextSnapshot:
    """Bounded context for one operational entity."""

    context_key: str
    observations: tuple[ContextObservation, ...]
    observation_count: int
    latest_observed_at: datetime | None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundContextResult:
    """Result of one context accumulation cycle."""

    processed_conditions: int
    accumulated_observations: int
    contexts: tuple[BackgroundContextSnapshot, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundContextRuntime:
    """Deterministic bounded background context runtime."""

    def __init__(
        self,
        *,
        max_observations_per_context: int = 10,
    ) -> None:
        if max_observations_per_context < 1:
            raise ValueError(
                "max_observations_per_context must be >= 1"
            )

        self._max_observations = max_observations_per_context
        self._state = BackgroundIntelligenceState.STOPPED

        self._contexts: dict[
            str,
            list[ContextObservation],
        ] = {}

        self._processed_event_ids: set[str] = set()

    @property
    def state(self) -> BackgroundIntelligenceState:
        return self._state

    @property
    def running(self) -> bool:
        return (
            self._state
            == BackgroundIntelligenceState.RUNNING
        )

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True

    @property
    def max_observations_per_context(self) -> int:
        return self._max_observations

    def start(self) -> None:
        if self.running:
            return

        self._state = BackgroundIntelligenceState.RUNNING

    def stop(self) -> None:
        if not self.running:
            return

        self._state = BackgroundIntelligenceState.STOPPED

    def reset(self) -> None:
        """Clear accumulated background context."""

        self._contexts.clear()
        self._processed_event_ids.clear()

    def _context_key(
        self,
        condition: BackgroundCondition,
    ) -> str:
        """Build a stable context key."""

        if condition.event_id:
            return (
                f"{condition.source_system}:"
                f"{condition.event_type}"
            )

        return condition.source_system

    def accumulate(
        self,
        conditions: tuple[
            BackgroundCondition, ...
        ] | list[BackgroundCondition],
        *,
        observed_at: datetime | None = None,
    ) -> BackgroundContextResult:
        """Accumulate detected conditions into bounded context."""

        if not self.running:
            raise RuntimeError(
                "background context runtime is not running"
            )

        if observed_at is None:
            observed_at = datetime.now(timezone.utc)

        if (
            observed_at.tzinfo is None
            or observed_at.utcoffset() is None
        ):
            raise ValueError(
                "observed_at must be timezone-aware"
            )

        normalized = tuple(conditions)

        for condition in normalized:
            if not isinstance(
                condition,
                BackgroundCondition,
            ):
                raise TypeError(
                    "conditions must contain "
                    "BackgroundCondition instances"
                )

            if not condition.event_id.strip():
                raise ValueError(
                    "event_id must be non-empty"
                )

            if not condition.event_type.strip():
                raise ValueError(
                    "event_type must be non-empty"
                )

            if not condition.source_system.strip():
                raise ValueError(
                    "source_system must be non-empty"
                )

            if (
                condition.detected_at.tzinfo is None
                or condition.detected_at.utcoffset() is None
            ):
                raise ValueError(
                    "condition detected_at must be timezone-aware"
                )

        processed = 0
        accumulated = 0

        for condition in sorted(
            normalized,
            key=lambda item: (
                item.detected_at,
                item.event_id,
            ),
        ):
            if condition.event_id in self._processed_event_ids:
                continue

            self._processed_event_ids.add(
                condition.event_id
            )
            processed += 1

            observation = ContextObservation(
                event_id=condition.event_id,
                event_type=condition.event_type,
                source_system=condition.source_system,
                entity_id=None,
                condition=condition.condition,
                severity=condition.severity,
                observed_at=observed_at,
                reason=condition.reason,
                metadata={
                    "source": "M37.4",
                    "read_only": True,
                    "executable": False,
                    "requires_human_approval": True,
                },
            )

            key = self._context_key(condition)

            bucket = self._contexts.setdefault(
                key,
                [],
            )

            bucket.append(observation)

            bucket.sort(
                key=lambda item: (
                    item.observed_at,
                    item.event_id,
                )
            )

            if len(bucket) > self._max_observations:
                del bucket[
                    : len(bucket) - self._max_observations
                ]

            accumulated += 1

        snapshots: list[BackgroundContextSnapshot] = []

        for key in sorted(self._contexts):
            observations = tuple(self._contexts[key])

            snapshots.append(
                BackgroundContextSnapshot(
                    context_key=key,
                    observations=observations,
                    observation_count=len(observations),
                    latest_observed_at=(
                        observations[-1].observed_at
                        if observations
                        else None
                    ),
                    metadata={
                        "source": "M37.4",
                        "bounded": True,
                        "max_observations": (
                            self._max_observations
                        ),
                        "read_only": True,
                        "executable": False,
                    },
                )
            )

        return BackgroundContextResult(
            processed_conditions=processed,
            accumulated_observations=accumulated,
            contexts=tuple(snapshots),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.4",
                "context_accumulation": True,
                "bounded": True,
                "max_observations_per_context": (
                    self._max_observations
                ),
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
