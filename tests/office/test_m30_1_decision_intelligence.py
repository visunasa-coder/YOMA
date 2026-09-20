"""Tests for M30.1 unified decision intelligence model."""

from datetime import datetime

import pytest

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


BASE = datetime(2026, 9, 5, 12, 0, 0)


def make_evidence():
    return DecisionIntelligenceEvidence(
        evidence_id="EV-1",
        evidence_type="predictive",
        source_id="PRED-1",
        description="Predicted workload pressure",
        weight=0.85,
    )


def make_decision(**overrides):
    values = {
        "decision_id": "DINT-ORG1-U1-workload_pressure",
        "decision_type": "workload_review",
        "created_at": BASE,
        "organization_id": "ORG1",
        "user_id": "U1",
        "situation_type": "workload_pressure",
        "priority": "high",
        "confidence": 0.82,
        "current_intelligence_available": True,
        "historical_intelligence_available": True,
        "predictive_intelligence_available": True,
        "current_decision_ids": ("DEC-1",),
        "historical_context_ids": ("HDEC-1",),
        "predictive_context_ids": ("PDEC-1",),
        "evidence": (make_evidence(),),
        "recommendation_type": "workload_review",
        "recommendation_reason": "Current workload is elevated and historical recurrence suggests continued pressure.",
    }
    values.update(overrides)
    return DecisionIntelligence(**values)


def test_basic_creation():
    decision = make_decision()

    assert decision.decision_id.startswith("DINT-")
    assert decision.decision_type == "workload_review"
    assert decision.confidence == 0.82


def test_intelligence_available():
    decision = make_decision()

    assert decision.intelligence_available is True


def test_current_context():
    decision = make_decision()

    assert decision.has_current_context is True


def test_historical_context():
    decision = make_decision()

    assert decision.has_historical_context is True


def test_predictive_context():
    decision = make_decision()

    assert decision.has_predictive_context is True


def test_evidence_count():
    decision = make_decision()

    assert decision.evidence_count == 1


def test_requires_review():
    decision = make_decision()

    assert decision.requires_review is True
    assert decision.requires_human_approval is True


def test_no_intelligence_available():
    decision = make_decision(
        current_intelligence_available=False,
        historical_intelligence_available=False,
        predictive_intelligence_available=False,
        current_decision_ids=(),
        historical_context_ids=(),
        predictive_context_ids=(),
        evidence=(),
    )

    assert decision.intelligence_available is False
    assert decision.evidence_count == 0


def test_confidence_validation():
    with pytest.raises(ValueError):
        make_decision(confidence=1.1)


def test_negative_confidence_validation():
    with pytest.raises(ValueError):
        make_decision(confidence=-0.1)


def test_priority_validation():
    with pytest.raises(ValueError):
        make_decision(priority="urgent")


def test_human_approval_cannot_be_disabled():
    with pytest.raises(ValueError):
        make_decision(requires_human_approval=False)


def test_decision_prefix_validation():
    with pytest.raises(ValueError):
        make_decision(decision_id="DEC-1")


def test_evidence_weight_validation():
    with pytest.raises(ValueError):
        DecisionIntelligenceEvidence(
            evidence_id="EV-1",
            evidence_type="current",
            source_id="SRC-1",
            weight=1.5,
        )


def test_deterministic_values_are_preserved():
    decision = make_decision()

    assert decision.organization_id == "ORG1"
    assert decision.user_id == "U1"
    assert decision.situation_type == "workload_pressure"
    assert decision.current_decision_ids == ("DEC-1",)
    assert decision.historical_context_ids == ("HDEC-1",)
    assert decision.predictive_context_ids == ("PDEC-1",)


def test_advisory_model_has_no_actions():
    decision = make_decision()

    assert not hasattr(decision, "actions")
