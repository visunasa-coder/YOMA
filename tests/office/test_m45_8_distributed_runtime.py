from unittest.mock import Mock

import pytest

from yoma.office.distributed_runtime import (
    DistributedRuntime,
    DistributedRuntimeStatus,
    create_distributed_runtime,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.runtime import YomaEmbeddedRuntime


def make_identity():
    organization = DistributedOrganizationIdentity(
        organization_id="ORG-M45",
        organization_name="M45 Test Organization",
        deployment_id="DEP-M45",
    )

    node = DistributedNodeIdentity(
        node_id="NODE-PC-01",
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_name="Employee PC 01",
    )

    return organization, node


def make_runtime():
    organization, node = make_identity()
    return DistributedRuntime(
        organization=organization,
        node=node,
    )


def test_runtime_constructs():
    runtime = make_runtime()

    assert isinstance(runtime, DistributedRuntime)
    assert runtime.organization.organization_id == "ORG-M45"
    assert runtime.node.node_id == "NODE-PC-01"


def test_runtime_reuses_existing_embedded_runtime():
    organization, node = make_identity()
    embedded = YomaEmbeddedRuntime()

    runtime = DistributedRuntime(
        organization=organization,
        node=node,
        embedded_runtime=embedded,
    )

    assert runtime.embedded_runtime is embedded


def test_factory_creates_runtime():
    runtime = create_distributed_runtime(
        organization=make_identity()[0],
        node=make_identity()[1],
    )

    assert isinstance(runtime, DistributedRuntime)


def test_wrong_node_binding_is_rejected():
    organization, _ = make_identity()

    node = DistributedNodeIdentity(
        node_id="NODE-OTHER",
        organization_id="ORG-OTHER",
        deployment_id="DEP-OTHER",
        node_name="Other PC",
    )

    with pytest.raises(ValueError):
        DistributedRuntime(
            organization=organization,
            node=node,
        )


def test_initial_runtime_is_stopped():
    runtime = make_runtime()

    status = runtime.status()

    assert status.running is False
    assert status.executable is False
    assert status.execution_allowed is False
    assert status.requires_human_approval is True


def test_node_registration_flows_through_security_boundary():
    runtime = make_runtime()

    trust = runtime.register_node()

    assert trust.node_id == "NODE-PC-01"
    assert trust.state.value == "unknown"


def test_node_trust_flows_through_security_boundary():
    runtime = make_runtime()

    runtime.register_node()
    trust = runtime.trust_node(reason="m45_test_trust")

    assert trust.state.value == "trusted"


def test_node_validation_flows_through_security_boundary():
    runtime = make_runtime()

    runtime.register_node()
    runtime.trust_node()

    result = runtime.validate_node()

    assert result.valid is True
    assert result.trusted is True


def test_start_uses_edge_worker():
    runtime = make_runtime()

    runtime.edge_worker.start = Mock()
    runtime.edge_worker.status = Mock()

    runtime.start()

    runtime.edge_worker.start.assert_called_once()
    assert runtime.status().running is True


def test_start_is_idempotent():
    runtime = make_runtime()

    runtime.edge_worker.start = Mock()

    runtime.start()
    runtime.start()

    runtime.edge_worker.start.assert_called_once()


def test_stop_uses_edge_worker():
    runtime = make_runtime()

    runtime.edge_worker.start = Mock()
    runtime.edge_worker.stop = Mock()

    runtime.start()
    runtime.stop()

    runtime.edge_worker.stop.assert_called_once()
    assert runtime.status().running is False


def test_stop_is_idempotent():
    runtime = make_runtime()

    runtime.edge_worker.start = Mock()
    runtime.edge_worker.stop = Mock()

    runtime.start()
    runtime.stop()
    runtime.stop()

    runtime.edge_worker.stop.assert_called_once()


def test_connectivity_flows_through_offline_boundary():
    runtime = make_runtime()

    runtime.set_offline()

    status = runtime.offline.status()

    assert status.state.value == "offline"


def test_online_connectivity_flows_through_offline_boundary():
    runtime = make_runtime()

    runtime.set_offline()
    runtime.set_online()

    status = runtime.offline.status()

    assert status.state.value == "online"


def test_event_collection_flows_through_m45_4():
    runtime = make_runtime()

    runtime.event_collector.collect = Mock(return_value="collection-result")

    result = runtime.collect_events(())

    assert result == "collection-result"
    runtime.event_collector.collect.assert_called_once_with(())


def test_diagnostics_contains_all_distributed_layers():
    runtime = make_runtime()

    diagnostics = runtime.diagnostics()

    assert "organization" in diagnostics
    assert "node" in diagnostics
    assert "runtime" in diagnostics
    assert "edge_worker" in diagnostics
    assert "security" in diagnostics
    assert "event_collection" in diagnostics
    assert "cloud_sync" in diagnostics
    assert "offline" in diagnostics
    assert "governance" in diagnostics
    assert "execution" in diagnostics


def test_diagnostics_is_secret_free():
    runtime = make_runtime()

    diagnostics = runtime.diagnostics()

    text = str(diagnostics).lower()

    assert "password" not in text
    assert "client_secret" not in text
    assert "credential_value" not in text


def test_governance_boundary_never_allows_execution():
    runtime = make_runtime()

    diagnostics = runtime.diagnostics()

    assert diagnostics["governance"]["execution_allowed"] is False
    assert diagnostics["governance"]["executable"] is False
    assert diagnostics["governance"]["requires_human_approval"] is True


def test_runtime_status_never_becomes_executable():
    runtime = make_runtime()

    status = runtime.status()

    assert status.executable is False
    assert status.execution_allowed is False
    assert status.requires_human_approval is True


def test_status_serialization():
    runtime = make_runtime()

    status = runtime.status()
    data = status.as_dict()

    assert data["organization_id"] == "ORG-M45"
    assert data["deployment_id"] == "DEP-M45"
    assert data["node_id"] == "NODE-PC-01"
    assert data["executable"] is False
    assert data["execution_allowed"] is False


def test_runtime_does_not_create_second_embedded_runtime_when_injected():
    organization, node = make_identity()
    embedded = YomaEmbeddedRuntime()

    runtime = DistributedRuntime(
        organization=organization,
        node=node,
        embedded_runtime=embedded,
    )

    assert runtime.embedded_runtime is embedded
    assert runtime.edge_worker.runtime is embedded
