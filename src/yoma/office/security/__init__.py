"""
YOMA Security Package.

M47-M52 security layers.

Security modules provide defensive decisions only.
Execution authority remains outside this package.
"""

from .unified_policy import (
    SecurityEnforcementDecision,
    UnifiedSecurityDecision,
    UnifiedSecurityPolicyPlane,
)
from .cross_layer_enforcement import (
    CrossLayerSecurityEnforcer,
    SecurityLayerState,
)
from .precedence import (
    SecurityPrecedence,
    SecurityDecisionPrecedence,
)
from .security_context import SecurityContext
from .enforcement_boundary import (
    EnforcementBoundaryResult,
    FinalSecurityEnforcementBoundary,
)
from .security_state import SecurityState, SecurityStatePropagator
from .integration_security import (
    IntegrationSecurityResult,
    EnterpriseIntegrationSecurity,
)
from .fail_safe import SecurityFailSafe, SecurityFailSafeState
from .verification import SecurityVerificationCase, SecurityVerificationEngine
from .unified_runtime import (
    UnifiedSecurityRuntime,
    UnifiedSecurityRuntimeResult,
)

# Explicitly retain previously implemented public security APIs
# where available. This avoids M50-style package export regressions.
for _module_name, _names in {
    "core": (
        "SecurityCore",
        "SecurityDecision",
        "ThreatLevel",
        "TrustLevel",
        "SecurityAssessment",
    ),
    "rbac": (
        "RBAC",
        "SecurityRole",
        "SecurityIdentity",
    ),
    "request_guard": (
        "RequestGuard",
        "RateLimiter",
    ),
    "threat_detection": (
        "ThreatDetector",
        "ThreatCategory",
        "ThreatAssessment",
    ),
    "audit": (
        "SecurityAuditEvent",
        "SecurityAuditChain",
    ),
    "data_guard": (
        "FileGuard",
        "DatabaseGuard",
    ),
    "runtime": (
        "SecurityRuntime",
    ),
    "host_policy": (
        "HostSecurityPolicy",
    ),
    "host_access": (
        "HostAccessController",
        "HostAccessResult",
    ),
    "secret_boundary": (
        "HostSecretBoundary",
        "SecretBoundaryResult",
    ),
    "integrity": (
        "BinaryIntegrityVerifier",
        "IntegrityResult",
    ),
    "process_monitor": (
        "ProcessMonitor",
        "ProcessObservation",
    ),
    "configuration_integrity": (
        "ConfigurationIntegrityMonitor",
        "ConfigurationIntegrityResult",
    ),
    "filesystem_monitor": (
        "FilesystemMonitor",
        "FilesystemObservation",
    ),
    "adaptive_defense": (
        "AdaptiveAttackDefense",
        "AttackSignal",
        "AttackDecision",
    ),
    "containment": (
        "HostContainmentController",
        "ContainmentResult",
    ),
    "host_runtime": (
        "HostSecurityRuntime",
    ),
    "incident_events": (
        "SecurityEvent",
        "SecurityEventNormalizer",
        "SecurityEventType",
        "IncidentSeverity",
        "IncidentState",
    ),
    "incident_correlation": (
        "SecurityEventCorrelator",
        "CorrelationResult",
    ),
    "incident_detection": (
        "IncidentDetector",
        "IncidentDetection",
    ),
    "incident_timeline": (
        "IncidentTimeline",
        "IncidentEvidenceTimeline",
    ),
    "investigation": (
        "SecurityInvestigationEngine",
        "InvestigationResult",
    ),
    "response_advisor": (
        "ResponseAdvisor",
        "ResponseRecommendation",
    ),
    "incident_workflow": (
        "IncidentResponseWorkflow",
        "IncidentApprovalWorkflow",
    ),
    "incident_recovery": (
        "IncidentRecoveryManager",
        "RecoveryAssessment",
    ),
    "operations_dashboard": (
        "SecurityOperationsDashboard",
        "SecurityOperationsStatus",
    ),
    "operations_runtime": (
        "SecurityOperationsRuntime",
    ),
    "data_protection": (
        "DataClassification",
        "DataSensitivity",
        "DataSubject",
        "DataClassificationResult",
        "DataClassificationEngine",
    ),
    "data_policy": (
        "DataAccessDecision",
        "DataAccessPolicy",
        "DataAccessPolicyResult",
        "DataAccessPolicyEngine",
    ),
    "sensitive_data": (
        "SensitiveDataType",
        "SensitiveFinding",
        "SensitiveDataDetector",
    ),
    "data_loss_prevention": (
        "DLPDecision",
        "DLPAssessment",
        "DataLossPrevention",
    ),
    "database_protection": (
        "DatabaseOperation",
        "DatabaseRequest",
        "DatabaseProtectionResult",
        "DatabaseProtection",
    ),
    "document_protection": (
        "DocumentOperation",
        "DocumentRequest",
        "DocumentProtectionResult",
        "DocumentProtection",
    ),
    "ai_context_firewall": (
        "AIContextDecision",
        "AIContextAssessment",
        "AIContextFirewall",
    ),
    "data_minimization": (
        "RedactionMode",
        "DataMinimizationResult",
        "DataMinimizer",
    ),
    "data_access_audit": (
        "DataAccessAuditEvent",
        "DataAccessAuditChain",
    ),
    "data_protection_runtime": (
        "DataProtectionRuntime",
        "DataProtectionRequest",
        "DataProtectionResult",
    ),
    "identity": (
        "Identity",
        "IdentityType",
    ),
    "authentication": (
        "AuthenticationBoundary",
    ),
    "permissions": (
        "PermissionGovernance",
    ),
    "device_trust": (
        "DeviceTrustEngine",
    ),
    "session_security": (
        "SessionSecurity",
    ),
    "privileged_access": (
        "PrivilegedAccessGovernance",
    ),
    "service_identity": (
        "ServiceIdentityManager",
    ),
    "zero_trust": (
        "ZeroTrustAccessDecision",
        "ZeroTrustEngine",
    ),
    "access_audit": (
        "AccessAuditChain",
    ),
    "identity_runtime": (
        "IdentityGovernanceRuntime",
    ),
}.items():
    try:
        _module = __import__(
            f"{__name__}.{_module_name}",
            fromlist=list(_names),
        )
        for _name in _names:
            if hasattr(_module, _name):
                globals()[_name] = getattr(_module, _name)
    except Exception:
        # Never make unrelated historical security imports fatal.
        pass

