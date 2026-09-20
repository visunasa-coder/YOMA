from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from yoma.office.operations import OperationalEvent, OperationalSignal


SignalRule = Callable[[list[OperationalEvent]], list[OperationalSignal]]


class OperationalIntelligenceEngine:
    """
    Provider-neutral intelligence orchestration layer.

    Rules consume normalized OperationalEvents and produce
    OperationalSignals. The engine does not directly execute
    employment, disciplinary, financial, or security actions.
    """

    def __init__(self) -> None:
        self._rules: dict[str, SignalRule] = {}

    def register_rule(self, name: str, rule: SignalRule) -> None:
        if not name or not name.strip():
            raise ValueError("Rule name is required")

        if name in self._rules:
            raise ValueError(f"Rule already registered: {name}")

        self._rules[name] = rule

    def unregister_rule(self, name: str) -> bool:
        return self._rules.pop(name, None) is not None

    def list_rules(self) -> list[str]:
        return list(self._rules)

    def analyze(
        self,
        events: list[OperationalEvent],
    ) -> list[OperationalSignal]:
        signals: list[OperationalSignal] = []

        for rule in self._rules.values():
            produced = rule(events)

            for signal in produced:
                if not isinstance(signal, OperationalSignal):
                    raise TypeError(
                        "Intelligence rules must return OperationalSignal objects"
                    )

                signals.append(signal)

        return signals

    @staticmethod
    def group_by_user(
        events: list[OperationalEvent],
    ) -> dict[str, list[OperationalEvent]]:
        grouped: dict[str, list[OperationalEvent]] = defaultdict(list)

        for event in events:
            if event.user_id:
                grouped[event.user_id].append(event)

        return dict(grouped)

    @staticmethod
    def group_by_system(
        events: list[OperationalEvent],
    ) -> dict[str, list[OperationalEvent]]:
        grouped: dict[str, list[OperationalEvent]] = defaultdict(list)

        for event in events:
            if event.system_id:
                grouped[event.system_id].append(event)

        return dict(grouped)
