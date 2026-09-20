from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationAnalysis,
    DistributedOrganizationIdentity,
    DistributedOrganizationIdentityManager,
    analyze_distributed_organization,
)


def make_organization():
    return DistributedOrganizationIdentity(
        organization_id="org-1",
        organization_name="Jeeven Tech",
        deployment_id="deployment-1",
    )


def make_node(node_id="node-1"):
    return DistributedNodeIdentity(
        node_id=node_id,
        organization_id="org-1",
        deployment_id="deployment-1",
        node_name="Employee-PC",
    )


def test_organization_identity_creation():
    identity = make_organization()

    assert identity.organization_id == "org-1"
    assert identity.organization_name == "Jeeven Tech"
    assert identity.deployment_id == "deployment-1"
    assert identity.edition == "distributed"


def test_node_identity_creation():
    node = make_node()

    assert node.node_id == "node-1"
    assert node.organization_id == "org-1"
    assert node.node_type == "employee_pc"


def test_identity_key_is_deterministic():
    identity = make_organization()

    assert identity.identity_key == "org-1:deployment-1"


def test_node_identity_key_is_deterministic():
    node = make_node()

    assert node.identity_key == "org-1:deployment-1:node-1"


def test_node_belongs_to_organization():
    assert make_node().belongs_to(make_organization()) is True


def test_foreign_node_rejected():
    node = DistributedNodeIdentity(
        node_id="node-2",
        organization_id="org-2",
        deployment_id="deployment-2",
        node_name="Other-PC",
    )

    assert node.belongs_to(make_organization()) is False


def test_analysis_with_valid_nodes():
    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (make_node(),),
    )

    assert isinstance(result, DistributedOrganizationAnalysis)
    assert result.valid is True
    assert result.node_count == 1
    assert result.issues == ()


def test_empty_node_set_is_valid():
    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (),
    )

    assert result.valid is True
    assert result.node_count == 0


def test_foreign_node_is_reported():
    foreign = DistributedNodeIdentity(
        node_id="node-2",
        organization_id="org-2",
        deployment_id="deployment-2",
        node_name="Other-PC",
    )

    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (foreign,),
    )

    assert result.valid is False
    assert len(result.issues) == 1


def test_duplicate_node_is_reported():
    node = make_node()

    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (node, node),
    )

    assert result.valid is False
    assert any(
        "duplicate node_id" in issue
        for issue in result.issues
    )


def test_invalid_organization_type():
    try:
        DistributedOrganizationIdentityManager().analyze(None)
    except TypeError:
        pass
    else:
        raise AssertionError(
            "invalid organization type must fail"
        )


def test_invalid_nodes_container():
    try:
        DistributedOrganizationIdentityManager().analyze(
            make_organization(),
            [],
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "nodes must be a tuple"
        )


def test_invalid_node_type():
    try:
        DistributedOrganizationIdentityManager().analyze(
            make_organization(),
            ("invalid",),
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "invalid node type must fail"
        )


def test_identity_validation():
    try:
        DistributedOrganizationIdentity(
            organization_id="",
            organization_name="Test",
            deployment_id="d1",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "empty organization_id must fail"
        )


def test_node_validation():
    try:
        DistributedNodeIdentity(
            node_id="",
            organization_id="org-1",
            deployment_id="d1",
            node_name="PC",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "empty node_id must fail"
        )


def test_secret_free_metadata():
    identity = make_organization()
    data = identity.as_dict()

    assert "password" not in data
    assert "token" not in data
    assert "secret" not in data


def test_node_metadata_is_secret_free():
    data = make_node().as_dict()

    assert "password" not in data
    assert "token" not in data
    assert "secret" not in data


def test_governance_boundary():
    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (make_node(),),
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_analysis_is_deterministic():
    manager = DistributedOrganizationIdentityManager()
    organization = make_organization()
    nodes = (make_node(),)

    first = manager.analyze(organization, nodes)
    second = manager.analyze(organization, nodes)

    assert first == second


def test_helper_function():
    result = analyze_distributed_organization(
        make_organization(),
        (make_node(),),
    )

    assert result.organization_id == "org-1"
    assert result.valid is True


def test_analysis_has_no_execution_authority():
    result = DistributedOrganizationIdentityManager().analyze(
        make_organization(),
        (make_node(),),
    )

    assert not hasattr(result, "execute")
    assert not hasattr(result, "authorize")
    assert not hasattr(result, "approve")
