"""M37.8 Background Intelligence Runtime.

Composes M37.1 through M37.7 into one governed background
intelligence pipeline.

Pipeline:

Event
 -> Monitor
 -> Eligibility
 -> Condition
 -> Context
 -> Pattern
 -> Risk/Priority
 -> Recommendation

This runtime:
- does not create a second event bus
- does not execute actions
- does not grant authorization
- preserves human approval requirements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from .background_condition import BackgroundConditionRuntime
from .background_context import BackgroundContextRuntime
from .background_intelligence import (
    BackgroundEvent,
    BackgroundIntelligenceState,
    BackgroundIntelligenceRuntime,
)
from .background_pattern import BackgroundPatternRuntime
from .background_priority import BackgroundPriorityRuntime
from .background_recommendation import (
    BackgroundRecommendation,
    BackgroundRecommendationRuntime,
)
from .background_trigger import BackgroundTriggerRuntime


@dataclass(frozen=True)
class BackgroundIntelligenceRuntimeResult:
    """Complete result of one background intelligence cycle."""

    processed_events: int
    detected_events: int
    eligible_events: int
    detected_conditions: int
    accumulated_observations: int
    detected_patterns: int
    assessed_patterns: int
    recommendations_created: int

    recommendations: tuple[
        BackgroundRecommendation, ...
    ]

    state: BackgroundIntelligenceState

    read_only: bool = True
    executable: bool = False
    requires_human_approval: bool = True

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


class UnifiedBackgroundIntelligenceRuntime:
    """M37.8 governed background intelligence composition runtime."""

    def __init__(
        self,
        *,
        event_types: set[str] | frozenset[str] | None = None,
        source_systems: set[str] | frozenset[str] | None = None,
        max_observations_per_context: int = 10,
        repetition_threshold: int = 3,
        escalation_threshold: int = 2,
        critical_threshold: int = 2,
        high_occurrence_threshold: int = 5,
        urgent_occurrence_threshold: int = 5,
    ) -> None:
        self.monitor = BackgroundIntelligenceRuntime(
            event_types=event_types
        )

        self.trigger = BackgroundTriggerRuntime(
            event_types=event_types,
            source_systems=source_systems,
        )

        self.condition = BackgroundConditionRuntime()

        self.context = BackgroundContextRuntime(
            max_observations_per_context=(
                max_observations_per_context
            )
        )

        self.pattern = BackgroundPatternRuntime(
            repetition_threshold=repetition_threshold,
            escalation_threshold=escalation_threshold,
            critical_threshold=critical_threshold,
        )

        self.priority = BackgroundPriorityRuntime(
            high_occurrence_threshold=(
                high_occurrence_threshold
            ),
            urgent_occurrence_threshold=(
                urgent_occurrence_threshold
            ),
        )

        self.recommendation = (
            BackgroundRecommendationRuntime()
        )

        self._state = BackgroundIntelligenceState.STOPPED

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
        """Start the complete background intelligence pipeline."""

        if self.running:
            return

        self.monitor.start()
        self.trigger.start()
        self.condition.start()
        self.context.start()
        self.pattern.start()
        self.priority.start()
        self.recommendation.start()

        self._state = BackgroundIntelligenceState.RUNNING

    def stop(self) -> None:
        """Stop the complete background intelligence pipeline."""

        if not self.running:
            return

        self.recommendation.stop()
        self.priority.stop()
        self.pattern.stop()
        self.context.stop()
        self.condition.stop()
        self.trigger.stop()
        self.monitor.stop()

        self._state = BackgroundIntelligenceState.STOPPED

    def reset(self) -> None:
        """Reset all pipeline-level accumulated state."""

        self.recommendation.reset()
        self.priority.reset()
        self.pattern.reset()
        self.context.reset()
        self.condition.reset()
        self.trigger.reset()
        self.monitor.reset()

    def process(
        self,
        events: tuple[
            BackgroundEvent, ...
        ] | list[BackgroundEvent],
        *,
        occurred_at: datetime | None = None,
    ) -> BackgroundIntelligenceRuntimeResult:
        """Run one complete background intelligence cycle."""

        if not self.running:
            raise RuntimeError(
                "background intelligence runtime is not running"
            )

        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)

        if (
            occurred_at.tzinfo is None
            or occurred_at.utcoffset() is None
        ):
            raise ValueError(
                "occurred_at must be timezone-aware"
            )

        normalized = tuple(events)

        # M37.1
        monitor_result = self.monitor.process(
            normalized,
            detected_at=occurred_at,
        )

        # M37.2
        trigger_result = self.trigger.evaluate(
            tuple(
                BackgroundEvent(
                    event_id=item.event_id,
                    event_type=item.event_type,
                    occurred_at=item.occurred_at,
                    source_system=item.source_system,
                    entity_id=item.entity_id,
                    metadata=item.metadata,
                )
                for item in normalized
            ),
            evaluated_at=occurred_at,
        )

        # M37.3
        condition_result = self.condition.detect(
            trigger_result.decisions,
            detected_at=occurred_at,
        )

        # M37.4
        context_result = self.context.accumulate(
            condition_result.conditions,
            observed_at=occurred_at,
        )

        # M37.5
        pattern_result = self.pattern.recognize(
            context_result.contexts,
            detected_at=occurred_at,
        )

        # M37.6
        priority_result = self.priority.assess(
            pattern_result.patterns,
            assessed_at=occurred_at,
        )

        # M37.7
        recommendation_result = (
            self.recommendation.recommend(
                priority_result.assessments,
                created_at=occurred_at,
            )
        )

        return BackgroundIntelligenceRuntimeResult(
            # M37.8 reports newly processed events for the
            # integrated cycle. M37.1 may receive duplicate
            # input events but suppress them from detection.
            processed_events=monitor_result.detected_events,
            detected_events=monitor_result.detected_events,
            eligible_events=trigger_result.eligible_events,
            detected_conditions=(
                condition_result.detected_conditions
            ),
            accumulated_observations=(
                context_result.accumulated_observations
            ),
            detected_patterns=(
                pattern_result.detected_patterns
            ),
            assessed_patterns=(
                priority_result.assessed_patterns
            ),
            recommendations_created=(
                recommendation_result.recommendations_created
            ),
            recommendations=(
                recommendation_result.recommendations
            ),
            state=self._state,
            read_only=True,
            executable=False,
            requires_human_approval=True,
            metadata={
                "source": "M37.8",
                "background_intelligence": True,
                "pipeline": (
                    "M37.1>M37.2>M37.3>M37.4>"
                    "M37.5>M37.6>M37.7"
                ),
                "read_only": True,
                "executable": False,
                "requires_human_approval": True,
            },
        )
