from datetime import datetime, timezone

import pytest

from yoma.office.distributed_node_security import (
    DistributedNodeSecurityManager,
    NodeTrustState,
    create_distributed_node_security,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


NOW = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def make_runtime():
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

    return DistributedNodeSecurityManager(
        organization=organization,
        node=node,
    )


def test_manager_requires_valid_organization():
    with pytest.raises(TypeError):
        DistributedNodeSecurityManager(
            organization=object(),
            node=object(),
        )


def test_factory_creates_manager():
    runtime = make_runtime()

    assert isinstance(runtime, DistributedNodeSecurityManager)


def test_initial_status_is_unknown():
    runtime = make_runtime()

    status = runtime.status()

    assert status["trust_state"] == "unknown"
    assert status["trusted"] is False
    assert status["executable"] is False
    assert status["execution_allowed"] is False
    assert status["requires_human_approval"] is True


def test_register_creates_unknown_trust():
    runtime = make_runtime()

    trust = runtime.register()

    assert trust.state == NodeTrustState.UNKNOWN
    assert trust.node_id == "NODE-PC-01"
    assert trust.organization_id == "ORG-M45"
    assert trust.deployment_id == "DEP-M45"


def test_unregistered_node_is_not_valid():
    runtime = make_runtime()

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.valid is False
    assert result.state == NodeTrustState.UNKNOWN
    assert "node is not registered" in result.issues


def test_trusted_node_validates():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node(reason="approved_test_node")

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.valid is True
    assert result.trusted is True
    assert result.state == NodeTrustState.TRUSTED
    assert result.issues == ()


def test_wrong_organization_is_rejected():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    result = runtime.validate(
        organization_id="ORG-OTHER",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.valid is False
    assert "organization mismatch" in result.issues


def test_wrong_deployment_is_rejected():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-OTHER",
        node_id="NODE-PC-01",
    )

    assert result.valid is False
    assert "deployment mismatch" in result.issues


def test_wrong_node_is_rejected():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-OTHER",
    )

    assert result.valid is False
    assert "node mismatch" in result.issues


def test_suspended_node_is_rejected():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()
    runtime.suspend_node(reason="security_review")

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.valid is False
    assert result.state == NodeTrustState.SUSPENDED
    assert "node is suspended" in result.issues


def test_revoked_node_is_rejected():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()
    runtime.revoke_node(reason="node_revoked_test")

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.valid is False
    assert result.state == NodeTrustState.REVOKED
    assert "node is revoked" in result.issues


def test_trust_requires_no_execution_authorization():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    assert result.trusted is True
    assert result.requires_human_approval is True
    assert result.executable is False
    assert result.execution_allowed is False


def test_security_result_rejects_execution_flags():
    with pytest.raises(ValueError):
        from yoma.office.distributed_node_security import (
            DistributedNodeSecurityResult,
        )

        DistributedNodeSecurityResult(
            node_id="NODE-PC-01",
            organization_id="ORG-M45",
            deployment_id="DEP-M45",
            valid=True,
            state=NodeTrustState.TRUSTED,
            executable=True,
        )


def test_trust_serialization_is_secret_free():
    runtime = make_runtime()

    trust = runtime.register()

    data = trust.as_dict()

    assert data["node_id"] == "NODE-PC-01"
    assert "secret" not in data
    assert "credential" not in data
    assert "token" not in data


def test_security_result_serialization():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    result = runtime.validate(
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
    )

    data = result.as_dict()

    assert data["valid"] is True
    assert data["state"] == "trusted"
    assert data["executable"] is False
    assert data["execution_allowed"] is False


def test_status_is_secret_free():
    runtime = make_runtime()

    runtime.register()
    runtime.trust_node()

    status = runtime.status()

    assert status["trusted"] is True
    assert status["executable"] is False
    assert status["execution_allowed"] is False
    assert "secret" not in status
    assert "credential" not in status
