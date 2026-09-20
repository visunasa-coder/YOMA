"""M53/M54 dedicated regression."""

import json

from yoma.office.security.m53 import (
    FirstRunSetupWizard,
    GoogleProvisioningManager,
    OAuthJsonValidator,
    ProvisioningState,
    SecureProvisioningStore,
    SetupStep,
    YomaSetupService,
)

from yoma.office.security.m54 import (
    M54OrganizationRuntime,
    NodeType,
    OrganizationControlPlane,
    OrganizationRole,
)


def oauth_payload():
    return {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "secret-for-test-only",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def test_m53_welcome():
    data = FirstRunSetupWizard.welcome()

    assert data["product"] == "YOMA"
    assert data["features"]
    assert data["execution_authorized"] is False
    assert data["executable"] is False


def test_m53_valid_oauth():
    result = OAuthJsonValidator.validate(oauth_payload())

    assert result.valid
    assert result.client_type == "installed"
    assert result.has_client_id
    assert result.has_client_secret
    assert result.fingerprint


def test_m53_invalid_oauth():
    result = OAuthJsonValidator.validate({"bad": True})

    assert result.valid is False


def test_m53_file_import(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(oauth_payload()),
        encoding="utf-8",
    )

    store = SecureProvisioningStore(tmp_path / "store")
    manager = GoogleProvisioningManager(store)

    result = manager.import_oauth_json(path)

    assert result.valid
    assert store.has_credentials()
    assert store.get_state() == ProvisioningState.VALIDATED


def test_m53_authorization_flow(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(oauth_payload()),
        encoding="utf-8",
    )

    manager = GoogleProvisioningManager(
        SecureProvisioningStore(tmp_path / "store")
    )

    assert manager.import_oauth_json(path).valid
    assert manager.begin_authorization()
    assert manager.mark_authorized()
    assert manager.mark_connection_tested(True)

    assert manager.status().state == ProvisioningState.ACTIVE


def test_m53_connection_requires_authorization(tmp_path):
    manager = GoogleProvisioningManager(
        SecureProvisioningStore(tmp_path / "store")
    )

    assert manager.mark_connection_tested(True) is False


def test_m53_secret_not_in_status(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(oauth_payload()),
        encoding="utf-8",
    )

    manager = GoogleProvisioningManager(
        SecureProvisioningStore(tmp_path / "store")
    )

    manager.import_oauth_json(path)

    status = json.dumps(manager.status().as_dict())

    assert "secret-for-test-only" not in status
    assert "client_secret" not in status
    assert "refresh_token" not in status


def test_m53_service_boundary(tmp_path):
    service = YomaSetupService(tmp_path / "store")

    assert service.execution_authorized() is False
    assert service.executable() is False
    assert service.requires_human_approval() is True


def test_m53_steps():
    assert SetupStep.WELCOME.value == "welcome"
    assert SetupStep.JSON_IMPORT.value == "json_import"
    assert SetupStep.AUTHORIZATION.value == "authorization"
    assert SetupStep.COMPLETE.value == "complete"


def test_m54_create_organization():
    cp = OrganizationControlPlane()

    org = cp.create_organization("Example Company")

    assert org.organization_id in cp.organizations
    assert org.name == "Example Company"


def test_m54_hierarchy():
    cp = OrganizationControlPlane()

    org = cp.create_organization("Example Company")

    founder = cp.add_user(
        org.organization_id,
        "Founder",
        "founder@example.com",
        OrganizationRole.FOUNDER,
    )

    ceo = cp.add_user(
        org.organization_id,
        "CEO",
        "ceo@example.com",
        OrganizationRole.CEO,
        manager_user_id=founder.user_id,
    )

    manager = cp.add_user(
        org.organization_id,
        "Manager",
        "manager@example.com",
        OrganizationRole.MANAGER,
        manager_user_id=ceo.user_id,
    )

    employee = cp.add_user(
        org.organization_id,
        "Employee",
        "employee@example.com",
        OrganizationRole.EMPLOYEE,
        manager_user_id=manager.user_id,
    )

    runtime = M54OrganizationRuntime(cp)

    chain = runtime.authority.chain(employee.user_id)

    assert [user.role for user in chain] == [
        OrganizationRole.EMPLOYEE,
        OrganizationRole.MANAGER,
        OrganizationRole.CEO,
        OrganizationRole.FOUNDER,
    ]


def test_m54_authority_rule():
    cp = OrganizationControlPlane()
    org = cp.create_organization("Example")

    manager = cp.add_user(
        org.organization_id,
        "Manager",
        "manager@example.com",
        OrganizationRole.MANAGER,
    )

    cp.add_authority_rule(
        org.organization_id,
        OrganizationRole.MANAGER,
        "approve.expense",
    )

    assert cp.can_request(
        manager.user_id,
        "approve.expense",
    )


def test_m54_node_enrollment():
    cp = OrganizationControlPlane()

    org = cp.create_organization("Example")

    user = cp.add_user(
        org.organization_id,
        "Employee",
        "employee@example.com",
        OrganizationRole.EMPLOYEE,
    )

    token = cp.create_node_enrollment(
        org.organization_id,
        NodeType.EMPLOYEE,
        user.user_id,
    )

    node = cp.enroll_node(
        token,
        "EMPLOYEE-PC",
    )

    assert node.organization_id == org.organization_id
    assert node.user_id == user.user_id
    assert node.node_type == NodeType.EMPLOYEE


def test_m54_invalid_enrollment():
    cp = OrganizationControlPlane()
    org = cp.create_organization("Example")

    cp.create_node_enrollment(
        org.organization_id,
        NodeType.EMPLOYEE,
    )

    try:
        cp.enroll_node(
            "invalid-token",
            "PC",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "Invalid enrollment token was accepted."
        )


def test_m54_circular_hierarchy_blocked():
    cp = OrganizationControlPlane()
    org = cp.create_organization("Example")

    a = cp.add_user(
        org.organization_id,
        "A",
        "a@example.com",
        OrganizationRole.MANAGER,
    )

    b = cp.add_user(
        org.organization_id,
        "B",
        "b@example.com",
        OrganizationRole.MANAGER,
        manager_user_id=a.user_id,
    )

    cp.users[a.user_id] = type(a)(
        user_id=a.user_id,
        organization_id=a.organization_id,
        display_name=a.display_name,
        email=a.email,
        role=a.role,
        department_id=a.department_id,
        manager_user_id=b.user_id,
        enrollment=a.enrollment,
    )

    runtime = M54OrganizationRuntime(cp)

    try:
        runtime.authority.chain(a.user_id)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Circular hierarchy was not detected."
        )


def test_m54_dashboard_is_tenant_scoped():
    cp = OrganizationControlPlane()

    org1 = cp.create_organization("Company A")
    org2 = cp.create_organization("Company B")

    cp.add_user(
        org1.organization_id,
        "A",
        "a@example.com",
        OrganizationRole.EMPLOYEE,
    )

    cp.add_user(
        org2.organization_id,
        "B",
        "b@example.com",
        OrganizationRole.EMPLOYEE,
    )

    assert cp.dashboard(org1.organization_id)["users"] == 1
    assert cp.dashboard(org2.organization_id)["users"] == 1


def test_m54_runtime_boundary():
    status = M54OrganizationRuntime().status()

    assert status["organization_control_plane"]
    assert status["user_enrollment"]
    assert status["hierarchical_authority"]
    assert status["device_enrollment"]
    assert status["server_deployment"]
    assert status["distributed_edge_deployment"]
    assert status["execution_authority"] is False
    assert status["self_authorized_execution"] is False
    assert status["requires_human_approval"] is True
    assert status["executable"] is False
