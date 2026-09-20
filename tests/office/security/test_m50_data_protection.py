import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yoma.office.security import (
    DataClassification,
    DataClassificationEngine,
    DataAccessPolicy,
    DataAccessPolicyEngine,
    DataAccessDecision,
    SensitiveDataDetector,
    SensitiveDataType,
    DataLossPrevention,
    DLPDecision,
    DatabaseProtection,
    DatabaseOperation,
    DatabaseRequest,
    DocumentProtection,
    DocumentOperation,
    DocumentRequest,
    AIContextFirewall,
    AIContextDecision,
    DataMinimizer,
    RedactionMode,
    DataAccessAuditChain,
    DataProtectionRequest,
    DataProtectionRuntime,
)


def test_m50_1_classification():
    engine = DataClassificationEngine()

    assert engine.classify("public company website").classification == DataClassification.INTERNAL
    assert engine.classify("employee salary payroll").classification == DataClassification.CONFIDENTIAL
    assert engine.classify("api_key=SECRET_VALUE").classification == DataClassification.RESTRICTED


def test_m50_2_least_privilege_policy():
    engine = DataAccessPolicyEngine()

    denied = engine.evaluate(
        DataAccessPolicy(
            actor="employee",
            purpose="report",
            classification="CONFIDENTIAL",
            operation="READ",
            least_privilege=False,
        )
    )

    assert denied.decision == DataAccessDecision.DENY
    assert denied.executable is False


def test_m50_3_sensitive_detection():
    detector = SensitiveDataDetector()

    findings = detector.scan(
        "Contact user@example.com, phone 9876543210, password=Secret123"
    )

    kinds = {item.kind for item in findings}

    assert SensitiveDataType.EMAIL in kinds
    assert SensitiveDataType.PHONE in kinds
    assert SensitiveDataType.PASSWORD in kinds


def test_m50_4_dlp_blocks_protected_export():
    dlp = DataLossPrevention()

    result = dlp.assess(
        destination="external.example",
        sensitive_data_detected=True,
        classification="RESTRICTED",
        approved=False,
    )

    assert result.decision == DLPDecision.BLOCK
    assert result.executable is False


def test_m50_5_database_boundary():
    db = DatabaseProtection()

    read = db.assess(
        DatabaseRequest(
            actor="employee",
            operation=DatabaseOperation.READ,
            resource="employee_records",
            purpose="approved reporting",
        )
    )

    write = db.assess(
        DatabaseRequest(
            actor="employee",
            operation=DatabaseOperation.WRITE,
            resource="employee_records",
            purpose="modify record",
            approved=False,
        )
    )

    assert read.allowed is True
    assert read.adapter_required is True
    assert write.allowed is False


def test_m50_6_document_boundary():
    documents = DocumentProtection()

    result = documents.assess(
        DocumentRequest(
            actor="employee",
            operation=DocumentOperation.EXPORT,
            path="confidential/report.pdf",
            classification="CONFIDENTIAL",
            approved=False,
        )
    )

    assert result.allowed is False
    assert result.executable is False


def test_m50_7_ai_context_firewall():
    firewall = AIContextFirewall()

    result = firewall.inspect(
        {"employee": "salary"},
        classification="RESTRICTED",
        sensitive_findings=1,
        approved=False,
    )

    assert result.decision == AIContextDecision.REDACT
    assert result.executable is False


def test_m50_8_minimization():
    minimizer = DataMinimizer()

    result = minimizer.minimize(
        "Email user@example.com password=Secret123",
        mode=RedactionMode.MASK,
    )

    assert result.minimized is True
    assert result.redactions >= 2
    assert "user@example.com" not in result.value
    assert "Secret123" not in result.value


def test_m50_9_audit_chain():
    audit = DataAccessAuditChain()

    audit.append(
        actor="employee",
        operation="READ",
        resource="report",
        classification="INTERNAL",
        decision="ALLOW",
        purpose="reporting",
    )

    audit.append(
        actor="manager",
        operation="REVIEW",
        resource="report",
        classification="CONFIDENTIAL",
        decision="REVIEW",
        purpose="approval",
    )

    assert len(audit.events) == 2
    assert audit.verify() is True


def test_m50_10_unified_runtime():
    runtime = DataProtectionRuntime()

    result = runtime.inspect(
        DataProtectionRequest(
            actor="employee",
            purpose="prepare report",
            operation="READ",
            resource="employee_report",
            data="employee salary is 50000, contact user@example.com",
        )
    )

    status = runtime.status()

    assert result.requires_human_approval is True
    assert result.executable is False
    assert result.sensitive_findings
    assert result.minimized.minimized is True
    assert status["classification"] is True
    assert status["dlp"] is True
    assert status["database_protection"] is True
    assert status["document_protection"] is True
    assert status["ai_context_firewall"] is True
    assert status["audit_chain_valid"] is True
    assert status["requires_human_approval"] is True
    assert status["executable"] is False


def test_m50_no_self_authorization():
    runtime = DataProtectionRuntime()

    result = runtime.inspect(
        DataProtectionRequest(
            actor="ai",
            purpose="export records",
            operation="EXPORT",
            resource="restricted_records",
            data="password=supersecret",
            destination="external.example",
            approved=False,
            declared_classification="RESTRICTED",
        )
    )

    assert result.policy.decision == DataAccessDecision.DENY
    assert result.dlp.decision == DLPDecision.BLOCK
    assert result.ai_context.decision in {
        AIContextDecision.REDACT,
        AIContextDecision.BLOCK,
    }
    assert result.executable is False
    assert result.requires_human_approval is True


def test_m50_audit_does_not_store_raw_sensitive_data():
    runtime = DataProtectionRuntime()

    runtime.inspect(
        DataProtectionRequest(
            actor="employee",
            purpose="review",
            operation="READ",
            resource="private",
            data="password=SuperSecret123",
        )
    )

    event = runtime.audit.events[0]

    assert "SuperSecret123" not in str(event.as_dict())
    assert "password=" not in str(event.as_dict())


def test_m50_status_is_defensive():
    runtime = DataProtectionRuntime()
    status = runtime.status()

    assert status["active"] is True
    assert status["least_privilege"] is True
    assert status["requires_human_approval"] is True
    assert status["executable"] is False
