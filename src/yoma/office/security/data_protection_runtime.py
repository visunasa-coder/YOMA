from dataclasses import dataclass
from typing import Any, Mapping

from .ai_context_firewall import AIContextFirewall
from .data_access_audit import DataAccessAuditChain
from .data_classification import DataClassificationEngine
from .data_loss_prevention import DataLossPrevention
from .data_minimization import DataMinimizer
from .data_policy import DataAccessPolicy, DataAccessPolicyEngine
from .database_protection import DatabaseProtection, DatabaseRequest
from .document_protection import DocumentProtection, DocumentRequest
from .sensitive_data import SensitiveDataDetector


@dataclass(frozen=True)
class DataProtectionRequest:
    actor: str
    purpose: str
    operation: str
    resource: str
    data: str
    destination: str = ""
    approved: bool = False
    declared_classification: str | None = None


@dataclass(frozen=True)
class DataProtectionResult:
    classification: Any
    sensitive_findings: tuple[Any, ...]
    policy: Any
    dlp: Any
    ai_context: Any
    minimized: Any
    audit_event: Any
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.as_dict(),
            "sensitive_findings": [
                finding.as_dict() for finding in self.sensitive_findings
            ],
            "policy": self.policy.as_dict(),
            "dlp": self.dlp.as_dict(),
            "ai_context": self.ai_context.as_dict(),
            "minimized": self.minimized.as_dict(),
            "audit_event": self.audit_event.as_dict(),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DataProtectionRuntime:
    def __init__(self) -> None:
        self.classifier = DataClassificationEngine()
        self.detector = SensitiveDataDetector()
        self.policy = DataAccessPolicyEngine()
        self.dlp = DataLossPrevention()
        self.database = DatabaseProtection()
        self.documents = DocumentProtection()
        self.context_firewall = AIContextFirewall()
        self.minimizer = DataMinimizer()
        self.audit = DataAccessAuditChain()

    def inspect(self, request: DataProtectionRequest) -> DataProtectionResult:
        classification = self.classifier.classify(
            request.data,
            declared=request.declared_classification,
        )

        findings = self.detector.scan(request.data)

        policy = self.policy.evaluate(
            DataAccessPolicy(
                actor=request.actor,
                purpose=request.purpose,
                classification=classification.classification.value,
                operation=request.operation,
                approved=request.approved,
            )
        )

        dlp = self.dlp.assess(
            destination=request.destination or "internal",
            sensitive_data_detected=bool(findings),
            classification=classification.classification.value,
            approved=request.approved,
        )

        context = self.context_firewall.inspect(
            {"resource": request.resource},
            classification=classification.classification.value,
            sensitive_findings=len(findings),
            approved=request.approved,
        )

        minimized = self.minimizer.minimize(request.data)

        audit_event = self.audit.append(
            actor=request.actor,
            operation=request.operation,
            resource=request.resource,
            classification=classification.classification.value,
            decision=policy.decision.value,
            purpose=request.purpose,
        )

        return DataProtectionResult(
            classification=classification,
            sensitive_findings=findings,
            policy=policy,
            dlp=dlp,
            ai_context=context,
            minimized=minimized,
            audit_event=audit_event,
        )

    def status(self) -> dict[str, Any]:
        return {
            "active": True,
            "classification": True,
            "access_policy": True,
            "sensitive_data_detection": True,
            "dlp": True,
            "database_protection": True,
            "document_protection": True,
            "ai_context_firewall": True,
            "data_minimization": True,
            "audit_chain": True,
            "audit_chain_valid": self.audit.verify(),
            "least_privilege": True,
            "requires_human_approval": True,
            "executable": False,
        }
