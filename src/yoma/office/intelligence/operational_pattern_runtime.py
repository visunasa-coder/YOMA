from __future__ import annotations

from dataclasses import dataclass

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.operations import (
    OperationalPattern,
    OperationalPatternCorrelator,
    OperationalSituationContext,
)


@dataclass(frozen=True)
class OperationalPatternResult:
    contexts: tuple[OperationalSituationContext, ...]
    patterns: tuple[OperationalPattern, ...]


class OperationalPatternRuntime:
    """
    Runtime coordinator for deriving higher-level operational
    patterns from explicitly resolved situation contexts.

    The runtime composes OrganizationGraph validation and the
    existing OperationalPatternCorrelator. It performs no
    free-text inference and does not execute actions.
    """

    def __init__(
        self,
        *,
        graph: OrganizationGraph,
        pattern_correlator: OperationalPatternCorrelator | None = None,
    ) -> None:
        if not isinstance(graph, OrganizationGraph):
            raise TypeError("graph must be an OrganizationGraph")

        self.graph = graph
        self.pattern_correlator = (
            pattern_correlator
            if pattern_correlator is not None
            else OperationalPatternCorrelator()
        )
        self._last_result: OperationalPatternResult | None = None

    @property
    def last_result(self) -> OperationalPatternResult | None:
        return self._last_result

    def process(
        self,
        context_result,
    ) -> OperationalPatternResult:
        from yoma.office.intelligence.operational_situation_context_runtime import (
            OperationalSituationContextResult,
        )

        if not isinstance(
            context_result,
            OperationalSituationContextResult,
        ):
            raise TypeError(
                "context_result must be an "
                "OperationalSituationContextResult"
            )

        contexts = tuple(context_result.contexts)

        patterns = self.pattern_correlator.correlate(
            list(contexts)
        )

        result = OperationalPatternResult(
            contexts=contexts,
            patterns=tuple(patterns),
        )

        self._last_result = result
        return result
