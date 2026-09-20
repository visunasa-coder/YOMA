from __future__ import annotations

import pytest

from yoma.office.security import (
    SecurityCore,
    SecurityDecision,
    ThreatLevel,
    TrustLevel,
)


def test_denies_unauthenticated_request():
    result = SecurityCore().assess(
        authenticated=False,
        authorized=False,
    )

    assert result.decision is SecurityDecision.DENY
    assert result.reason == "authentication required"
    assert result.executable is False


def test_denies_unauthorized_request():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=False,
        trust_level=TrustLevel.TRUSTED,
    )

    assert result.decision is SecurityDecision.DENY
    assert result.reason == "authorization required"


def test_denies_invalid_request():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        request_valid=False,
    )

    assert result.decision is SecurityDecision.DENY
    assert result.reason == "request validation failed"


def test_denies_high_threat():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.HIGH,
        approval_present=True,
    )

    assert result.decision is SecurityDecision.DENY
    assert result.threat_level is ThreatLevel.HIGH


def test_denies_critical_threat():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.CRITICAL,
        approval_present=True,
    )

    assert result.decision is SecurityDecision.DENY


def test_unknown_trust_requires_review():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.UNKNOWN,
    )

    assert result.decision is SecurityDecision.REVIEW


def test_untrusted_identity_requires_review():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.UNTRUSTED,
    )

    assert result.decision is SecurityDecision.REVIEW


def test_medium_threat_requires_review():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.MEDIUM,
    )

    assert result.decision is SecurityDecision.REVIEW


def test_missing_governed_approval_requires_review():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.NONE,
        approval_present=False,
    )

    assert result.decision is SecurityDecision.REVIEW
    assert result.executable is False


def test_fully_satisfied_security_state():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.NONE,
        approval_present=True,
    )

    assert result.decision is SecurityDecision.ALLOW
    assert result.executable is False
    assert result.requires_human_approval is True


def test_serialization_is_safe():
    result = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        approval_present=True,
    )

    data = result.as_dict()

    assert data["decision"] == "allow"
    assert data["trust_level"] == "trusted"
    assert data["threat_level"] == "none"
    assert data["requires_human_approval"] is True
    assert data["executable"] is False


def test_invalid_boolean_is_rejected():
    with pytest.raises(TypeError):
        SecurityCore().assess(
            authenticated="yes",
            authorized=True,
        )


def test_invalid_threat_level_is_rejected():
    with pytest.raises(ValueError):
        SecurityCore().assess(
            authenticated=True,
            authorized=True,
            threat_level="extreme",
        )


def test_invalid_trust_level_is_rejected():
    with pytest.raises(ValueError):
        SecurityCore().assess(
            authenticated=True,
            authorized=True,
            trust_level="unknown-super-user",
        )
