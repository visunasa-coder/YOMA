from datetime import datetime, timezone

import pytest

from yoma.office.decision import (
    DecisionContext,
    DecisionOrchestrator,
    workload_decision,
)
from yoma.office.operations import OperationalSignal


def make_signal(
    signal_type="workload.high",
    score=0.9,
):
    return OperationalSignal(
        signal_id="SIG001",
        signal_type=signal_type,
        detected_at=datetime.now(timezone.utc),
        user_id="U001",
        score=score,
        severity="warning",
        evidence_event_ids=("EV001",),
    )


def test_orchestrator_registers_handler():
    orchestrator = DecisionOrchestrator()

    orchestrator.register_handler(
        "workload.high",
        workload_decision,
    )

    assert orchestrator.list_handlers() == ["workload.high"]


def test_duplicate_handler_rejected():
    orchestrator = DecisionOrchestrator()

    orchestrator.register_handler(
        "workload.high",
        workload_decision,
    )

    with pytest.raises(ValueError):
        orchestrator.register_handler(
            "workload.high",
            workload_decision,
        )


def test_unknown_signal_is_safe():
    orchestrator = DecisionOrchestrator()

    context = orchestrator.evaluate(
        make_signal("unknown.signal")
    )

    assert isinstance(context, DecisionContext)
    assert context.recommendations == ()
    assert context.actions == ()
    assert context.requires_human_approval is True


def test_workload_signal_generates_recommendation():
    orchestrator = DecisionOrchestrator()

    orchestrator.register_handler(
        "workload.high",
        workload_decision,
    )

    context = orchestrator.evaluate(
        make_signal()
    )

    assert len(context.recommendations) == 1
    assert context.recommendations[0]["type"] == "workload_review"
    assert context.recommendations[0]["employee_id"] == "U001"


def test_workload_signal_generates_approval_required_action():
    orchestrator = DecisionOrchestrator()

    orchestrator.register_handler(
        "workload.high",
        workload_decision,
    )

    context = orchestrator.evaluate(
        make_signal()
    )

    assert len(context.actions) == 1
    assert context.actions[0].requires_approval is True
    assert context.requires_human_approval is True


def test_evaluate_many():
    orchestrator = DecisionOrchestrator()

    orchestrator.register_handler(
        "workload.high",
        workload_decision,
    )

    contexts = orchestrator.evaluate_many(
        [
            make_signal("workload.high", 0.8),
            make_signal("workload.high", 0.95),
        ]
    )

    assert len(contexts) == 2
    assert contexts[0].actions[0].requires_approval is True
    assert contexts[1].actions[0].requires_approval is True


def test_invalid_handler_result_rejected():
    orchestrator = DecisionOrchestrator()

    def bad_handler(signal):
        return {"bad": True}

    orchestrator.register_handler(
        "workload.high",
        bad_handler,
    )

    with pytest.raises(TypeError):
        orchestrator.evaluate(make_signal())


def test_empty_signal_type_rejected():
    orchestrator = DecisionOrchestrator()

    with pytest.raises(ValueError):
        orchestrator.register_handler(
            "",
            workload_decision,
        )


def test_workload_decision_preserves_signal():
    signal = make_signal()

    context = workload_decision(signal)

    assert context.signal is signal
    assert context.actions[0].target_user_id == "U001"
