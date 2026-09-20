from __future__ import annotations

from dataclasses import dataclass

from yoma.office.intelligence.operational_runtime import (
    OperationalIntelligenceResult,
)
from yoma.office.operations import (
    OperationalSituation,
    OperationalSituationCorrelator,
)


@dataclass(frozen=True)
class OperationalSituationResult:
    events: tuple
    signals: tuple
    situations: tuple[OperationalSituation, ...]


class OperationalSituationRuntime:
    """
    Extends operational intelligence processing with situation
    correlation.

    The runtime composes the existing intelligence result and
    OperationalSituationCorrelator. It does not duplicate signal
    generation or situation correlation rules.
    """

    def __init__(
        self,
        *,
        situation_correlator: OperationalSituationCorrelator | None = None,
    ) -> None:
        self.situation_correlator = (
            situation_correlator
            if situation_correlator is not None
            else OperationalSituationCorrelator()
        )
        self._last_result: OperationalSituationResult | None = None

    @property
    def last_result(self) -> OperationalSituationResult | None:
        return self._last_result

    def process(
        self,
        intelligence_result: OperationalIntelligenceResult,
    ) -> OperationalSituationResult:
        if not isinstance(
            intelligence_result,
            OperationalIntelligenceResult,
        ):
            raise TypeError(
                "intelligence_result must be an "
                "OperationalIntelligenceResult"
            )

        situations = self.situation_correlator.correlate(
            list(intelligence_result.signals)
        )

        result = OperationalSituationResult(
            events=intelligence_result.events,
            signals=intelligence_result.signals,
            situations=tuple(situations),
        )

        self._last_result = result
        return result
