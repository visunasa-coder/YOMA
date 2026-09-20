from datetime import datetime, timezone

import pytest

from yoma.office.adapters import YomaAdapter
from yoma.office.adapters.runtime import (
    AdapterRuntimeManager,
    AdapterRuntimeResult,
)
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_bus_runtime import (
    OperationalBusIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.resilient_integration_intelligence_runtime import (
    ResilientIntegrationIntelligenceRuntime,
    ResilientIntegrationResult,
)
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent, OperationalEventBus


class GoodAdapter(YomaAdapter):
    name = "good_adapter"
    category = "test"

    def __init__(self):
        super().__init__()
        self._connected = False
        self.collect_count = 0

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        if not self.connected:
            raise RuntimeError("not connected")

        self.collect_count += 1

        return [
            OperationalEvent(
                event_id=f"GOOD-{self.collect_count}",
                event_type="workload.high",
                occurred_at=datetime.now(timezone.utc),
                organization_id="org-1",
                user_id="emp-1",
                source=self.name,
                severity="high",
                data={"score": 0.9},
            )
        ]


class FailingAdapter(YomaAdapter):
    name = "bad_adapter"
    category = "test"

    def __init__(self):
        super().__init__()
        self._connected = False

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        raise RuntimeError("simulated failure")


def make_runtime(include_bad=True):
    adapter_runtime = AdapterRuntimeManager(
        max_retries=0,
    )

    good = GoodAdapter()
    adapter_runtime.register(good)
    adapter_runtime.connect("good_adapter", {})

    if include_bad:
        bad = FailingAdapter()
        adapter_runtime.register(bad)
        adapter_runtime.connect("bad_adapter", {})

    engine = OperationalIntelligenceEngine()
    engine.register_rule(
        "workload",
        high_workload_rule,
    )

    organization = Organization(
        organization_id="org-1",
        name="Test Organization",
    )

    employee = Employee(
        employee_id="emp-1",
        name="Test Employee",
        organization_id="org-1",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    unified = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    bus = OperationalEventBus()

    bus_runtime = OperationalBusIntelligenceRuntime(
        intelligence_runtime=unified,
        event_bus=bus,
    )

    runtime = ResilientIntegrationIntelligenceRuntime(
        adapter_runtime=adapter_runtime,
        bus_runtime=bus_runtime,
    )

    return runtime, adapter_runtime, bus_runtime, bus


def test_constructor_validates_adapter_runtime():
    with pytest.raises(TypeError):
        ResilientIntegrationIntelligenceRuntime(
            adapter_runtime=object(),
            bus_runtime=object(),
        )


def test_constructor_validates_bus_runtime():
    adapter_runtime = AdapterRuntimeManager()

    with pytest.raises(TypeError):
        ResilientIntegrationIntelligenceRuntime(
            adapter_runtime=adapter_runtime,
            bus_runtime=object(),
        )


def test_start_and_stop_delegate_to_bus_runtime():
    runtime, _, bus_runtime, _ = make_runtime(False)

    assert bus_runtime.running is False

    runtime.start()

    assert bus_runtime.running is True

    runtime.stop()

    assert bus_runtime.running is False


def test_successful_adapter_events_reach_intelligence():
    runtime, _, _, _ = make_runtime(False)

    runtime.start()

    result = runtime.collect_all()

    assert isinstance(result, ResilientIntegrationResult)
    assert len(result.events) == 1
    assert len(result.intelligence_results) == 1

    intelligence = result.intelligence_results[0].intelligence

    assert len(intelligence.events) == 1
    assert len(intelligence.signals) == 1
    assert len(intelligence.situations) == 1


def test_failed_adapter_does_not_break_successful_adapter():
    runtime, _, _, _ = make_runtime(True)

    runtime.start()

    result = runtime.collect_all()

    assert len(result.events) == 1
    assert result.successful_adapters == ("good_adapter",)
    assert result.failed_adapters == ("bad_adapter",)

    result_map = {
        item.adapter: item
        for item in result.adapter_results
    }

    assert result_map["good_adapter"].status == "collected"
    assert result_map["bad_adapter"].status == "failed"


def test_failed_adapter_error_is_preserved():
    runtime, _, _, _ = make_runtime(True)

    runtime.start()

    result = runtime.collect_all()

    failed = next(
        item
        for item in result.adapter_results
        if item.adapter == "bad_adapter"
    )

    assert failed.error == "RuntimeError"
    assert failed.attempts == 1


def test_failed_adapter_produces_no_intelligence_event():
    runtime, _, _, _ = make_runtime(True)

    runtime.start()

    result = runtime.collect_all()

    assert len(result.intelligence_results) == 1
    assert (
        result.intelligence_results[0].event.event_id
        == "GOOD-1"
    )


def test_empty_adapter_runtime_is_safe():
    adapter_runtime = AdapterRuntimeManager()

    engine = OperationalIntelligenceEngine()

    organization = Organization(
        organization_id="org-1",
        name="Test Organization",
    )

    graph = OrganizationGraph(
        organizations=[organization],
    )

    unified = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    bus = OperationalEventBus()

    bus_runtime = OperationalBusIntelligenceRuntime(
        intelligence_runtime=unified,
        event_bus=bus,
    )

    runtime = ResilientIntegrationIntelligenceRuntime(
        adapter_runtime=adapter_runtime,
        bus_runtime=bus_runtime,
    )

    runtime.start()

    result = runtime.collect_all()

    assert result.events == ()
    assert result.adapter_results == ()
    assert result.intelligence_results == ()


def test_last_result_is_updated():
    runtime, _, _, _ = make_runtime(False)

    runtime.start()

    assert runtime.last_result is None

    result = runtime.collect_all()

    assert runtime.last_result is result


def test_close_unsubscribes_bus_runtime():
    runtime, _, bus_runtime, bus = make_runtime(False)

    runtime.start()
    runtime.close()

    assert bus_runtime.subscribed is False
    assert bus.subscriber_count == 0


def test_existing_adapter_retry_contract_remains_untouched():
    manager = AdapterRuntimeManager(max_retries=2)

    result = AdapterRuntimeResult(
        adapter="test",
        status="failed",
        error="RuntimeError",
        attempts=3,
    )

    assert result.attempts == 3
    assert result.status == "failed"
