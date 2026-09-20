from datetime import datetime, timezone

from yoma.office.control_server.decision_intelligence import (
    ControlServerDecisionIntelligence,
    ControlServerDecisionIntelligenceStatus,
)
from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceRuntime,
)


def make_runtime():
    return ControlServerRuntime(
        host="127.0.0.1",
        port=0,
    )


def make_decision_runtime():
    return DecisionIntelligenceRuntime()


def test_status_before_decision_analysis():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    status = integration.status()

    assert isinstance(
        status,
        ControlServerDecisionIntelligenceStatus,
    )
    assert status.available is False
    assert status.decision_count == 0
    assert status.explanation_count == 0
    assert status.requires_human_review is False


def test_latest_before_analysis_is_none():
    integration = ControlServerDecisionIntelligence(
        make_runtime(),
        make_decision_runtime(),
    )

    assert integration.latest() is None


def test_status_reflects_server_state():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    assert integration.running is False
    assert integration.status().running is False


def test_runtime_references_are_preserved():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    assert integration.control_server_runtime is server
    assert integration.decision_runtime is decisions


def test_invalid_server_rejected():
    decisions = make_decision_runtime()

    try:
        ControlServerDecisionIntelligence(
            object(),
            decisions,
        )
    except TypeError as exc:
        assert "ControlServerRuntime" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_invalid_decision_runtime_rejected():
    server = make_runtime()

    try:
        ControlServerDecisionIntelligence(
            server,
            object(),
        )
    except TypeError as exc:
        assert "DecisionIntelligenceRuntime" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_empty_analysis_is_safe():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    decisions.analyze()

    status = integration.status()

    assert status.available is False
    assert status.decision_count == 0
    assert status.explanation_count == 0
    assert integration.latest() is not None


def test_latest_contains_runtime_counts():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    decisions.analyze()

    latest = integration.latest()

    assert latest is not None
    assert latest["decision_count"] == 0
    assert latest["graph_count"] == 0
    assert latest["explanation_count"] == 0
    assert latest["requires_human_review"] is False
    assert latest["decisions"] == ()
    assert latest["explanations"] == ()


def test_status_model_ready_requires_available_and_running():
    status = ControlServerDecisionIntelligenceStatus(
        available=True,
        running=False,
        decision_count=1,
        explanation_count=1,
        requires_human_review=True,
    )

    assert status.ready is False


def test_status_model_ready_when_available_and_running():
    status = ControlServerDecisionIntelligenceStatus(
        available=True,
        running=True,
        decision_count=1,
        explanation_count=1,
        requires_human_review=True,
    )

    assert status.ready is True


def test_human_review_boundary_is_preserved():
    server = make_runtime()
    decisions = make_decision_runtime()

    integration = ControlServerDecisionIntelligence(
        server,
        decisions,
    )

    decisions.analyze()

    status = integration.status()

    assert status.requires_human_review is False


def test_no_action_execution_surface():
    integration = ControlServerDecisionIntelligence(
        make_runtime(),
        make_decision_runtime(),
    )

    public_names = {
        name
        for name in dir(integration)
        if not name.startswith("_")
    }

    assert "execute" not in public_names
    assert "approve" not in public_names
    assert "execute_action" not in public_names
