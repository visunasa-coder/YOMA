from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.embedded_operational_intelligence import (
    EmbeddedOperationalIntelligence,
)
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent
from yoma.office.runtime import YomaEmbeddedRuntime


def make_unified_runtime():
    organization = Organization(
        organization_id="org-1",
        name="Test Org",
    )

    employee = Employee(
        employee_id="emp-1",
        name="Employee One",
        organization_id="org-1",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    engine = OperationalIntelligenceEngine()

    def workload_rule(events):
        from yoma.office.operations import OperationalSignal

        return [
            OperationalSignal(
                signal_id=f"SIG-{event.event_id}",
                signal_type="workload.high",
                detected_at=event.occurred_at,
                organization_id=event.organization_id,
                user_id=event.user_id,
                score=event.data["score"],
                severity="high",
                evidence_event_ids=(event.event_id,),
            )
            for event in events
            if event.event_type == "workload.high"
        ]

    engine.register_rule("workload", workload_rule)

    return OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )


def make_event():
    return OperationalEvent(
        event_id="EV-EMBEDDED-1",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="embedded-test",
        severity="high",
        data={"score": 0.9},
    )


def test_embedded_intelligence_uses_existing_embedded_bus():
    embedded = YomaEmbeddedRuntime()
    unified = make_unified_runtime()

    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=unified,
    )

    assert bridge.bus_runtime.event_bus is embedded.bus


def test_embedded_intelligence_starts_unsubscribed():
    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=YomaEmbeddedRuntime(),
        intelligence_runtime=make_unified_runtime(),
    )

    assert bridge.running is False
    assert bridge.subscribed is False


def test_start_subscribes_to_existing_bus():
    embedded = YomaEmbeddedRuntime()
    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=make_unified_runtime(),
    )

    bridge.start()

    assert bridge.running is True
    assert bridge.subscribed is True
    assert embedded.bus.subscriber_count == 1


def test_event_from_embedded_runtime_reaches_unified_runtime():
    embedded = YomaEmbeddedRuntime()
    unified = make_unified_runtime()

    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=unified,
    )

    embedded.start()
    bridge.start()

    event = make_event()
    embedded.publish(event)

    assert bridge.last_result is not None
    assert bridge.last_result.event == event
    assert bridge.last_result.intelligence.events == (event,)
    assert len(bridge.last_result.intelligence.signals) == 1
    assert len(bridge.last_result.intelligence.situations) == 1
    assert len(bridge.last_result.intelligence.contexts) == 1


def test_stopped_bridge_ignores_events():
    embedded = YomaEmbeddedRuntime()
    unified = make_unified_runtime()

    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=unified,
    )

    embedded.start()
    bridge.start()
    bridge.stop()

    embedded.publish(make_event())

    assert bridge.last_result is None


def test_stop_preserves_subscription_but_disables_processing():
    embedded = YomaEmbeddedRuntime()
    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=make_unified_runtime(),
    )

    bridge.start()
    bridge.stop()

    assert bridge.running is False
    assert bridge.subscribed is True
    assert embedded.bus.subscriber_count == 1


def test_close_unsubscribes_from_existing_bus():
    embedded = YomaEmbeddedRuntime()
    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=make_unified_runtime(),
    )

    bridge.start()
    bridge.close()

    assert bridge.running is False
    assert bridge.subscribed is False
    assert embedded.bus.subscriber_count == 0


def test_start_is_idempotent():
    embedded = YomaEmbeddedRuntime()
    bridge = EmbeddedOperationalIntelligence(
        embedded_runtime=embedded,
        intelligence_runtime=make_unified_runtime(),
    )

    bridge.start()
    bridge.start()

    assert bridge.subscribed is True
    assert embedded.bus.subscriber_count == 1


def test_constructor_validates_dependencies():
    with pytest.raises(TypeError):
        EmbeddedOperationalIntelligence(
            embedded_runtime=object(),
            intelligence_runtime=make_unified_runtime(),
        )

    with pytest.raises(TypeError):
        EmbeddedOperationalIntelligence(
            embedded_runtime=YomaEmbeddedRuntime(),
            intelligence_runtime=object(),
        )
