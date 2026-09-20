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
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent


def make_intelligence() -> OperationalUnifiedRuntime:
    organization = Organization(
        organization_id="ORG001",
        name="YOMA Hardening Org",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Hardening Employee",
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
        event_id="M27.8-EVENT",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="EMP001",
        system_id=None,
        source="m27.8-test",
        severity="warning",
        data={"score": 0.95},
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


def test_start_is_idempotent():
    runtime = make_runtime()

    try:
        runtime.start()

        first_thread = runtime.control_server_runtime.thread
        first_subscriber_count = runtime.embedded_runtime.bus.subscriber_count

        runtime.start()

        assert runtime.control_server_runtime.thread is first_thread
        assert runtime.running is True
        assert runtime.subscribed is True
        assert (
            runtime.embedded_runtime.bus.subscriber_count
            == first_subscriber_count
        )
    finally:
        runtime.close()


def test_stop_is_idempotent():
    runtime = make_runtime()

    runtime.start()
    runtime.stop()
    runtime.stop()

    assert runtime.control_server_runtime.running is False
    assert runtime.embedded_runtime.running is False
    assert runtime.running is False

    runtime.close()


def test_close_is_idempotent():
    runtime = make_runtime()

    runtime.start()
    runtime.close()
    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert runtime.control_server_runtime.running is False


def test_start_failure_rolls_back_bridge():
    runtime = make_runtime()

    original_start = runtime.control_server_runtime.start

    def failing_start():
        raise RuntimeError("control server startup failed")

    runtime.control_server_runtime.start = failing_start

    with pytest.raises(RuntimeError, match="control server startup failed"):
        runtime.start()

    assert runtime.running is False
    assert runtime.subscribed is True

    runtime.control_server_runtime.start = original_start

    runtime.close()


def test_failed_start_does_not_duplicate_subscription():
    runtime = make_runtime()

    def failing_start():
        raise RuntimeError("startup failure")

    runtime.control_server_runtime.start = failing_start

    with pytest.raises(RuntimeError):
        runtime.start()

    first_count = runtime.embedded_runtime.bus.subscriber_count

    assert first_count == 1

    runtime.control_server_runtime.start = (
        ControlServerRuntime.start.__get__(
            runtime.control_server_runtime,
            ControlServerRuntime,
        )
    )

    runtime.close()


def test_event_processing_survives_hardened_lifecycle():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        result = runtime.last_result

        assert result is not None
        assert result.event.event_id == "M27.8-EVENT"
        assert len(result.intelligence.signals) == 1
    finally:
        runtime.close()


def test_stop_attempts_bridge_even_when_control_server_stop_fails():
    runtime = make_runtime()

    runtime.start()

    original_stop = runtime.control_server_runtime.stop

    def failing_stop():
        raise RuntimeError("control server shutdown failed")

    runtime.control_server_runtime.stop = failing_stop

    with pytest.raises(RuntimeError, match="control server shutdown failed"):
        runtime.stop()

    assert runtime.subscribed is True

    runtime.control_server_runtime.stop = original_stop

    runtime.close()


def test_close_attempts_bridge_even_when_control_server_stop_fails():
    runtime = make_runtime()

    runtime.start()

    original_stop = runtime.control_server_runtime.stop

    def failing_stop():
        raise RuntimeError("control server shutdown failed")

    runtime.control_server_runtime.stop = failing_stop

    with pytest.raises(RuntimeError, match="control server shutdown failed"):
        runtime.close()

    assert runtime.subscribed is False

    runtime.control_server_runtime.stop = original_stop


def test_close_unsubscribes_after_normal_shutdown():
    runtime = make_runtime()

    runtime.start()

    assert runtime.embedded_runtime.bus.subscriber_count == 1

    runtime.close()

    assert runtime.embedded_runtime.bus.subscriber_count == 0
    assert runtime.subscribed is False


def test_canonical_event_bus_is_never_replaced():
    runtime = make_runtime()

    bus = runtime.embedded_runtime.bus

    runtime.start()

    assert runtime.embedded_runtime.bus is bus
    assert runtime.bridge.bus_runtime.event_bus is bus

    runtime.close()

    assert runtime.embedded_runtime.bus is bus


def test_control_server_and_intelligence_share_existing_components():
    runtime = make_runtime()

    assert (
        runtime.embedded_runtime
        is runtime.control_server_runtime.embedded_runtime
    )

    assert (
        runtime.agent.intelligence_runtime
        is runtime.agent.intelligence_runtime
        or runtime.agent.intelligence_runtime is None
    )

    runtime.close()
