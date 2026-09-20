from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from yoma.office.operations.situation_context import (
    OperationalSituationContext,
)


@dataclass(frozen=True)
class OperationalPattern:
    """
    Higher-level operational pattern derived from multiple
    OperationalSituationContext objects.

    Patterns are descriptive and advisory. They do not make
    employment, disciplinary, financial, or security decisions.
    """

    pattern_id: str
    pattern_type: str
    detected_at: datetime
    correlation_dimension: str
    correlation_id: str
    situation_ids: tuple[str, ...] = ()
    signal_ids: tuple[str, ...] = ()
    evidence_event_ids: tuple[str, ...] = ()
    severity: str = "info"
    score: float = 0.0


class OperationalPatternCorrelator:
    """
    Correlates operational situations using explicit organizational
    context.

    Only the strongest explicit shared organizational dimension is
    emitted for a group of situations. This avoids redundant parent
    patterns such as TEAM + DEPARTMENT + ORGANIZATION for the same
    situations.

    No names, free text, roles, or inferred relationships are used.
    """

    _DIMENSION_PRIORITY = (
        "team",
        "department",
        "location",
        "organization",
        "system",
    )

    def correlate(
        self,
        contexts: list[OperationalSituationContext],
    ) -> list[OperationalPattern]:
        if not contexts:
            return []

        patterns: list[OperationalPattern] = []

        for dimension in self._DIMENSION_PRIORITY:
            groups: dict[str, list[OperationalSituationContext]] = {}

            for context in contexts:
                correlation_id = self._correlation_id(
                    context,
                    dimension,
                )

                if correlation_id is not None:
                    groups.setdefault(
                        correlation_id,
                        [],
                    ).append(context)

            for correlation_id, group in groups.items():
                unique_situations = {
                    context.situation_id
                    for context in group
                }

                if len(unique_situations) < 2:
                    continue

                # Organization-level correlation is only useful when
                # no more specific organizational dimension connects
                # the same situations.
                if dimension == "organization":
                    has_more_specific = any(
                        pattern.situation_ids == tuple(
                            sorted(unique_situations)
                        )
                        and pattern.correlation_dimension
                        in {
                            "team",
                            "department",
                            "location",
                        }
                        for pattern in patterns
                    )

                    if has_more_specific:
                        continue

                patterns.append(
                    self._build_pattern(
                        dimension,
                        correlation_id,
                        group,
                    )
                )

        return sorted(
            patterns,
            key=lambda pattern: (
                self._dimension_rank(
                    pattern.correlation_dimension
                ),
                pattern.correlation_id,
                pattern.situation_ids,
            ),
        )

    @staticmethod
    def _correlation_id(
        context: OperationalSituationContext,
        dimension: str,
    ) -> str | None:
        if dimension == "system":
            return context.situation.system_id

        node = getattr(context, dimension, None)

        if node is None:
            return None

        return node.node_id

    @classmethod
    def _dimension_rank(cls, dimension: str) -> int:
        return cls._DIMENSION_PRIORITY.index(dimension)

    @staticmethod
    def _build_pattern(
        dimension: str,
        correlation_id: str,
        contexts: list[OperationalSituationContext],
    ) -> OperationalPattern:
        ordered = sorted(
            contexts,
            key=lambda context: context.situation_id,
        )

        situations = {
            context.situation_id: context.situation
            for context in ordered
        }

        situation_ids = tuple(sorted(situations))

        signal_ids = tuple(
            sorted(
                {
                    signal_id
                    for situation in situations.values()
                    for signal_id in situation.signal_ids
                }
            )
        )

        evidence_event_ids = tuple(
            sorted(
                {
                    event_id
                    for situation in situations.values()
                    for event_id in situation.evidence_event_ids
                }
            )
        )

        severity_rank = {
            "info": 0,
            "warning": 1,
            "high": 2,
            "critical": 3,
        }

        severity = max(
            (
                situation.severity
                for situation in situations.values()
            ),
            key=lambda value: severity_rank.get(value, -1),
        )

        score = (
            sum(
                situation.score
                for situation in situations.values()
            )
            / len(situations)
        )

        detected_at = max(
            situation.detected_at
            for situation in situations.values()
        )

        pattern_id = (
            f"PAT-{dimension.upper()}-{correlation_id}-"
            f"{'-'.join(situation_ids)}"
        )

        return OperationalPattern(
            pattern_id=pattern_id,
            pattern_type="cross_situation",
            detected_at=detected_at,
            correlation_dimension=dimension,
            correlation_id=correlation_id,
            situation_ids=situation_ids,
            signal_ids=signal_ids,
            evidence_event_ids=evidence_event_ids,
            severity=severity,
            score=score,
        )
