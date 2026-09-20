"""YOMA IT Edition - ticket, incident and SLA intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_TICKET_STATUSES = {
    "open", "in_progress", "pending", "resolved", "closed", "cancelled"
}
_INCIDENT_STATUSES = {
    "open", "investigating", "mitigating", "resolved", "closed"
}
_PRIORITIES = {"low", "normal", "high", "critical"}
_SEVERITIES = {"minor", "major", "critical"}


@dataclass(frozen=True)
class ITTicket:
    ticket_id: str
    organization_id: str
    title: str
    status: str = "open"
    priority: str = "normal"
    assignee_id: str | None = None
    service_id: str | None = None
    sla_id: str | None = None
    due_at: datetime | None = None

    def __post_init__(self):
        for name in ("ticket_id", "organization_id", "title"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")

        if self.status not in _TICKET_STATUSES:
            raise ValueError("invalid ticket status")

        if self.priority not in _PRIORITIES:
            raise ValueError("invalid ticket priority")

        for name in ("assignee_id", "service_id", "sla_id"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{name} must be a non-empty string when provided")

        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")


@dataclass(frozen=True)
class ITIncident:
    incident_id: str
    organization_id: str
    title: str
    status: str = "open"
    severity: str = "major"
    service_id: str | None = None
    owner_id: str | None = None
    started_at: datetime | None = None

    def __post_init__(self):
        for name in ("incident_id", "organization_id", "title"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")

        if self.status not in _INCIDENT_STATUSES:
            raise ValueError("invalid incident status")

        if self.severity not in _SEVERITIES:
            raise ValueError("invalid incident severity")

        for name in ("service_id", "owner_id"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{name} must be a non-empty string when provided")

        if self.started_at is not None and self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")


@dataclass(frozen=True)
class ITServiceLevelAgreement:
    sla_id: str
    organization_id: str
    name: str
    response_minutes: int
    resolution_minutes: int

    def __post_init__(self):
        for name in ("sla_id", "organization_id", "name"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")

        if not isinstance(self.response_minutes, int) or self.response_minutes <= 0:
            raise ValueError("response_minutes must be a positive integer")

        if not isinstance(self.resolution_minutes, int) or self.resolution_minutes <= 0:
            raise ValueError("resolution_minutes must be a positive integer")


@dataclass(frozen=True)
class ITTicketIncidentPortfolio:
    organization_id: str
    tickets: tuple[ITTicket, ...] = ()
    incidents: tuple[ITIncident, ...] = ()
    slas: tuple[ITServiceLevelAgreement, ...] = ()

    def __post_init__(self):
        if not isinstance(self.organization_id, str) or not self.organization_id.strip():
            raise ValueError("organization_id must be a non-empty string")

        if not isinstance(self.tickets, tuple):
            raise ValueError("tickets must be a tuple")
        if not isinstance(self.incidents, tuple):
            raise ValueError("incidents must be a tuple")
        if not isinstance(self.slas, tuple):
            raise ValueError("slas must be a tuple")

        for item in self.tickets:
            if item.organization_id != self.organization_id:
                raise ValueError("all tickets must belong to the organization")

        for item in self.incidents:
            if item.organization_id != self.organization_id:
                raise ValueError("all incidents must belong to the organization")

        for item in self.slas:
            if item.organization_id != self.organization_id:
                raise ValueError("all SLAs must belong to the organization")


@dataclass(frozen=True)
class ITTicketIncidentAnalysis:
    organization_id: str
    ticket_count: int
    open_ticket_count: int
    unassigned_ticket_count: int
    high_priority_ticket_count: int
    overdue_ticket_count: int
    incident_count: int
    open_incident_count: int
    critical_incident_count: int
    unowned_incident_count: int
    sla_count: int
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


class ITTicketIncidentIntelligence:
    """Read-only ticket, incident and SLA analyzer."""

    def analyze(
        self,
        portfolio: ITTicketIncidentPortfolio,
        *,
        now: datetime | None = None,
    ) -> ITTicketIncidentAnalysis:
        if not isinstance(portfolio, ITTicketIncidentPortfolio):
            raise TypeError("portfolio must be ITTicketIncidentPortfolio")

        if now is None:
            now = datetime.now().astimezone()

        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        open_tickets = tuple(
            t for t in portfolio.tickets
            if t.status not in {"resolved", "closed", "cancelled"}
        )

        overdue = tuple(
            t for t in open_tickets
            if t.due_at is not None and t.due_at < now
        )

        unassigned = tuple(
            t for t in open_tickets if t.assignee_id is None
        )

        high_priority = tuple(
            t for t in open_tickets
            if t.priority in {"high", "critical"}
        )

        open_incidents = tuple(
            i for i in portfolio.incidents
            if i.status not in {"resolved", "closed"}
        )

        critical_incidents = tuple(
            i for i in open_incidents
            if i.severity == "critical"
        )

        unowned_incidents = tuple(
            i for i in open_incidents if i.owner_id is None
        )

        issues = []

        if overdue:
            issues.append("open tickets are overdue")
        if unassigned:
            issues.append("open tickets are unassigned")
        if high_priority:
            issues.append("high-priority tickets require attention")
        if open_incidents:
            issues.append("open incidents require operational attention")
        if critical_incidents:
            issues.append("critical incidents require immediate human attention")
        if unowned_incidents:
            issues.append("open incidents have no assigned owner")

        return ITTicketIncidentAnalysis(
            organization_id=portfolio.organization_id,
            ticket_count=len(portfolio.tickets),
            open_ticket_count=len(open_tickets),
            unassigned_ticket_count=len(unassigned),
            high_priority_ticket_count=len(high_priority),
            overdue_ticket_count=len(overdue),
            incident_count=len(portfolio.incidents),
            open_incident_count=len(open_incidents),
            critical_incident_count=len(critical_incidents),
            unowned_incident_count=len(unowned_incidents),
            sla_count=len(portfolio.slas),
            issues=tuple(issues),
        )


def analyze_it_tickets(
    portfolio: ITTicketIncidentPortfolio,
    *,
    now: datetime | None = None,
) -> ITTicketIncidentAnalysis:
    return ITTicketIncidentIntelligence().analyze(portfolio, now=now)
