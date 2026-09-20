from datetime import datetime, timezone

from yoma.office.it.it_tickets import (
    ITIncident,
    ITServiceLevelAgreement,
    ITTicket,
    ITTicketIncidentIntelligence,
    ITTicketIncidentPortfolio,
)


def test_ticket_creation():
    assert ITTicket("t1", "org-1", "API issue").status == "open"


def test_invalid_ticket_status():
    try:
        ITTicket("t1", "org-1", "Issue", status="unknown")
        assert False
    except ValueError:
        assert True


def test_invalid_ticket_priority():
    try:
        ITTicket("t1", "org-1", "Issue", priority="urgent")
        assert False
    except ValueError:
        assert True


def test_ticket_due_date_timezone():
    try:
        ITTicket("t1", "org-1", "Issue", due_at=datetime(2026, 9, 6))
        assert False
    except ValueError:
        assert True


def test_incident_creation():
    incident = ITIncident(
        "i1", "org-1", "Production outage", severity="critical"
    )
    assert incident.severity == "critical"


def test_invalid_incident_status():
    try:
        ITIncident("i1", "org-1", "Incident", status="unknown")
        assert False
    except ValueError:
        assert True


def test_invalid_incident_severity():
    try:
        ITIncident("i1", "org-1", "Incident", severity="urgent")
        assert False
    except ValueError:
        assert True


def test_sla_creation():
    sla = ITServiceLevelAgreement(
        "sla-1", "org-1", "Support", 30, 240
    )
    assert sla.response_minutes == 30


def test_invalid_sla_duration():
    try:
        ITServiceLevelAgreement("sla-1", "org-1", "Invalid", 0, 10)
        assert False
    except ValueError:
        assert True


def test_portfolio_counts():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(
            ITTicket("t1", "org-1", "Issue"),
            ITTicket("t2", "org-1", "Closed", status="closed"),
        ),
        incidents=(ITIncident("i1", "org-1", "Incident"),),
        slas=(ITServiceLevelAgreement("s1", "org-1", "SLA", 30, 240),),
    )

    result = ITTicketIncidentIntelligence().analyze(portfolio)

    assert result.ticket_count == 2
    assert result.open_ticket_count == 1
    assert result.incident_count == 1
    assert result.open_incident_count == 1
    assert result.sla_count == 1


def test_unassigned_tickets():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(ITTicket("t1", "org-1", "Unassigned"),),
    )

    result = ITTicketIncidentIntelligence().analyze(portfolio)

    assert result.unassigned_ticket_count == 1


def test_overdue_tickets():
    now = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)

    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(
            ITTicket(
                "t1",
                "org-1",
                "Overdue",
                due_at=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
            ),
        ),
    )

    result = ITTicketIncidentIntelligence().analyze(
        portfolio, now=now
    )

    assert result.overdue_ticket_count == 1


def test_high_priority_tickets():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(
            ITTicket(
                "t1",
                "org-1",
                "Critical issue",
                priority="critical",
            ),
        ),
    )

    result = ITTicketIncidentIntelligence().analyze(portfolio)

    assert result.high_priority_ticket_count == 1


def test_critical_incidents():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        incidents=(
            ITIncident(
                "i1",
                "org-1",
                "Production outage",
                severity="critical",
            ),
        ),
    )

    result = ITTicketIncidentIntelligence().analyze(portfolio)

    assert result.critical_incident_count == 1


def test_unowned_incidents():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        incidents=(ITIncident("i1", "org-1", "Incident"),),
    )

    result = ITTicketIncidentIntelligence().analyze(portfolio)

    assert result.unowned_incident_count == 1


def test_safety_boundary():
    result = ITTicketIncidentIntelligence().analyze(
        ITTicketIncidentPortfolio("org-1")
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_deterministic_analysis():
    portfolio = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(ITTicket("t1", "org-1", "Issue"),),
    )

    intelligence = ITTicketIncidentIntelligence()

    assert intelligence.analyze(portfolio) == intelligence.analyze(portfolio)


def test_invalid_input():
    try:
        ITTicketIncidentIntelligence().analyze("invalid")
        assert False
    except TypeError:
        assert True
