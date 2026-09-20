"""M37.6 Background Intelligence Risk & Priority Assessment.

Assesses operational risk and attention priority from M37.5 patterns.

This layer:
- consumes M37.5 background patterns
- deterministically classifies risk and priority
- provides explainable assessment
- never executes actions
- never grants authorization
- preserves human approval requirements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .background_condition import ConditionSeverity
from .background_intelligence import BackgroundIntelligenceState
from .background_pattern import (
    BackgroundPattern,
    PatternType,
)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class BackgroundPriorityAssessment:
    """Risk and attention-priority assessment for one pattern."""

    context_key: str
    pattern_type: PatternType
    risk_level: RiskLevel
    priority: PriorityLevel
    occurrence_count: int
    event_ids: tuple[str, ...]
    reason: str
    assessed_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundPriorityResult:
    """Result of one risk/priority assessment cycle."""

    processed_patterns: int
    assessed_patterns: int
    assessments: tuple[BackgroundPriorityAssessment, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundPriorityRuntime:
    """Deterministic background risk and priority assessor."""

    def __init__(
        self,
        *,
        high_occurrence_threshold: int = 5,
        urgent_occurrence_threshold: int = 5,
    ) -> None:
        if high_occurrence_threshold < 1:
            raise ValueError(
                "high_occurrence_threshold must be >= 1"
            )

        if urgent_occurrence_threshold < 1:
            raise ValueError(
                "urgent_occurrence_threshold must be >= 1"
            )

        self._high_occurrence_threshold = (
            high_occurrence_threshold
        )
        self._urgent_occurrence_threshold = (
            urgent_occurrence_threshold
        )

        self._state = BackgroundIntelligenceState.STOPPED
        self._processed_pattern_keys: set[
            tuple[str, PatternType, tuple[str, ...]]
        ] = set()

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
        self._processed_pattern_keys.clear()

    def _assessment_key(
        self,
        pattern: BackgroundPattern,
    ) -> tuple[str, PatternType, tuple[str, ...]]:
        return (
            pattern.context_key,
            pattern.pattern_type,
            pattern.event_ids,
        )

    def _assess(
        self,
        pattern: BackgroundPattern,
    ) -> tuple[RiskLevel, PriorityLevel, str]:
        """Apply deterministic risk/priority rules."""

        if (
            pattern.pattern_type
            == PatternType.CRITICAL_REPETITION
        ):
            if (
                pattern.occurrence_count
                >= self._urgent_occurrence_threshold
            ):
                return (
                    RiskLevel.CRITICAL,
                    PriorityLevel.URGENT,
                    "repeated critical conditions require "
                    "urgent human attention",
                )

            return (
                RiskLevel.CRITICAL,
                PriorityLevel.HIGH,
                "critical operational pattern requires "
                "high-priority human attention",
            )

        if pattern.pattern_type == PatternType.ESCALATION:
            if (
                pattern.occurrence_count
                >= self._high_occurrence_threshold
            ):
                return (
                    RiskLevel.HIGH,
                    PriorityLevel.HIGH,
                    "repeated escalation pattern indicates "
                    "elevated operational risk",
                )

            return (
                RiskLevel.MEDIUM,
                PriorityLevel.NORMAL,
                "emerging escalation pattern warrants "
                "human review",
            )

        if (
            pattern.occurrence_count
            >= self._high_occurrence_threshold
        ):
            return (
                RiskLevel.MEDIUM,
                PriorityLevel.NORMAL,
                "repeated operational activity may indicate "
                "an emerging issue",
            )

        return (
            RiskLevel.LOW,
            PriorityLevel.LOW,
            "repeated operational activity currently "
            "represents low assessed risk",
        )

    def assess(
        self,
        patterns: tuple[
            BackgroundPattern, ...
        ] | list[BackgroundPattern],
        *,
        assessed_at: datetime | None = None,
    ) -> BackgroundPriorityResult:
        """Assess risk and priority for background patterns."""

        if not self.running:
            raise RuntimeError(
                "background priority runtime is not running"
            )

        if assessed_at is None:
            assessed_at = datetime.now(timezone.utc)

        if (
            assessed_at.tzinfo is None
            or assessed_at.utcoffset() is None
        ):
            raise ValueError(
                "assessed_at must be timezone-aware"
            )

        normalized = tuple(patterns)

        for pattern in normalized:
            if not isinstance(
                pattern,
                BackgroundPattern,
            ):
                raise TypeError(
                    "patterns must contain "
                    "BackgroundPattern instances"
                )

            if not pattern.context_key.strip():
                raise ValueError(
                    "context_key must be non-empty"
                )

            if pattern.occurrence_count < 1:
                raise ValueError(
                    "occurrence_count must be >= 1"
                )

            if (
                pattern.detected_at.tzinfo is None
                or pattern.detected_at.utcoffset() is None
            ):
                raise ValueError(
                    "pattern detected_at must be timezone-aware"
                )

        assessments: list[
            BackgroundPriorityAssessment
        ] = []

        for pattern in sorted(
            normalized,
            key=lambda item: (
                item.context_key,
                item.pattern_type.value,
                item.event_ids,
            ),
        ):
            key = self._assessment_key(pattern)

            if key in self._processed_pattern_keys:
                continue

            self._processed_pattern_keys.add(key)

            risk, priority, reason = self._assess(pattern)

            assessments.append(
                BackgroundPriorityAssessment(
                    context_key=pattern.context_key,
                    pattern_type=pattern.pattern_type,
                    risk_level=risk,
                    priority=priority,
                    occurrence_count=pattern.occurrence_count,
                    event_ids=pattern.event_ids,
                    reason=reason,
                    assessed_at=assessed_at,
                    metadata={
                        "source": "M37.6",
                        "read_only": True,
                        "executable": False,
                        "requires_human_approval": True,
                    },
                )
            )

        return BackgroundPriorityResult(
            processed_patterns=len(normalized),
            assessed_patterns=len(assessments),
            assessments=tuple(assessments),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.6",
                "risk_priority_assessment": True,
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
