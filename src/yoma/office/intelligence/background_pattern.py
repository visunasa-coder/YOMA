"""M37.5 Background Intelligence Pattern Recognition.

Recognizes repeated and emerging operational patterns from M37.4
bounded background context.

This layer:
- consumes M37.4 context snapshots
- detects deterministic repeated/emerging patterns
- produces explainable pattern findings
- never executes actions
- never bypasses human approval
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from .background_condition import ConditionSeverity
from .background_context import BackgroundContextSnapshot
from .background_intelligence import BackgroundIntelligenceState


class PatternType(str, Enum):
    REPEATED_EVENT = "repeated_event"
    ESCALATION = "escalation"
    CRITICAL_REPETITION = "critical_repetition"


@dataclass(frozen=True)
class BackgroundPattern:
    """Detected operational pattern."""

    context_key: str
    pattern_type: PatternType
    severity: ConditionSeverity
    occurrence_count: int
    event_ids: tuple[str, ...]
    reason: str
    detected_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundPatternResult:
    """Result of one pattern-recognition cycle."""

    processed_contexts: int
    detected_patterns: int
    patterns: tuple[BackgroundPattern, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundPatternRuntime:
    """Deterministic background operational pattern detector."""

    def __init__(
        self,
        *,
        repetition_threshold: int = 3,
        escalation_threshold: int = 2,
        critical_threshold: int = 2,
    ) -> None:
        if repetition_threshold < 2:
            raise ValueError(
                "repetition_threshold must be >= 2"
            )

        if escalation_threshold < 2:
            raise ValueError(
                "escalation_threshold must be >= 2"
            )

        if critical_threshold < 2:
            raise ValueError(
                "critical_threshold must be >= 2"
            )

        self._repetition_threshold = repetition_threshold
        self._escalation_threshold = escalation_threshold
        self._critical_threshold = critical_threshold

        self._state = BackgroundIntelligenceState.STOPPED
        self._processed_context_keys: set[str] = set()

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

    def start(self) -> None:
        if self.running:
            return

        self._state = BackgroundIntelligenceState.RUNNING

    def stop(self) -> None:
        if not self.running:
            return

        self._state = BackgroundIntelligenceState.STOPPED

    def reset(self) -> None:
        self._processed_context_keys.clear()

    def recognize(
        self,
        contexts: tuple[
            BackgroundContextSnapshot, ...
        ] | list[BackgroundContextSnapshot],
        *,
        detected_at: datetime | None = None,
    ) -> BackgroundPatternResult:
        """Recognize patterns from bounded operational context."""

        if not self.running:
            raise RuntimeError(
                "background pattern runtime is not running"
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

        normalized = tuple(contexts)

        for context in normalized:
            if not isinstance(
                context,
                BackgroundContextSnapshot,
            ):
                raise TypeError(
                    "contexts must contain "
                    "BackgroundContextSnapshot instances"
                )

            if not context.context_key.strip():
                raise ValueError(
                    "context_key must be non-empty"
                )

            for observation in context.observations:
                if (
                    observation.observed_at.tzinfo is None
                    or observation.observed_at.utcoffset() is None
                ):
                    raise ValueError(
                        "observation observed_at must be "
                        "timezone-aware"
                    )

        patterns: list[BackgroundPattern] = []

        for context in sorted(
            normalized,
            key=lambda item: item.context_key,
        ):
            if context.context_key in self._processed_context_keys:
                continue

            self._processed_context_keys.add(
                context.context_key
            )

            observations = tuple(
                sorted(
                    context.observations,
                    key=lambda item: (
                        item.observed_at,
                        item.event_id,
                    ),
                )
            )

            if not observations:
                continue

            count = len(observations)
            event_ids = tuple(
                observation.event_id
                for observation in observations
            )

            critical_count = sum(
                observation.severity
                == ConditionSeverity.CRITICAL
                for observation in observations
            )

            escalation_count = sum(
                observation.condition
                in {
                    "warning_operational_condition",
                    "critical_operational_condition",
                }
                for observation in observations
            )

            if critical_count >= self._critical_threshold:
                patterns.append(
                    BackgroundPattern(
                        context_key=context.context_key,
                        pattern_type=(
                            PatternType.CRITICAL_REPETITION
                        ),
                        severity=ConditionSeverity.CRITICAL,
                        occurrence_count=critical_count,
                        event_ids=event_ids,
                        reason=(
                            "repeated critical operational "
                            "conditions detected"
                        ),
                        detected_at=detected_at,
                        metadata={
                            "source": "M37.5",
                            "read_only": True,
                            "executable": False,
                            "requires_human_approval": True,
                        },
                    )
                )

            elif escalation_count >= self._escalation_threshold:
                patterns.append(
                    BackgroundPattern(
                        context_key=context.context_key,
                        pattern_type=PatternType.ESCALATION,
                        severity=ConditionSeverity.WARNING,
                        occurrence_count=escalation_count,
                        event_ids=event_ids,
                        reason=(
                            "repeated warning or critical "
                            "conditions indicate an "
                            "emerging escalation pattern"
                        ),
                        detected_at=detected_at,
                        metadata={
                            "source": "M37.5",
                            "read_only": True,
                            "executable": False,
                            "requires_human_approval": True,
                        },
                    )
                )

            elif count >= self._repetition_threshold:
                patterns.append(
                    BackgroundPattern(
                        context_key=context.context_key,
                        pattern_type=PatternType.REPEATED_EVENT,
                        severity=ConditionSeverity.INFO,
                        occurrence_count=count,
                        event_ids=event_ids,
                        reason=(
                            "repeated operational event "
                            "pattern detected"
                        ),
                        detected_at=detected_at,
                        metadata={
                            "source": "M37.5",
                            "read_only": True,
                            "executable": False,
                            "requires_human_approval": True,
                        },
                    )
                )

        return BackgroundPatternResult(
            processed_contexts=len(normalized),
            detected_patterns=len(patterns),
            patterns=tuple(patterns),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.5",
                "pattern_recognition": True,
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
