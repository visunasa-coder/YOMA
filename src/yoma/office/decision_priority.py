from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
)


@dataclass(frozen=True)
class DecisionPriorityScore:
    """
    M30.4 ranking information for one decision.

    The score is deterministic and advisory-only.
    """

    decision_id: str
    priority: str
    priority_score: float
    confidence_score: float
    intelligence_score: float
    evidence_score: float
    urgency_score: float
    total_score: float
    rank: int = 0

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError(
                "decision_id must not be empty"
            )

        for name in (
            "priority_score",
            "confidence_score",
            "intelligence_score",
            "evidence_score",
            "urgency_score",
            "total_score",
        ):
            value = float(getattr(self, name))

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if self.rank < 0:
            raise ValueError(
                "rank must be non-negative"
            )


@dataclass(frozen=True)
class RankedDecision:
    """
    One ranked DecisionIntelligence item.
    """

    decision: DecisionIntelligence
    score: DecisionPriorityScore


@dataclass(frozen=True)
class DecisionPriorityRanking:
    """
    Complete deterministic ranking result.
    """

    ranked_decisions: tuple[RankedDecision, ...]

    @property
    def decisions(self) -> tuple[DecisionIntelligence, ...]:
        return tuple(
            item.decision
            for item in self.ranked_decisions
        )

    @property
    def scores(self) -> tuple[DecisionPriorityScore, ...]:
        return tuple(
            item.score
            for item in self.ranked_decisions
        )

    @property
    def top_decision(self) -> Optional[DecisionIntelligence]:
        if not self.ranked_decisions:
            return None

        return self.ranked_decisions[0].decision

    @property
    def count(self) -> int:
        return len(self.ranked_decisions)

    @property
    def requires_human_review(self) -> bool:
        return any(
            item.decision.requires_human_approval
            for item in self.ranked_decisions
        )


class DecisionPriorityRanker:
    """
    M30.4 Decision Priority & Ranking.

    Ranking is deterministic and advisory-only.

    Score composition:

        priority       35%
        confidence     20%
        intelligence   20%
        evidence       15%
        urgency        10%

    No autonomous actions are generated.
    """

    _PRIORITY_WEIGHTS = {
        "low": 0.25,
        "normal": 0.50,
        "high": 0.75,
        "critical": 1.00,
    }

    @staticmethod
    def _priority_score(
        decision: DecisionIntelligence,
    ) -> float:
        return DecisionPriorityRanker._PRIORITY_WEIGHTS.get(
            decision.priority.lower(),
            0.50,
        )

    @staticmethod
    def _confidence_score(
        decision: DecisionIntelligence,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(decision.confidence),
            ),
        )

    @staticmethod
    def _intelligence_score(
        decision: DecisionIntelligence,
    ) -> float:
        available = sum(
            (
                bool(
                    decision.current_intelligence_available
                ),
                bool(
                    decision.historical_intelligence_available
                ),
                bool(
                    decision.predictive_intelligence_available
                ),
            )
        )

        return round(
            available / 3.0,
            6,
        )

    @staticmethod
    def _evidence_score(
        decision: DecisionIntelligence,
    ) -> float:
        count = len(decision.evidence)

        if count <= 0:
            return 0.0

        total_weight = sum(
            max(
                0.0,
                min(
                    1.0,
                    float(item.weight),
                ),
            )
            for item in decision.evidence
        )

        # Evidence count saturates at five items.
        count_component = min(
            1.0,
            count / 5.0,
        )

        # Average evidence strength.
        weight_component = min(
            1.0,
            total_weight / max(1, count),
        )

        return round(
            (count_component * 0.40)
            + (weight_component * 0.60),
            6,
        )

    @staticmethod
    def _urgency_score(
        decision: DecisionIntelligence,
    ) -> float:
        """
        Predictive intelligence increases urgency because it
        represents anticipated operational conditions.

        Critical/high priorities already contribute through
        priority_score and are not double-counted here.
        """
        if decision.predictive_intelligence_available:
            return 1.0

        if decision.historical_intelligence_available:
            return 0.70

        if decision.current_intelligence_available:
            return 0.50

        return 0.0

    @classmethod
    def score(
        cls,
        decision: DecisionIntelligence,
    ) -> DecisionPriorityScore:
        if not isinstance(
            decision,
            DecisionIntelligence,
        ):
            raise TypeError(
                "decision must be a DecisionIntelligence"
            )

        priority_score = cls._priority_score(
            decision
        )
        confidence_score = cls._confidence_score(
            decision
        )
        intelligence_score = cls._intelligence_score(
            decision
        )
        evidence_score = cls._evidence_score(
            decision
        )
        urgency_score = cls._urgency_score(
            decision
        )

        total_score = round(
            (priority_score * 0.35)
            + (confidence_score * 0.20)
            + (intelligence_score * 0.20)
            + (evidence_score * 0.15)
            + (urgency_score * 0.10),
            6,
        )

        return DecisionPriorityScore(
            decision_id=decision.decision_id,
            priority=decision.priority,
            priority_score=round(
                priority_score,
                6,
            ),
            confidence_score=round(
                confidence_score,
                6,
            ),
            intelligence_score=round(
                intelligence_score,
                6,
            ),
            evidence_score=round(
                evidence_score,
                6,
            ),
            urgency_score=round(
                urgency_score,
                6,
            ),
            total_score=total_score,
        )

    @classmethod
    def rank(
        cls,
        decisions: Iterable[DecisionIntelligence],
    ) -> DecisionPriorityRanking:
        decisions = tuple(decisions)

        scores = [
            cls.score(decision)
            for decision in decisions
        ]

        combined = list(
            zip(
                decisions,
                scores,
            )
        )

        # Highest score first.
        # Decision ID is the deterministic tie-breaker.
        combined.sort(
            key=lambda item: (
                -item[1].total_score,
                item[0].decision_id,
            )
        )

        ranked = []

        for index, (
            decision,
            score,
        ) in enumerate(combined, start=1):
            ranked.append(
                RankedDecision(
                    decision=decision,
                    score=DecisionPriorityScore(
                        decision_id=score.decision_id,
                        priority=score.priority,
                        priority_score=score.priority_score,
                        confidence_score=score.confidence_score,
                        intelligence_score=score.intelligence_score,
                        evidence_score=score.evidence_score,
                        urgency_score=score.urgency_score,
                        total_score=score.total_score,
                        rank=index,
                    ),
                )
            )

        return DecisionPriorityRanking(
            ranked_decisions=tuple(ranked)
        )

    @classmethod
    def rank_many(
        cls,
        rankings: Iterable[
            Iterable[DecisionIntelligence]
        ],
    ) -> tuple[DecisionPriorityRanking, ...]:
        return tuple(
            cls.rank(decisions)
            for decisions in rankings
        )
