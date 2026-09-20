from datetime import datetime, timezone

import pytest

from yoma.office.operations import OperationalSignal
from yoma.office.operations.situation import (
    OperationalSituation,
    OperationalSituationCorrelator,
)


def make_signal(
    signal_id: str,
    signal_type: str,
    *,
    user_id: str | None = "U001",
    organization_id: str | None = "ORG001",
    score: float = 0.8,
    severity: str = "warning",
    evidence: tuple[str, ...] = (),
):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id=user_id,
        score=score,
        severity=severity,
        evidence_event_ids=evidence,
    )


def test_correlates_related_signals_for_same_user():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal(
            "SIG001",
            "workload.high",
            score=0.9,
            evidence=("EV001",),
        ),
        make_signal(
            "SIG002",
            "meeting_load.high",
            score=0.8,
            evidence=("EV002",),
        ),
    ]

    situations = correlator.correlate(signals)

    assert len(situations) == 1
    assert isinstance(situations[0], OperationalSituation)
    assert situations[0].user_id == "U001"
    assert situations[0].signal_ids == ("SIG001", "SIG002")


def test_unrelated_signal_types_remain_separate():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal("SIG001", "workload.high"),
        make_signal("SIG002", "security.alert"),
    ]

    situations = correlator.correlate(signals)

    assert len(situations) == 2


def test_different_users_are_not_correlated():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal("SIG001", "workload.high", user_id="U001"),
        make_signal("SIG002", "meeting_load.high", user_id="U002"),
    ]

    situations = correlator.correlate(signals)

    assert len(situations) == 2


def test_situation_preserves_evidence():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal(
            "SIG001",
            "workload.high",
            evidence=("EV001", "EV002"),
        ),
        make_signal(
            "SIG002",
            "meeting_load.high",
            evidence=("EV002", "EV003"),
        ),
    ]

    situations = correlator.correlate(signals)

    assert situations[0].evidence_event_ids == (
        "EV001",
        "EV002",
        "EV003",
    )


def test_situation_score_is_deterministic():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal("SIG001", "workload.high", score=0.9),
        make_signal("SIG002", "meeting_load.high", score=0.7),
    ]

    situations = correlator.correlate(signals)

    assert situations[0].score == pytest.approx(0.8)


def test_highest_severity_is_preserved():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal(
            "SIG001",
            "workload.high",
            severity="warning",
        ),
        make_signal(
            "SIG002",
            "meeting_load.high",
            severity="critical",
        ),
    ]

    situations = correlator.correlate(signals)

    assert situations[0].severity == "critical"


def test_empty_input_returns_no_situations():
    correlator = OperationalSituationCorrelator()

    assert correlator.correlate([]) == []


def test_correlation_is_deterministic():
    correlator = OperationalSituationCorrelator()

    signals = [
        make_signal("SIG002", "meeting_load.high"),
        make_signal("SIG001", "workload.high"),
    ]

    first = correlator.correlate(signals)
    second = correlator.correlate(list(reversed(signals)))

    assert first == second
