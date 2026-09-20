from __future__ import annotations

from dataclasses import dataclass

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision.pattern import OperationalPatternDecisionAdapter
from yoma.office.intelligence.operational_pattern_runtime import (
    OperationalPatternResult,
)
from yoma.office.operations import (
    OperationalPattern,
    OperationalSignal,
)


@dataclass(frozen=True)
class OperationalPatternDecisionResult:
    patterns: tuple[OperationalPattern, ...]
    decisions: tuple[DecisionContext, ...]


class OperationalPatternDecisionRuntime:
    """
    Runtime coordinator for converting operational patterns into
    advisory decision contexts.

    The runtime composes the existing
    OperationalPatternDecisionAdapter. It does not execute actions
    and preserves the existing human-approval boundary.
    """

    def __init__(
        self,
        *,
        adapter: OperationalPatternDecisionAdapter | None = None,
    ) -> None:
        self.adapter = (
            adapter
            if adapter is not None
            else OperationalPatternDecisionAdapter()
        )
        self._last_result: OperationalPatternDecisionResult | None = None

    @property
    def last_result(
        self,
    ) -> OperationalPatternDecisionResult | None:
        return self._last_result

    def process(
        self,
        pattern_result: OperationalPatternResult,
        signals: tuple[OperationalSignal, ...]
        | list[OperationalSignal],
    ) -> OperationalPatternDecisionResult:
        if not isinstance(
            pattern_result,
            OperationalPatternResult,
        ):
            raise TypeError(
                "pattern_result must be an "
                "OperationalPatternResult"
            )

        signal_tuple = tuple(signals)

        decisions = tuple(
            self.adapter.adapt(
                pattern,
                signal_tuple,
            )
            for pattern in pattern_result.patterns
        )

        result = OperationalPatternDecisionResult(
            patterns=tuple(pattern_result.patterns),
            decisions=decisions,
        )

        self._last_result = result
        return result
