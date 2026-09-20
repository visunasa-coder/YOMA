from yoma.office.intelligence.organization_runtime import (
    OrganizationIntelligenceRuntime,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Organization,
)
from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_events import OrganizationChangeEvent


def test_runtime_builds_graph_and_validation():
    runtime = OrganizationIntelligenceRuntime(
        organizations=[Organization("org-1", "Acme")],
        departments=[
            Department("dept-1", "org-1", "Engineering"),
        ],
        employees=[
            Employee(
                "emp-1",
                "Alice",
                organization_id="org-1",
                department_id="dept-1",
            )
        ],
    )

    assert runtime.stale is False
    assert runtime.validation_issues() == []
    assert runtime.graph().node("org-1") is not None
    assert runtime.graph().node("dept-1") is not None
    assert runtime.graph().node("emp-1") is not None


def test_relevant_event_marks_runtime_stale():
    bus = OrganizationEventBus()

    runtime = OrganizationIntelligenceRuntime(
        event_bus=bus,
        organizations=[Organization("org-1", "Acme")],
    )

    event = OrganizationChangeEvent(
        event_type="user_updated",
        entity_type="employee",
        entity_id="emp-1",
        current_state={"name": "Alice"},
    )

    assert runtime.stale is False
    assert bus.publish(event) == 1
    assert runtime.stale is True
    assert runtime.last_event == event


def test_irrelevant_entity_event_does_not_mark_runtime_stale():
    bus = OrganizationEventBus()

    runtime = OrganizationIntelligenceRuntime(
        event_bus=bus,
        organizations=[Organization("org-1", "Acme")],
    )

    event = OrganizationChangeEvent(
        event_type="system_updated",
        entity_type="system",
        entity_id="sys-1",
        current_state={"name": "ERP"},
    )

    assert bus.publish(event) == 0
    assert runtime.stale is False
    assert runtime.last_event is None


def test_refresh_rebuilds_graph_and_clears_stale_state():
    bus = OrganizationEventBus()

    runtime = OrganizationIntelligenceRuntime(
        event_bus=bus,
        organizations=[Organization("org-1", "Acme")],
    )

    bus.publish(
        OrganizationChangeEvent(
            event_type="organization_updated",
            entity_type="organization",
            entity_id="org-1",
            current_state={"name": "Acme Updated"},
        )
    )

    assert runtime.stale is True

    runtime.refresh(
        organizations=[Organization("org-2", "Beta")],
        employees=[
            Employee(
                "emp-2",
                "Bob",
                organization_id="org-2",
            )
        ],
    )

    assert runtime.stale is False
    assert runtime.last_event is not None
    assert runtime.graph().node("org-1") is None
    assert runtime.graph().node("org-2") is not None
    assert runtime.graph().node("emp-2") is not None
    assert runtime.validation_issues() == []


def test_close_unsubscribes_runtime():
    bus = OrganizationEventBus()

    runtime = OrganizationIntelligenceRuntime(
        event_bus=bus,
        organizations=[Organization("org-1", "Acme")],
    )

    assert bus.subscriber_count() == 1
    assert runtime.close() is True
    assert bus.subscriber_count() == 0
    assert runtime.close() is False


def test_runtime_does_not_infer_models_from_event_state():
    bus = OrganizationEventBus()

    runtime = OrganizationIntelligenceRuntime(
        event_bus=bus,
        organizations=[Organization("org-1", "Acme")],
    )

    bus.publish(
        OrganizationChangeEvent(
            event_type="employee_created",
            entity_type="employee",
            entity_id="emp-9",
            current_state={
                "name": "New Employee",
                "organization_id": "org-1",
            },
        )
    )

    assert runtime.stale is True
    assert runtime.graph().node("emp-9") is None
