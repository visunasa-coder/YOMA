from __future__ import annotations

from typing import Iterable

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.organization_validator import (
    OrganizationGraphValidator,
    OrganizationValidationIssue,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)
from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_events import OrganizationChangeEvent


class OrganizationIntelligenceRuntime:
    """
    Event-aware coordinator for organization graph intelligence.

    The runtime owns an explicit organization-model snapshot and
    derives graph and validation intelligence from that snapshot.

    Organization change events invalidate the current intelligence
    snapshot. Rich organization models must be supplied explicitly
    through refresh(); event dictionaries are never inferred into
    organization models.
    """

    def __init__(
        self,
        *,
        event_bus: OrganizationEventBus | None = None,
        organizations: Iterable[Organization] = (),
        locations: Iterable[Location] = (),
        departments: Iterable[Department] = (),
        teams: Iterable[Team] = (),
        employees: Iterable[Employee] = (),
    ) -> None:
        self.organizations = list(organizations)
        self.locations = list(locations)
        self.departments = list(departments)
        self.teams = list(teams)
        self.employees = list(employees)

        self._graph = OrganizationGraph(
            organizations=self.organizations,
            locations=self.locations,
            departments=self.departments,
            teams=self.teams,
            employees=self.employees,
        )

        self._issues = OrganizationGraphValidator(
            organizations=self.organizations,
            locations=self.locations,
            departments=self.departments,
            teams=self.teams,
            employees=self.employees,
        ).validate()

        self._stale = False
        self._last_event: OrganizationChangeEvent | None = None
        self._event_bus = event_bus

        if event_bus is not None:
            event_bus.subscribe(
                self._handle_event,
                entity_types={
                    "organization",
                    "location",
                    "department",
                    "team",
                    "employee",
                },
            )

    @property
    def stale(self) -> bool:
        return self._stale

    @property
    def last_event(self) -> OrganizationChangeEvent | None:
        return self._last_event

    def graph(self) -> OrganizationGraph:
        return self._graph

    def validation_issues(self) -> list[OrganizationValidationIssue]:
        return list(self._issues)

    def refresh(
        self,
        *,
        organizations: Iterable[Organization] = (),
        locations: Iterable[Location] = (),
        departments: Iterable[Department] = (),
        teams: Iterable[Team] = (),
        employees: Iterable[Employee] = (),
    ) -> None:
        self.organizations = list(organizations)
        self.locations = list(locations)
        self.departments = list(departments)
        self.teams = list(teams)
        self.employees = list(employees)

        self._graph = OrganizationGraph(
            organizations=self.organizations,
            locations=self.locations,
            departments=self.departments,
            teams=self.teams,
            employees=self.employees,
        )

        self._issues = OrganizationGraphValidator(
            organizations=self.organizations,
            locations=self.locations,
            departments=self.departments,
            teams=self.teams,
            employees=self.employees,
        ).validate()

        self._stale = False

    def _handle_event(self, event: OrganizationChangeEvent) -> None:
        self._last_event = event
        self._stale = True

    def close(self) -> bool:
        if self._event_bus is None:
            return False

        removed = self._event_bus.unsubscribe(self._handle_event)

        if removed:
            self._event_bus = None

        return removed
