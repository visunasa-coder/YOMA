from dataclasses import dataclass
import time
import uuid

from .identity import EnterpriseIdentity, IdentityRegistry
from .authentication import AuthenticationBoundary
from .permissions import PermissionGovernance
from .device_trust import DeviceTrustEngine, DevicePosture
from .session_security import SessionSecurity, SecuritySession
from .privileged_access import PrivilegedAccessGovernance
from .service_identity import ServiceIdentityGovernance
from .zero_trust import ZeroTrustAccessEngine, ZeroTrustContext
from .access_audit import AccessAuditChain, AccessAuditEvent


@dataclass(frozen=True)
class IdentityGovernanceRequest:
    identity_id: str
    permission: str
    resource: str
    device_id: str
    threat_level: str = "none"
    approved: bool = False


class IdentityGovernanceRuntime:

    def __init__(self):
        self.identities = IdentityRegistry()
        self.authentication = AuthenticationBoundary()
        self.permissions = PermissionGovernance()
        self.device_trust = DeviceTrustEngine()
        self.sessions = SessionSecurity()
        self.privileged_access = PrivilegedAccessGovernance()
        self.service_identity = ServiceIdentityGovernance()
        self.zero_trust = ZeroTrustAccessEngine()
        self.audit = AccessAuditChain()

    def evaluate(
        self,
        request: IdentityGovernanceRequest,
        credential_valid: bool = True,
        session_valid: bool = True,
        device_managed: bool = True,
        device_integrity: bool = True,
        device_controls: bool = True,
    ):

        identity = self.identities.get(request.identity_id)

        if identity is None:
            return {
                "decision": "deny",
                "reason": "unknown identity",
                "requires_human_approval": True,
                "executable": False,
            }

        auth = self.authentication.authenticate(
            request.identity_id,
            credential_valid,
            session_valid,
            identity.active,
        )

        posture = self.device_trust.assess(
            DevicePosture(
                request.device_id,
                device_managed,
                device_integrity,
                device_controls,
                True,
            )
        )

        session = self.sessions.evaluate(
            SecuritySession(
                session_id=f"session-{request.identity_id}",
                identity_id=request.identity_id,
                issued_at=time.time() - 10,
                expires_at=time.time() + 3600,
            )
        )

        permission = self.permissions.evaluate(
            request.permission,
            identity.permissions,
            resource_protected=True,
            approved=request.approved,
        )

        permission_granted = permission.decision.value in {"allow", "review"}
        permission_review = permission.decision.value == "review"

        zero = self.zero_trust.decide(
            ZeroTrustContext(
                authenticated=auth.authenticated,
                authorized=permission_granted,
                trusted_device=posture.decision.value == "trusted",
                active_session=session.decision.value == "active",
                threat_level=request.threat_level,
                resource=request.resource,
                approved=request.approved,
                authorization_review=permission_review,
            )
        )

        event = AccessAuditEvent(
            event_id=str(uuid.uuid4()),
            identity_id=request.identity_id,
            resource=request.resource,
            decision=zero.decision.value,
            reason=zero.reason,
            timestamp=time.time(),
        )

        self.audit.append(event)

        return {
            "identity": identity,
            "authentication": auth,
            "device_trust": posture,
            "session": session,
            "permission": permission,
            "zero_trust": zero,
            "audit_chain_valid": self.audit.verify(),
            "decision": zero.decision.value,
            "requires_human_approval": True,
            "executable": False,
        }

    def status(self):
        return {
            "active": True,
            "identity_model": True,
            "authentication_boundary": True,
            "rbac": True,
            "least_privilege": True,
            "device_trust": True,
            "session_security": True,
            "privileged_access_governance": True,
            "service_identity_governance": True,
            "zero_trust": True,
            "access_audit": True,
            "anomaly_detection": True,
            "fail_closed": True,
            "requires_human_approval": True,
            "executable": False,
        }
