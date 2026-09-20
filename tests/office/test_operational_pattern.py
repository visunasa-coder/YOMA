from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.organization_graph import (
    OrganizationGraph,
    OrganizationGraphNode,
)
from yoma.office.operations import (
    OperationalSituation,
    OperationalSituationContext,
    OperationalPattern,
    OperationalPatternCorrelator,
)


def make_situation(
    situation_id: str,
    *,
    user_id: str | None = None,
    system_id: str | None = None,
    score: float = 0.8,
    severity: str = "warning",
    signals: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
) -> OperationalSituation:
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=datetime(
            2026, 9, 5, 10, 0, tzinfo=timezone.utc
        ),
        organization_id="ORG001",
        user_id=user_id,
        system_id=system_id,
        score=score,
        severity=severity,
        signal_ids=signals,
        evidence_event_ids=evidence,
    )


def make_context(
    situation: OperationalSituation,
    *,
    team: str | None = None,
    department: str | None = None,
    location: str | None = None,
    organization: str | None = "ORG001",
) -> OperationalSituationContext:
    def node(node_id: str | None, node_type: str):
        if node_id is None:
            return None
        return OrganizationGraphNode(
            node_id=node_id,
            node_type=node_type,
            name=node_id,
        )

    return OperationalSituationContext(
        situation=situation,
        employee_id=situation.user_id,
        team=node(team, "team"),
        department=node(department, "department"),
        location=node(location, "location"),
        organization=node(organization, "organization"),
    )


def test_correlates_situations_by_explicit_team():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation(
                "SIT001",
                user_id="EMP001",
                signals=("SIG001",),
            ),
            team="TEAM001",
            department="DEP001",
        ),
        make_context(
            make_situation(
                "SIT002",
                user_id="EMP002",
                signals=("SIG002",),
            ),
            team="TEAM001",
            department="DEP001",
        ),
    ]

    patterns = correlator.correlate(contexts)

    assert len(patterns) == 2
    team_patterns = [
        pattern
        for pattern in patterns
        if pattern.correlation_dimension == "team"
    ]

    assert len(team_patterns) == 1
    assert team_patterns[0].correlation_id == "TEAM001"
    assert team_patterns[0].situation_ids == (
        "SIT001",
        "SIT002",
    )


def test_does_not_correlate_unrelated_teams():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation("SIT001", user_id="EMP001"),
            team="TEAM001",
        ),
        make_context(
            make_situation("SIT002", user_id="EMP002"),
            team="TEAM002",
        ),
    ]

    patterns = correlator.correlate(contexts)

    assert not any(
        pattern.correlation_dimension == "team"
        for pattern in patterns
    )


def test_correlates_by_department_when_team_is_missing():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation("SIT001", user_id="EMP001"),
            department="DEP001",
        ),
        make_context(
            make_situation("SIT002", user_id="EMP002"),
            department="DEP001",
        ),
    ]

    patterns = correlator.correlate(contexts)

    assert any(
        pattern.correlation_dimension == "department"
        and pattern.correlation_id == "DEP001"
        for pattern in patterns
    )


def test_preserves_situation_signal_and_evidence_ids():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation(
                "SIT001",
                user_id="EMP001",
                signals=("SIG002",),
                evidence=("EV002",),
            ),
            team="TEAM001",
        ),
        make_context(
            make_situation(
                "SIT002",
                user_id="EMP002",
                signals=("SIG001",),
                evidence=("EV001",),
            ),
            team="TEAM001",
        ),
    ]

    patterns = correlator.correlate(contexts)

    pattern = next(
        pattern
        for pattern in patterns
        if pattern.correlation_dimension == "team"
    )

    assert pattern.situation_ids == ("SIT001", "SIT002")
    assert pattern.signal_ids == ("SIG001", "SIG002")
    assert pattern.evidence_event_ids == ("EV001", "EV002")


def test_pattern_score_is_deterministic():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation(
                "SIT001",
                user_id="EMP001",
                score=0.9,
            ),
            team="TEAM001",
        ),
        make_context(
            make_situation(
                "SIT002",
                user_id="EMP002",
                score=0.7,
            ),
            team="TEAM001",
        ),
    ]

    patterns = correlator.correlate(contexts)

    pattern = next(
        pattern
        for pattern in patterns
        if pattern.correlation_dimension == "team"
    )

    assert pattern.score == pytest.approx(0.8)


def test_highest_severity_is_preserved():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation(
                "SIT001",
                user_id="EMP001",
                severity="warning",
            ),
            team="TEAM001",
        ),
        make_context(
            make_situation(
                "SIT002",
                user_id="EMP002",
                severity="critical",
            ),
            team="TEAM001",
        ),
    ]

    patterns = correlator.correlate(contexts)

    pattern = next(
        pattern
        for pattern in patterns
        if pattern.correlation_dimension == "team"
    )

    assert pattern.severity == "critical"


def test_single_situation_does_not_create_pattern():
    correlator = OperationalPatternCorrelator()

    contexts = [
        make_context(
            make_situation("SIT001", user_id="EMP001"),
            team="TEAM001",
        ),
    ]

    assert correlator.correlate(contexts) == []


def test_correlation_is_deterministic():
    correlator = OperationalPatternCorrelator()

    first_context = make_context(
        make_situation("SIT001", user_id="EMP001"),
        team="TEAM001",
    )
    second_context = make_context(
        make_situation("SIT002", user_id="EMP002"),
        team="TEAM001",
    )

    first = correlator.correlate(
        [first_context, second_context]
    )
    second = correlator.correlate(
        [second_context, first_context]
    )

    assert first == second
