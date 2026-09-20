"""YOMA M54 - Organization and administration control plane.

This module models:
Organization -> Users -> Departments -> Authority -> Devices -> Nodes.

It is deliberately separate from AI execution authority.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrganizationRole(str, Enum):
    FOUNDER = "founder"
    CEO = "ceo"
    DIRECTOR = "director"
    ADMINISTRATOR = "administrator"
    HR = "hr"
    FINANCE = "finance"
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    EMPLOYEE = "employee"
    READ_ONLY = "read_only"


class NodeType(str, Enum):
    SERVER = "server"
    ADMIN = "admin"
    EXECUTIVE = "executive"
    EMPLOYEE = "employee"
    EDGE = "edge"


class NodeState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    OFFLINE = "offline"
    REVOKED = "revoked"


class EnrollmentState(str, Enum):
    INVITED = "invited"
    ENROLLED = "enrolled"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    created_at: float
    active: bool = True


@dataclass(frozen=True)
class OrganizationUser:
    user_id: str
    organization_id: str
    display_name: str
    email: str
    role: OrganizationRole
    department_id: str | None
    manager_user_id: str | None
    enrollment: EnrollmentState = EnrollmentState.INVITED


@dataclass(frozen=True)
class Department:
    department_id: str
    organization_id: str
    name: str
    manager_user_id: str | None = None


@dataclass(frozen=True)
class AuthorityRule:
    rule_id: str
    organization_id: str
    role: OrganizationRole
    permission: str
    approval_required: bool = True
    approval_limit: float | None = None


@dataclass(frozen=True)
class YomaNode:
    node_id: str
    organization_id: str
    user_id: str | None
    node_type: NodeType
    device_name: str
    state: NodeState = NodeState.PENDING


@dataclass(frozen=True)
class EnrollmentToken:
    token_id: str
    organization_id: str
    user_id: str | None
    node_type: NodeType
    token_hash: str
    expires_at: float


class OrganizationControlPlane:
    """In-memory control-plane reference implementation.

    Persistence can be attached to the existing organization/runtime
    infrastructure without changing the public model.
    """

    def __init__(self):
        self.organizations: dict[str, Organization] = {}
        self.users: dict[str, OrganizationUser] = {}
        self.departments: dict[str, Department] = {}
        self.rules: dict[str, AuthorityRule] = {}
        self.nodes: dict[str, YomaNode] = {}
        self.tokens: dict[str, EnrollmentToken] = {}

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(8)}"

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()

    def create_organization(self, name: str) -> Organization:
        if not name.strip():
            raise ValueError("Organization name is required.")

        organization = Organization(
            organization_id=self._id("org"),
            name=name.strip(),
            created_at=time.time(),
        )

        self.organizations[organization.organization_id] = organization
        return organization

    def add_user(
        self,
        organization_id: str,
        display_name: str,
        email: str,
        role: OrganizationRole,
        department_id: str | None = None,
        manager_user_id: str | None = None,
    ) -> OrganizationUser:

        self.require_organization(organization_id)

        user = OrganizationUser(
            user_id=self._id("usr"),
            organization_id=organization_id,
            display_name=display_name.strip(),
            email=email.strip(),
            role=role,
            department_id=department_id,
            manager_user_id=manager_user_id,
        )

        self.users[user.user_id] = user
        return user

    def add_department(
        self,
        organization_id: str,
        name: str,
        manager_user_id: str | None = None,
    ) -> Department:

        self.require_organization(organization_id)

        department = Department(
            department_id=self._id("dep"),
            organization_id=organization_id,
            name=name.strip(),
            manager_user_id=manager_user_id,
        )

        self.departments[department.department_id] = department
        return department

    def add_authority_rule(
        self,
        organization_id: str,
        role: OrganizationRole,
        permission: str,
        approval_required: bool = True,
        approval_limit: float | None = None,
    ) -> AuthorityRule:

        self.require_organization(organization_id)

        rule = AuthorityRule(
            rule_id=self._id("rule"),
            organization_id=organization_id,
            role=role,
            permission=permission,
            approval_required=approval_required,
            approval_limit=approval_limit,
        )

        self.rules[rule.rule_id] = rule
        return rule

    def invite_user(self, user_id: str) -> str:
        user = self.require_user(user_id)

        raw = secrets.token_urlsafe(32)

        token = EnrollmentToken(
            token_id=self._id("enroll"),
            organization_id=user.organization_id,
            user_id=user.user_id,
            node_type=NodeType.EMPLOYEE,
            token_hash=self._hash(raw),
            expires_at=time.time() + 86400,
        )

        self.tokens[token.token_id] = token

        return raw

    def create_node_enrollment(
        self,
        organization_id: str,
        node_type: NodeType,
        user_id: str | None = None,
    ) -> str:

        self.require_organization(organization_id)

        raw = secrets.token_urlsafe(32)

        token = EnrollmentToken(
            token_id=self._id("enroll"),
            organization_id=organization_id,
            user_id=user_id,
            node_type=node_type,
            token_hash=self._hash(raw),
            expires_at=time.time() + 86400,
        )

        self.tokens[token.token_id] = token

        return raw

    def enroll_node(
        self,
        token_value: str,
        device_name: str,
    ) -> YomaNode:

        token_hash = self._hash(token_value)

        matches = [
            token for token in self.tokens.values()
            if token.token_hash == token_hash
            and token.expires_at > time.time()
        ]

        if not matches:
            raise PermissionError(
                "Invalid or expired enrollment token."
            )

        token = matches[0]

        node = YomaNode(
            node_id=self._id("node"),
            organization_id=token.organization_id,
            user_id=token.user_id,
            node_type=token.node_type,
            device_name=device_name,
            state=NodeState.ACTIVE,
        )

        self.nodes[node.node_id] = node

        return node

    def authority_for(
        self,
        user_id: str,
        permission: str,
    ) -> list[AuthorityRule]:

        user = self.require_user(user_id)

        return [
            rule
            for rule in self.rules.values()
            if rule.organization_id == user.organization_id
            and rule.role == user.role
            and rule.permission == permission
        ]

    def can_request(
        self,
        user_id: str,
        permission: str,
    ) -> bool:

        return bool(
            self.authority_for(
                user_id,
                permission,
            )
        )

    def require_organization(
        self,
        organization_id: str,
    ) -> Organization:

        if organization_id not in self.organizations:
            raise KeyError("Organization does not exist.")

        return self.organizations[organization_id]

    def require_user(self, user_id: str) -> OrganizationUser:
        if user_id not in self.users:
            raise KeyError("User does not exist.")

        return self.users[user_id]

    def dashboard(self, organization_id: str) -> dict[str, Any]:
        self.require_organization(organization_id)

        users = [
            user
            for user in self.users.values()
            if user.organization_id == organization_id
        ]

        departments = [
            dep
            for dep in self.departments.values()
            if dep.organization_id == organization_id
        ]

        nodes = [
            node
            for node in self.nodes.values()
            if node.organization_id == organization_id
        ]

        return {
            "organization_id": organization_id,
            "users": len(users),
            "departments": len(departments),
            "nodes": len(nodes),
            "active_nodes": sum(
                node.state == NodeState.ACTIVE
                for node in nodes
            ),
            "execution_authority": False,
            "self_authorized_execution": False,
            "requires_human_approval": True,
            "executable": False,
        }


class HierarchicalAuthorityResolver:
    """Resolves reporting/approval relationships without executing actions."""

    def __init__(self, control_plane: OrganizationControlPlane):
        self.control_plane = control_plane

    def chain(self, user_id: str) -> list[OrganizationUser]:
        current = self.control_plane.require_user(user_id)
        result = [current]

        visited = {current.user_id}

        while current.manager_user_id:
            if current.manager_user_id in visited:
                raise ValueError("Circular management hierarchy detected.")

            current = self.control_plane.require_user(
                current.manager_user_id
            )

            visited.add(current.user_id)
            result.append(current)

        return result

    def approvers(self, user_id: str) -> list[OrganizationUser]:
        return self.chain(user_id)[1:]


class M54OrganizationRuntime:
    def __init__(
        self,
        control_plane: OrganizationControlPlane | None = None,
    ):
        self.control_plane = (
            control_plane or OrganizationControlPlane()
        )

        self.authority = HierarchicalAuthorityResolver(
            self.control_plane
        )

    def status(self) -> dict[str, Any]:
        return {
            "active": True,
            "organization_control_plane": True,
            "user_enrollment": True,
            "department_management": True,
            "hierarchical_authority": True,
            "device_enrollment": True,
            "node_enrollment": True,
            "server_deployment": True,
            "distributed_edge_deployment": True,
            "execution_authority": False,
            "self_authorized_execution": False,
            "requires_human_approval": True,
            "executable": False,
        }
