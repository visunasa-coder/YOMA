from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.control_server_intelligence_runtime import (
    ControlServerIntelligenceRuntime,
)
from yoma.office.intelligence.control_server_intelligence_status import (
    ControlServerIntelligenceStatus,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent


def make_intelligence() -> OperationalUnifiedRuntime:
    organization = Organization(
        organization_id="ORG001",
        name="YOMA Test Org",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Test Employee",
        organization_id="ORG001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    return OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )


def make_event() -> OperationalEvent:
    return OperationalEvent(
        event_id="M27.5-EVENT",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="EMP001",
        system_id=None,
        source="test",
        location_id=None,
        severity="warning",
        data={"score": 0.9},
    )


def make_runtime() -> ControlServerIntelligenceRuntime:
    control = ControlServerRuntime(
        host="127.0.0.1",
        port=0,
    )

    return ControlServerIntelligenceRuntime(
        control_server_runtime=control,
        intelligence_runtime=make_intelligence(),
    )


def test_snapshot_before_processing():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    snapshot = status.snapshot()

    assert snapshot == {
        "available": True,
        "running": False,
        "subscribed": False,
        "has_latest_result": False,
        "event_count": 0,
        "signal_count": 0,
        "situation_count": 0,
        "context_count": 0,
        "pattern_count": 0,
        "decision_count": 0,
    }

    runtime.close()


def test_snapshot_reports_runtime_state():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()

    snapshot = status.snapshot()

    assert snapshot["available"] is True
    assert snapshot["running"] is True
    assert snapshot["subscribed"] is True
    assert snapshot["has_latest_result"] is False

    runtime.close()


def test_snapshot_reports_pipeline_counts():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()
    runtime.embedded_runtime.publish(make_event())

    snapshot = status.snapshot()

    assert snapshot["has_latest_result"] is True
    assert snapshot["event_count"] == 1
    assert snapshot["signal_count"] == 1

    runtime.close()


def test_latest_summary_before_processing():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    summary = status.latest_summary()

    assert summary == {
        "available": True,
        "has_latest_result": False,
        "event_id": None,
        "event_type": None,
        "signal_count": 0,
        "situation_count": 0,
        "context_count": 0,
        "pattern_count": 0,
        "decision_count": 0,
    }

    runtime.close()


def test_latest_summary_after_processing():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()
    runtime.embedded_runtime.publish(make_event())

    summary = status.latest_summary()

    assert summary["available"] is True
    assert summary["has_latest_result"] is True
    assert summary["event_id"] == "M27.5-EVENT"
    assert summary["event_type"] == "workload.high"
    assert summary["signal_count"] == 1

    runtime.close()


def test_snapshot_is_read_only():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    first = status.snapshot()
    second = status.snapshot()

    assert first == second
    assert runtime.running is False
    assert runtime.subscribed is False

    runtime.close()


def test_invalid_runtime_is_rejected():
    with pytest.raises(TypeError):
        ControlServerIntelligenceStatus(runtime=object())


def test_stop_is_reflected_in_snapshot():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()
    runtime.stop()

    snapshot = status.snapshot()

    assert snapshot["running"] is False
    assert snapshot["subscribed"] is True

    runtime.close()


def test_close_is_reflected_in_snapshot():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()
    runtime.close()

    snapshot = status.snapshot()

    assert snapshot["running"] is False
    assert snapshot["subscribed"] is False

    runtime.close()


def test_latest_summary_does_not_expose_raw_payloads():
    runtime = make_runtime()
    status = ControlServerIntelligenceStatus(runtime=runtime)

    runtime.start()
    runtime.embedded_runtime.publish(make_event())

    summary = status.latest_summary()

    assert "data" not in summary
    assert "parameters" not in summary
    assert "secret" not in summary
    assert "password" not in summary

    runtime.close()
