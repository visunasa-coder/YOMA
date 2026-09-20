"""M30.1 unified decision intelligence model.

Combines current, historical, and predictive intelligence into one
advisory decision-intelligence representation.

This module does not execute actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class DecisionIntelligenceEvidence:
    """Evidence supporting a decision-intelligence result."""

    evidence_id: str
    evidence_type: str
    source_id: str
    description: str = ""
    weight: float = 0.0
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if not self.evidence_type:
            raise ValueError("evidence_type is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0 and 1")


@dataclass(frozen=True)
class DecisionIntelligence:
    """Unified advisory decision-intelligence result.

    The object intentionally contains recommendations but no executable
    actions. Human approval is always required.
    """

    decision_id: str
    decision_type: str
    created_at: datetime

    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    system_id: Optional[str] = None

    situation_type: Optional[str] = None

    priority: str = "normal"
    confidence: float = 0.0

    current_intelligence_available: bool = False
    historical_intelligence_available: bool = False
    predictive_intelligence_available: bool = False

    current_decision_ids: Tuple[str, ...] = ()
    historical_context_ids: Tuple[str, ...] = ()
    predictive_context_ids: Tuple[str, ...] = ()

    evidence: Tuple[DecisionIntelligenceEvidence, ...] = ()

    recommendation_type: Optional[str] = None
    recommendation_reason: str = ""

    requires_human_approval: bool = True

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")

        if not self.decision_type:
            raise ValueError("decision_type is required")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.priority not in {
            "low",
            "normal",
            "high",
            "critical",
        }:
            raise ValueError(
                "priority must be low, normal, high, or critical"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "DecisionIntelligence must require human approval"
            )

        if not self.decision_id.startswith("DINT-"):
            raise ValueError(
                "decision_id must use the DINT- prefix"
            )

    @property
    def intelligence_available(self) -> bool:
        return (
            self.current_intelligence_available
            or self.historical_intelligence_available
            or self.predictive_intelligence_available
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def has_current_context(self) -> bool:
        return bool(self.current_decision_ids)

    @property
    def has_historical_context(self) -> bool:
        return bool(self.historical_context_ids)

    @property
    def has_predictive_context(self) -> bool:
        return bool(self.predictive_context_ids)
