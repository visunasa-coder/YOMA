"""M37.7 Background Intelligence Recommendation & Human Attention.

Converts M37.6 risk/priority assessments into explainable
human-attention recommendations.

This layer:
- consumes M37.6 assessments
- produces deterministic recommendations
- clearly separates recommendation from authorization
- never executes actions
- never creates or bypasses approval
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .background_intelligence import BackgroundIntelligenceState
from .background_priority import (
    BackgroundPriorityAssessment,
    PriorityLevel,
    RiskLevel,
)
from .background_pattern import PatternType


class RecommendationType(str, Enum):
    REVIEW = "review"
    INVESTIGATE = "investigate"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass(frozen=True)
class BackgroundRecommendation:
    context_key: str
    recommendation_type: RecommendationType
    priority: PriorityLevel
    risk_level: RiskLevel
    event_ids: tuple[str, ...]
    occurrence_count: int
    title: str
    reason: str
    recommended_next_step: str
    created_at: datetime
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackgroundRecommendationResult:
    processed_assessments: int
    recommendations_created: int
    recommendations: tuple[BackgroundRecommendation, ...]
    state: BackgroundIntelligenceState
    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BackgroundRecommendationRuntime:
    """Deterministic background recommendation runtime."""

    def __init__(self) -> None:
        self._state = BackgroundIntelligenceState.STOPPED
        self._processed_keys: set[
            tuple[str, str, tuple[str, ...]]
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
        self._processed_keys.clear()

    def _recommendation_type(
        self,
        assessment: BackgroundPriorityAssessment,
    ) -> RecommendationType:
        if assessment.priority == PriorityLevel.URGENT:
            return RecommendationType.ESCALATE_TO_HUMAN

        if assessment.risk_level in {
            RiskLevel.CRITICAL,
            RiskLevel.HIGH,
        }:
            return RecommendationType.INVESTIGATE

        return RecommendationType.REVIEW

    def _title(
        self,
        assessment: BackgroundPriorityAssessment,
        recommendation_type: RecommendationType,
    ) -> str:
        if recommendation_type == RecommendationType.ESCALATE_TO_HUMAN:
            return "Urgent operational attention required"

        if recommendation_type == RecommendationType.INVESTIGATE:
            return "Operational issue warrants investigation"

        if assessment.pattern_type == PatternType.ESCALATION:
            return "Emerging operational escalation detected"

        return "Repeated operational activity detected"

    def _next_step(
        self,
        assessment: BackgroundPriorityAssessment,
        recommendation_type: RecommendationType,
    ) -> str:
        if recommendation_type == RecommendationType.ESCALATE_TO_HUMAN:
            return (
                "Escalate the finding to an authorized human "
                "for review and decision"
            )

        if recommendation_type == RecommendationType.INVESTIGATE:
            return (
                "Review the affected operational context "
                "and investigate the underlying condition"
            )

        return (
            "Review the operational context and determine "
            "whether further action is warranted"
        )

    def recommend(
        self,
        assessments: tuple[
            BackgroundPriorityAssessment, ...
        ] | list[BackgroundPriorityAssessment],
        *,
        created_at: datetime | None = None,
    ) -> BackgroundRecommendationResult:

        if not self.running:
            raise RuntimeError(
                "background recommendation runtime is not running"
            )

        if created_at is None:
            created_at = datetime.now(timezone.utc)

        if (
            created_at.tzinfo is None
            or created_at.utcoffset() is None
        ):
            raise ValueError(
                "created_at must be timezone-aware"
            )

        normalized = tuple(assessments)

        for assessment in normalized:
            if not isinstance(
                assessment,
                BackgroundPriorityAssessment,
            ):
                raise TypeError(
                    "assessments must contain "
                    "BackgroundPriorityAssessment instances"
                )

            if not assessment.context_key.strip():
                raise ValueError(
                    "context_key must be non-empty"
                )

            if assessment.occurrence_count < 1:
                raise ValueError(
                    "occurrence_count must be >= 1"
                )

            if (
                assessment.assessed_at.tzinfo is None
                or assessment.assessed_at.utcoffset() is None
            ):
                raise ValueError(
                    "assessment assessed_at must be timezone-aware"
                )

        recommendations: list[
            BackgroundRecommendation
        ] = []

        for assessment in sorted(
            normalized,
            key=lambda item: (
                item.priority.value,
                item.context_key,
                item.pattern_type.value,
                item.event_ids,
            ),
        ):
            key = (
                assessment.context_key,
                assessment.pattern_type.value,
                assessment.event_ids,
            )

            if key in self._processed_keys:
                continue

            self._processed_keys.add(key)

            recommendation_type = self._recommendation_type(
                assessment
            )

            recommendations.append(
                BackgroundRecommendation(
                    context_key=assessment.context_key,
                    recommendation_type=recommendation_type,
                    priority=assessment.priority,
                    risk_level=assessment.risk_level,
                    event_ids=assessment.event_ids,
                    occurrence_count=assessment.occurrence_count,
                    title=self._title(
                        assessment,
                        recommendation_type,
                    ),
                    reason=assessment.reason,
                    recommended_next_step=self._next_step(
                        assessment,
                        recommendation_type,
                    ),
                    created_at=created_at,
                    requires_human_approval=True,
                    executable=False,
                    metadata={
                        "source": "M37.7",
                        "human_attention": True,
                        "recommendation_only": True,
                        "read_only": True,
                        "executable": False,
                        "requires_human_approval": True,
                    },
                )
            )

        return BackgroundRecommendationResult(
            processed_assessments=len(normalized),
            recommendations_created=len(recommendations),
            recommendations=tuple(recommendations),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.7",
                "recommendation_layer": True,
                "human_attention": True,
                "recommendation_only": True,
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
