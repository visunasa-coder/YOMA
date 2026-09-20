from __future__ import annotations

from dataclasses import dataclass

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.operations import (
    OperationalSituation,
    OperationalSituationContext,
    OperationalSituationContextResolver,
)


@dataclass(frozen=True)
class OperationalSituationContextResult:
    situations: tuple[OperationalSituation, ...]
    contexts: tuple[OperationalSituationContext, ...]


class OperationalSituationContextRuntime:
    """
    Runtime coordinator for resolving explicit organizational context
    for operational situations.

    The runtime composes the existing OrganizationGraph and
    OperationalSituationContextResolver. It performs no free-text
    inference and does not mutate organizational data.
    """

    def __init__(
        self,
        *,
        graph: OrganizationGraph,
    ) -> None:
        if not isinstance(graph, OrganizationGraph):
            raise TypeError("graph must be an OrganizationGraph")

        self.graph = graph
        self.resolver = OperationalSituationContextResolver(graph)
        self._last_result: OperationalSituationContextResult | None = None

    @property
    def last_result(self) -> OperationalSituationContextResult | None:
        return self._last_result

    def process(
        self,
        situation_result,
    ) -> OperationalSituationContextResult:
        from yoma.office.intelligence.operational_situation_runtime import (
            OperationalSituationResult,
        )

        if not isinstance(
            situation_result,
            OperationalSituationResult,
        ):
            raise TypeError(
                "situation_result must be an "
                "OperationalSituationResult"
            )

        situations = tuple(situation_result.situations)

        contexts = tuple(
            self.resolver.resolve(situation)
            for situation in situations
        )

        result = OperationalSituationContextResult(
            situations=situations,
            contexts=contexts,
        )

        self._last_result = result
        return result
