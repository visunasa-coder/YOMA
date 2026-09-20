from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from .execution_reconciliation import ExecutionOutcomeReconciliation


VALID_RELIABILITY_LEVELS = {
    "excellent",
    "reliable",
    "mixed",
    "unreliable",
    "insufficient_data",
}


@dataclass(frozen=True)
class ExecutionReliabilityMetrics:
    metric_id: str
    action_type: Optional[str]
    total_executions: int
    achieved_count: int
    partial_count: int
    failed_count: int
    unexpected_count: int
    insufficient_evidence_count: int
    success_rate: float
    partial_rate: float
    failure_rate: float
    unexpected_rate: float
    evidence_quality: float
    human_review_count: int
    reliability_level: str
    reconciliation_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.metric_id:
            raise ValueError("metric_id must not be empty")
        if not self.metric_id.startswith("REL-"):
            raise ValueError("metric_id must start with REL-")

        if self.total_executions < 0:
            raise ValueError("total_executions must be >= 0")

        for name, value in (
            ("achieved_count", self.achieved_count),
            ("partial_count", self.partial_count),
            ("failed_count", self.failed_count),
            ("unexpected_count", self.unexpected_count),
            (
                "insufficient_evidence_count",
                self.insufficient_evidence_count,
            ),
            ("human_review_count", self.human_review_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0")

        for name, value in (
            ("success_rate", self.success_rate),
            ("partial_rate", self.partial_rate),
            ("failure_rate", self.failure_rate),
            ("unexpected_rate", self.unexpected_rate),
            ("evidence_quality", self.evidence_quality),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

        if self.reliability_level not in VALID_RELIABILITY_LEVELS:
            raise ValueError(
                f"invalid reliability level: {self.reliability_level}"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "execution reliability intelligence must require human approval"
            )

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_review(self) -> bool:
        return self.reliability_level in {
            "mixed",
            "unreliable",
            "insufficient_data",
        }


@dataclass(frozen=True)
class ExecutionReliabilityIntelligence:
    intelligence_id: str
    metrics: ExecutionReliabilityMetrics
    action_types: Tuple[str, ...] = ()
    failure_patterns: Tuple[str, ...] = ()
    observations: Tuple[Mapping[str, Any], ...] = ()
    recommendation: str = ""
    confidence: float = 0.0
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.intelligence_id:
            raise ValueError("intelligence_id must not be empty")
        if not self.intelligence_id.startswith("RELI-"):
            raise ValueError("intelligence_id must start with RELI-")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if not self.requires_human_approval:
            raise ValueError(
                "execution reliability intelligence must require human approval"
            )

    @property
    def reliability_level(self) -> str:
        return self.metrics.reliability_level

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_review(self) -> bool:
        return (
            self.metrics.requires_review
            or self.metrics.human_review_count > 0
        )


class ExecutionReliabilityIntelligenceEngine:
    """
    Analytical reliability intelligence over M32.7 reconciliations.

    This engine never executes, retries, modifies, or autonomously
    corrects an action.
    """

    def __init__(self) -> None:
        self._intelligence: dict[
            str, ExecutionReliabilityIntelligence
        ] = {}

    @property
    def intelligence(
        self,
    ) -> Tuple[ExecutionReliabilityIntelligence, ...]:
        return tuple(self._intelligence.values())

    def get(
        self,
        intelligence_id: str,
    ) -> Optional[ExecutionReliabilityIntelligence]:
        return self._intelligence.get(intelligence_id)

    @staticmethod
    def _validate(
        reconciliations,
    ) -> Tuple[ExecutionOutcomeReconciliation, ...]:
        values = tuple(reconciliations)

        for reconciliation in values:
            if not isinstance(
                reconciliation,
                ExecutionOutcomeReconciliation,
            ):
                raise TypeError(
                    "all reconciliations must be "
                    "ExecutionOutcomeReconciliation instances"
                )

        return values

    @staticmethod
    def _level(
        total: int,
        achieved: int,
        partial: int,
        failed: int,
        unexpected: int,
        insufficient: int,
    ) -> str:
        if total == 0:
            return "insufficient_data"

        success_rate = achieved / total
        failure_rate = failed / total
        unexpected_rate = unexpected / total
        evidence_quality = (total - insufficient) / total

        if (
            success_rate >= 0.90
            and failure_rate <= 0.05
            and unexpected_rate <= 0.05
            and evidence_quality >= 0.90
        ):
            return "excellent"

        if (
            success_rate >= 0.75
            and failure_rate <= 0.20
            and unexpected_rate <= 0.10
            and evidence_quality >= 0.75
        ):
            return "reliable"

        if failure_rate >= 0.40 or unexpected_rate >= 0.25:
            return "unreliable"

        return "mixed"

    @staticmethod
    def _recommendation(level: str) -> str:
        recommendations = {
            "excellent": (
                "Execution reliability is consistently strong; "
                "continue human-governed execution."
            ),
            "reliable": (
                "Execution reliability is generally strong; "
                "continue monitoring exceptions under human review."
            ),
            "mixed": (
                "Execution reliability is mixed; "
                "review partial outcomes and recurring exceptions."
            ),
            "unreliable": (
                "Execution reliability is poor; "
                "human review should examine recurring failures "
                "before further execution decisions."
            ),
            "insufficient_data": (
                "Insufficient execution evidence is available "
                "to establish reliability."
            ),
        }

        return recommendations[level]

    def analyze(
        self,
        reconciliations,
        *,
        action_type: Optional[str] = None,
    ) -> ExecutionReliabilityIntelligence:
        values = self._validate(reconciliations)

        if action_type is not None:
            if not action_type:
                raise ValueError("action_type must not be empty")

            values = tuple(
                item
                for item in values
                if item.action_type == action_type
            )

        action_types = tuple(
            sorted({item.action_type for item in values})
        )

        achieved = sum(
            item.status == "achieved"
            for item in values
        )
        partial = sum(
            item.status == "partially_achieved"
            for item in values
        )
        failed = sum(
            item.status == "failed"
            for item in values
        )
        unexpected = sum(
            item.status == "unexpected"
            for item in values
        )
        insufficient = sum(
            item.status == "insufficient_evidence"
            for item in values
        )

        total = len(values)

        if total:
            success_rate = achieved / total
            partial_rate = partial / total
            failure_rate = failed / total
            unexpected_rate = unexpected / total
            evidence_quality = (total - insufficient) / total
        else:
            success_rate = 0.0
            partial_rate = 0.0
            failure_rate = 0.0
            unexpected_rate = 0.0
            evidence_quality = 0.0

        human_review_count = sum(
            item.requires_review
            for item in values
        )

        level = self._level(
            total,
            achieved,
            partial,
            failed,
            unexpected,
            insufficient,
        )

        reconciliation_ids = tuple(
            item.reconciliation_id
            for item in values
        )

        failure_patterns = tuple(
            sorted(
                {
                    f"{item.action_type}:{item.status}"
                    for item in values
                    if item.status
                    in {
                        "failed",
                        "unexpected",
                        "partially_achieved",
                    }
                }
            )
        )

        observations = tuple(
            {
                "reconciliation_id": item.reconciliation_id,
                "action_type": item.action_type,
                "status": item.status,
                "execution_status": item.execution_status,
                "observed_outcome_status": item.observed_outcome_status,
                "expected_event_count": item.expected_event_count,
                "observed_event_count": item.observed_event_count,
                "requires_review": item.requires_review,
            }
            for item in values
        )

        metric_scope = action_type or "ALL"
        metric_id = f"REL-{metric_scope}"

        metrics = ExecutionReliabilityMetrics(
            metric_id=metric_id,
            action_type=action_type,
            total_executions=total,
            achieved_count=achieved,
            partial_count=partial,
            failed_count=failed,
            unexpected_count=unexpected,
            insufficient_evidence_count=insufficient,
            success_rate=round(success_rate, 6),
            partial_rate=round(partial_rate, 6),
            failure_rate=round(failure_rate, 6),
            unexpected_rate=round(unexpected_rate, 6),
            evidence_quality=round(evidence_quality, 6),
            human_review_count=human_review_count,
            reliability_level=level,
            reconciliation_ids=reconciliation_ids,
            requires_human_approval=True,
        )

        confidence = (
            round(
                (
                    evidence_quality
                    * min(total / 5.0, 1.0)
                ),
                6,
            )
            if total
            else 0.0
        )

        result = ExecutionReliabilityIntelligence(
            intelligence_id=f"RELI-{metric_scope}",
            metrics=metrics,
            action_types=action_types,
            failure_patterns=failure_patterns,
            observations=observations,
            recommendation=self._recommendation(level),
            confidence=confidence,
            requires_human_approval=True,
        )

        self._intelligence[result.intelligence_id] = result
        return result

    def analyze_many(
        self,
        reconciliations,
        *,
        action_types: Tuple[str, ...] = (),
    ) -> Tuple[ExecutionReliabilityIntelligence, ...]:
        values = self._validate(reconciliations)

        if not action_types:
            return (self.analyze(values),)

        return tuple(
            self.analyze(values, action_type=action_type)
            for action_type in action_types
        )
