from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from yoma.office.operations import OperationalAction, OperationalSignal


@dataclass(frozen=True)
class DecisionContext:
    signal: OperationalSignal
    recommendations: tuple[dict[str, Any], ...] = ()
    actions: tuple[OperationalAction, ...] = ()
    requires_human_approval: bool = True


class DecisionOrchestrator:
    """
    Converts intelligence signals into controlled decision contexts.

    The orchestrator does not execute employment, disciplinary,
    financial, or security-sensitive actions automatically.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}

    def register_handler(self, signal_type: str, handler: Any) -> None:
        if not signal_type or not signal_type.strip():
            raise ValueError("signal_type is required")

        if signal_type in self._handlers:
            raise ValueError(
                f"Decision handler already registered: {signal_type}"
            )

        self._handlers[signal_type] = handler

    def list_handlers(self) -> list[str]:
        return list(self._handlers)

    def evaluate(
        self,
        signal: OperationalSignal,
    ) -> DecisionContext:
        handler = self._handlers.get(signal.signal_type)

        if handler is None:
            return DecisionContext(signal=signal)

        result = handler(signal)

        if not isinstance(result, DecisionContext):
            raise TypeError(
                "Decision handlers must return DecisionContext"
            )

        return result

    def evaluate_many(
        self,
        signals: list[OperationalSignal],
    ) -> list[DecisionContext]:
        return [self.evaluate(signal) for signal in signals]
