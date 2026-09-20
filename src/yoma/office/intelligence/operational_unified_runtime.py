from __future__ import annotations

from dataclasses import dataclass

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_pattern_decision_runtime import (
    OperationalPatternDecisionRuntime,
)
from yoma.office.intelligence.operational_pattern_runtime import (
    OperationalPatternRuntime,
)
from yoma.office.intelligence.operational_runtime import (
    OperationalIntelligenceRuntime,
)
from yoma.office.intelligence.operational_situation_context_runtime import (
    OperationalSituationContextRuntime,
)
from yoma.office.intelligence.operational_situation_runtime import (
    OperationalSituationRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.operations import (
    OperationalEvent,
    OperationalPattern,
    OperationalSituation,
    OperationalSituationContext,
    OperationalSignal,
)


@dataclass(frozen=True)
class OperationalUnifiedResult:
    events: tuple[OperationalEvent, ...]
    signals: tuple[OperationalSignal, ...]
    situations: tuple[OperationalSituation, ...]
    contexts: tuple[OperationalSituationContext, ...]
    patterns: tuple[OperationalPattern, ...]
    decisions: tuple[DecisionContext, ...]


class OperationalUnifiedRuntime:
    """
    Unified end-to-end operational intelligence runtime.

    Orchestrates the existing M25 runtime layers:

        Event
          -> Signal
          -> Situation
          -> Organization Context
          -> Pattern
          -> Decision Context

    The runtime composes existing components and does not duplicate
    intelligence, correlation, context-resolution, pattern, or
    decision logic.

    Decisions remain advisory and retain the existing
    human-approval boundary.
    """

    def __init__(
        self,
        *,
        intelligence_engine: OperationalIntelligenceEngine,
        graph: OrganizationGraph,
    ) -> None:
        if not isinstance(
            intelligence_engine,
            OperationalIntelligenceEngine,
        ):
            raise TypeError(
                "intelligence_engine must be an "
                "OperationalIntelligenceEngine"
            )

        if not isinstance(graph, OrganizationGraph):
            raise TypeError("graph must be an OrganizationGraph")

        self.intelligence_runtime = OperationalIntelligenceRuntime(
            intelligence_engine=intelligence_engine,
        )

        self.situation_runtime = OperationalSituationRuntime()

        self.context_runtime = OperationalSituationContextRuntime(
            graph=graph,
        )

        self.pattern_runtime = OperationalPatternRuntime(
            graph=graph,
        )

        self.decision_runtime = OperationalPatternDecisionRuntime()

        self._last_result: OperationalUnifiedResult | None = None

    @property
    def last_result(self) -> OperationalUnifiedResult | None:
        return self._last_result

    def process(
        self,
        events,
    ) -> OperationalUnifiedResult:
        intelligence_result = self.intelligence_runtime.process(
            events
        )

        situation_result = self.situation_runtime.process(
            intelligence_result
        )

        context_result = self.context_runtime.process(
            situation_result
        )

        pattern_result = self.pattern_runtime.process(
            context_result
        )

        decision_result = self.decision_runtime.process(
            pattern_result,
            intelligence_result.signals,
        )

        result = OperationalUnifiedResult(
            events=intelligence_result.events,
            signals=intelligence_result.signals,
            situations=situation_result.situations,
            contexts=context_result.contexts,
            patterns=pattern_result.patterns,
            decisions=decision_result.decisions,
        )

        self._last_result = result
        return result
