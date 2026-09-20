from __future__ import annotations

from typing import Iterable

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.operations import (
    OperationalPattern,
    OperationalSignal,
)


class OperationalPatternDecisionAdapter:
    """
    Converts an OperationalPattern into an advisory DecisionContext.

    The existing DecisionContext contract remains signal-based.
    The pattern therefore uses one of its source signals as a
    deterministic decision anchor while preserving the complete
    pattern as recommendation metadata.

    No action is automatically generated.
    """

    def adapt(
        self,
        pattern: OperationalPattern,
        signals: Iterable[OperationalSignal],
    ) -> DecisionContext:
        if not isinstance(pattern, OperationalPattern):
            raise TypeError(
                "pattern must be an OperationalPattern"
            )

        signal_map = {}

        for signal in signals:
            if not isinstance(signal, OperationalSignal):
                raise TypeError(
                    "signals must contain OperationalSignal objects"
                )

            if signal.signal_id in signal_map:
                raise ValueError(
                    f"Duplicate signal_id: {signal.signal_id}"
                )

            signal_map[signal.signal_id] = signal

        if not pattern.signal_ids:
            raise ValueError(
                "pattern must contain at least one signal_id"
            )

        missing = [
            signal_id
            for signal_id in pattern.signal_ids
            if signal_id not in signal_map
        ]

        if missing:
            raise ValueError(
                "Pattern references unknown signals: "
                + ", ".join(sorted(missing))
            )

        anchor_id = sorted(pattern.signal_ids)[0]
        anchor = signal_map[anchor_id]

        recommendation = {
            "type": "operational_pattern_review",
            "reason": (
                "Cross-situation operational pattern requires "
                "human review."
            ),
            "pattern_id": pattern.pattern_id,
            "pattern_type": pattern.pattern_type,
            "correlation_dimension": pattern.correlation_dimension,
            "correlation_id": pattern.correlation_id,
            "situation_ids": pattern.situation_ids,
            "signal_ids": pattern.signal_ids,
            "evidence_event_ids": pattern.evidence_event_ids,
            "severity": pattern.severity,
            "score": pattern.score,
        }

        return DecisionContext(
            signal=anchor,
            recommendations=(recommendation,),
            actions=(),
            requires_human_approval=True,
        )