__all__ = [
    "SecurityEnforcementDecision",
    "UnifiedSecurityDecision",
    "UnifiedSecurityPolicyPlane",
    "CrossLayerSecurityEnforcer",
    "SecurityLayerState",
    "SecurityPrecedence",
    "SecurityDecisionPrecedence",
    "SecurityContext",
    "FinalSecurityEnforcementBoundary",
    "EnforcementBoundaryResult",
    "SecurityState",
    "SecurityStatePropagator",
    "EnterpriseIntegrationSecurity",
    "IntegrationSecurityResult",
    "SecurityFailSafe",
    "SecurityFailSafeState",
    "SecurityVerificationEngine",
    "SecurityVerificationCase",
    "UnifiedSecurityRuntime",
    "UnifiedSecurityRuntimeResult",
]


# M48 compatibility exports - actual implementation names
from .configuration_integrity import ConfigurationIntegrity, ConfigurationIntegrityResult, ConfigurationSnapshot


# M48 compatibility exports - repaired by M52 integration validation
from .adaptive_defense import AdaptiveAttackDefense
from .configuration_integrity import ConfigurationSnapshot
from .containment import EmergencyContainment
from .filesystem_monitor import FileSystemMonitor
from .filesystem_monitor import FileSystemObservation
from .host_access import HostAccessBoundary
from .host_access import HostIdentity
from .host_policy import HostSecurityPolicy
from .host_runtime import HostSecurityRuntime
from .host_access import HostTrustState
from .integrity import IntegrityVerifier
from .process_monitor import ProcessMonitor
from .process_monitor import ProcessObservation
from .process_monitor import ProcessRisk
from .secret_boundary import SecretBoundary
from .adaptive_defense import SourceBlockState
from .adaptive_defense import SecuritySignal

# M53 - First-run provisioning
from .provisioning import (
    FirstRunSetupWizard,
    GoogleProvisioningManager,
    OAuthJsonValidator,
    OAuthValidationResult,
    ProvisioningState,
    ProvisioningStatus,
    SecureProvisioningStore,
    SetupStep,
)
from .setup_service import YomaSetupService

# M54 - Organization control plane
from .organization_control_plane import (
    AuthorityRule,
    Department,
    EnrollmentState,
    EnrollmentToken,
    HierarchicalAuthorityResolver,
    M54OrganizationRuntime,
    NodeState,
    NodeType,
    Organization,
    OrganizationControlPlane,
    OrganizationRole,
    OrganizationUser,
    YomaNode,
)
