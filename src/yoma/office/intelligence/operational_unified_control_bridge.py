"""M34.3 Operational Decision ? Unified Control Bridge.

Bridges the existing Operational Unified Runtime into the canonical
Decision Intelligence runtime and then into the M34.2 Unified Control
Runtime.

Composition only:
    OperationalUnifiedResult
        -> DecisionIntelligenceRuntime
        -> UnifiedControlRuntime

No execution, approval bypass, or duplicate intelligence/control logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Tuple, Any

from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceResult,
    DecisionIntelligenceRuntime,
)
from yoma.office.unified_control_runtime import (
    UnifiedControlRuntime,
    UnifiedControlRuntimeResult,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedResult,
)


@dataclass(frozen=True)
class OperationalUnifiedControlBridgeResult:
    """M34.3 bridge result."""

    operational: OperationalUnifiedResult
    decision_intelligence: DecisionIntelligenceResult
    unified_control: Tuple[
        UnifiedControlRuntimeResult, ...
    ]

    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError(
                "M34.3 must require human approval"
            )

        if self.executable:
            raise ValueError(
                "M34.3 bridge cannot be executable"
            )

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class OperationalUnifiedControlBridge:
    """M34.3 operational decision to unified control bridge."""

    def __init__(
        self,
        *,
        decision_runtime: Optional[
            DecisionIntelligenceRuntime
        ] = None,
        unified_control_runtime: Optional[
            UnifiedControlRuntime
        ] = None,
    ) -> None:
        self.decision_runtime = (
            decision_runtime
            or DecisionIntelligenceRuntime()
        )

        self.unified_control_runtime = (
            unified_control_runtime
            or UnifiedControlRuntime()
        )

        self._last_result: (
            OperationalUnifiedControlBridgeResult | None
        ) = None

    @property
    def last_result(
        self,
    ) -> OperationalUnifiedControlBridgeResult | None:
        return self._last_result

    def process(
        self,
        operational_result: OperationalUnifiedResult,
        *,
        scheduled_at: datetime,
        created_at: datetime,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> OperationalUnifiedControlBridgeResult:
        """Bridge operational decisions through canonical control."""

        if not isinstance(
            operational_result,
            OperationalUnifiedResult,
        ):
            raise TypeError(
                "operational_result must be an "
                "OperationalUnifiedResult"
            )

        if scheduled_at.tzinfo is None:
            raise ValueError(
                "scheduled_at must be timezone-aware"
            )

        if created_at.tzinfo is None:
            raise ValueError(
                "created_at must be timezone-aware"
            )

        decision_result = self.decision_runtime.analyze(
            current_decisions=operational_result.decisions,
        )

        control_results = tuple(
            self.unified_control_runtime.analyze(
                decision,
                scheduled_at=scheduled_at,
                created_at=created_at,
                metadata=metadata,
            )
            for decision in decision_result.decisions
        )

        result = OperationalUnifiedControlBridgeResult(
            operational=operational_result,
            decision_intelligence=decision_result,
            unified_control=control_results,
            requires_human_approval=True,
            executable=False,
            metadata=dict(metadata or {}),
        )

        self._last_result = result
        return result

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True


__all__ = [
    "OperationalUnifiedControlBridge",
    "OperationalUnifiedControlBridgeResult",
]
