from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from yoma.office.action_simulation import ActionSimulation
from yoma.office.closed_loop_observation import ClosedLoopObservation


@dataclass(frozen=True)
class OutcomeLearningSignal:
    learning_id: str
    decision_id: str
    plan_id: str
    prediction_accuracy: float
    outcome_alignment: float
    prediction_error: float
    learning_direction: str
    evidence_ids: Tuple[str, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.learning_id.startswith("LEARN-"):
            raise ValueError("learning_id must start with LEARN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")

        for name, value in (
            ("prediction_accuracy", self.prediction_accuracy),
            ("outcome_alignment", self.outcome_alignment),
            ("prediction_error", self.prediction_error),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if self.learning_direction not in {
            "improve",
            "stable",
            "degrade",
            "insufficient_data",
        }:
            raise ValueError("invalid learning direction")


@dataclass(frozen=True)
class OutcomeLearningResult:
    result_id: str
    decision_id: str
    plan_id: str
    prediction_outcome: str
    prediction_accuracy: float
    prediction_error: float
    signals: Tuple[OutcomeLearningSignal, ...] = ()
    observed_event_count: int = 0
    expected_event_count: int = 0
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.result_id.startswith("OLRN-"):
            raise ValueError("result_id must start with OLRN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")

        if self.prediction_outcome not in {
            "accurate",
            "partially_accurate",
            "inaccurate",
            "insufficient_data",
        }:
            raise ValueError("invalid prediction outcome")

        if not 0.0 <= self.prediction_accuracy <= 1.0:
            raise ValueError(
                "prediction_accuracy must be between 0 and 1"
            )

        if not 0.0 <= self.prediction_error <= 1.0:
            raise ValueError(
                "prediction_error must be between 0 and 1"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "outcome learning requires human approval"
            )

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def learning_available(self) -> bool:
        return bool(self.signals)

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class OutcomeLearningEngine:
    """
    Compares simulated outcomes with observed outcomes.

    This produces learning signals only. It does not retrain models,
    modify policies, or execute actions.
    """

    def learn(
        self,
        simulation: ActionSimulation,
        observation: ClosedLoopObservation,
    ) -> OutcomeLearningResult:
        if not isinstance(simulation, ActionSimulation):
            raise TypeError(
                "simulation must be an ActionSimulation"
            )

        if not isinstance(observation, ClosedLoopObservation):
            raise TypeError(
                "observation must be a ClosedLoopObservation"
            )

        if simulation.plan_id != observation.plan_id:
            raise ValueError(
                "simulation and observation must reference "
                "the same plan"
            )

        if simulation.decision_id != observation.decision_id:
            raise ValueError(
                "simulation and observation must reference "
                "the same decision"
            )

        accuracy = self._accuracy(
            simulation,
            observation,
        )

        error = round(1.0 - accuracy, 6)

        prediction_outcome = self._outcome(
            accuracy,
            observation,
        )

        direction = self._direction(
            accuracy,
            observation,
        )

        evidence_ids = tuple(
            dict.fromkeys(
                (
                    *simulation.evidence_ids,
                    *(
                        event_id
                        for item in observation.observations
                        for event_id in item.event_ids
                    ),
                )
            )
        )

        signal = OutcomeLearningSignal(
            learning_id=f"LEARN-{simulation.simulation_id}",
            decision_id=simulation.decision_id,
            plan_id=simulation.plan_id,
            prediction_accuracy=accuracy,
            outcome_alignment=accuracy,
            prediction_error=error,
            learning_direction=direction,
            evidence_ids=evidence_ids,
            data={
                "simulation_id": simulation.simulation_id,
                "observation_id": observation.observation_id,
                "observed_event_count": (
                    observation.observed_event_count
                ),
                "expected_event_count": (
                    observation.expected_event_count
                ),
            },
        )

        return OutcomeLearningResult(
            result_id=f"OLRN-{simulation.simulation_id}",
            decision_id=simulation.decision_id,
            plan_id=simulation.plan_id,
            prediction_outcome=prediction_outcome,
            prediction_accuracy=accuracy,
            prediction_error=error,
            signals=(signal,),
            observed_event_count=observation.observed_event_count,
            expected_event_count=observation.expected_event_count,
            requires_human_approval=True,
            metadata={
                "simulation_confidence": simulation.confidence,
                "observation_status": observation.outcome_status,
            },
        )

    def _accuracy(
        self,
        simulation: ActionSimulation,
        observation: ClosedLoopObservation,
    ) -> float:
        if observation.outcome_status in {
            "pending",
            "unknown",
        }:
            return 0.0

        if not simulation.outcomes:
            return 0.0

        outcome_probability = sum(
            outcome.probability
            for outcome in simulation.outcomes
        ) / len(simulation.outcomes)

        if observation.matches_expectation is True:
            alignment = 1.0
        elif observation.matches_expectation is False:
            alignment = 0.0
        else:
            alignment = 0.5

        return round(
            min(
                1.0,
                0.5 * outcome_probability
                + 0.5 * alignment,
            ),
            6,
        )

    def _outcome(
        self,
        accuracy: float,
        observation: ClosedLoopObservation,
    ) -> str:
        if observation.outcome_status in {
            "pending",
            "unknown",
        }:
            return "insufficient_data"

        if accuracy >= 0.75:
            return "accurate"

        if accuracy >= 0.40:
            return "partially_accurate"

        return "inaccurate"

    def _direction(
        self,
        accuracy: float,
        observation: ClosedLoopObservation,
    ) -> str:
        if observation.outcome_status in {
            "pending",
            "unknown",
        }:
            return "insufficient_data"

        if accuracy >= 0.75:
            return "stable"

        if accuracy >= 0.40:
            return "improve"

        return "degrade"

    def learn_many(
        self,
        pairs: Tuple[
            Tuple[ActionSimulation, ClosedLoopObservation],
            ...,
        ] | list[
            Tuple[ActionSimulation, ClosedLoopObservation]
        ],
    ) -> Tuple[OutcomeLearningResult, ...]:
        return tuple(
            self.learn(simulation, observation)
            for simulation, observation in pairs
        )
