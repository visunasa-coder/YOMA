from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.operational_control_observation import (
    OperationalControlObservation,
)
from yoma.office.intelligence.operational_control_reconciliation import (
    OperationalControlReconciliationState,
)
from yoma.office.intelligence.operational_control_learning import (
    OperationalControlLearningRuntime,
)


def make_observation(
    state=OperationalControlReconciliationState.CONSISTENT,
    observed="approved",
):
    now = datetime.now(timezone.utc)

    return OperationalControlObservation(
        decision_id="decision-m34-8",
        plan_id="plan-m34-8",
        orchestration_id="orchestration-m34-8",
        observed_state=observed,
        reconciliation_state=state,
        observed_at=now,
        execution_allowed=False,
        executable=False,
        metadata={"test": True},
    )


def test_m34_8_consistent_learning_signal():
    result = OperationalControlLearningRuntime.prepare(
        make_observation()
    )

    assert result.learning_signal == "control_outcome_consistent"


def test_m34_8_diverged_learning_signal():
    result = OperationalControlLearningRuntime.prepare(
        make_observation(
            OperationalControlReconciliationState.DIVERGED,
            "rejected",
        )
    )

    assert result.learning_signal == "control_outcome_diverged"


def test_m34_8_pending_learning_signal():
    result = OperationalControlLearningRuntime.prepare(
        make_observation(
            OperationalControlReconciliationState.PENDING,
            "unknown",
        )
    )

    assert result.learning_signal == "control_outcome_pending"


def test_m34_8_preserves_identity():
    result = OperationalControlLearningRuntime.prepare(
        make_observation()
    )

    assert result.decision_id == "decision-m34-8"
    assert result.plan_id == "plan-m34-8"
    assert result.orchestration_id == "orchestration-m34-8"


def test_m34_8_preserves_observation():
    observation = make_observation()

    result = OperationalControlLearningRuntime.prepare(
        observation
    )

    assert result.observed_state == observation.observed_state
    assert result.reconciliation_state == (
        observation.reconciliation_state
    )


def test_m34_8_never_enables_execution():
    for state, observed in (
        (OperationalControlReconciliationState.PENDING, "unknown"),
        (OperationalControlReconciliationState.CONSISTENT, "approved"),
        (OperationalControlReconciliationState.DIVERGED, "rejected"),
    ):
        result = OperationalControlLearningRuntime.prepare(
            make_observation(state, observed)
        )

        assert result.autonomous_learning is False
        assert result.executable is False


def test_m34_8_is_timestamped():
    result = OperationalControlLearningRuntime.prepare(
        make_observation()
    )

    assert result.observed_at.tzinfo is not None
    assert result.handed_off_at.tzinfo is not None


def test_m34_8_points_to_existing_learning():
    result = OperationalControlLearningRuntime.prepare(
        make_observation()
    )

    assert (
        result.metadata["learning_owner"]
        == "existing_outcome_learning"
    )


def test_m34_8_rejects_missing_identity():
    observation = make_observation()

    invalid = OperationalControlObservation(
        decision_id="",
        plan_id=observation.plan_id,
        orchestration_id=observation.orchestration_id,
        observed_state=observation.observed_state,
        reconciliation_state=observation.reconciliation_state,
        observed_at=observation.observed_at,
        execution_allowed=False,
        executable=False,
        metadata=observation.metadata,
    )

    with pytest.raises(ValueError):
        OperationalControlLearningRuntime.prepare(invalid)
