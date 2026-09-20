from __future__ import annotations

from dataclasses import dataclass

from yoma.office.it.it_dependencies import (
    ITDependencyAnalysis,
    ITDependencyIntelligence,
    ITDependencyPortfolio,
)
from yoma.office.it.it_devops import (
    ITDevOpsAnalysis,
    ITDevOpsIntelligence,
    ITDevOpsPortfolio,
)
from yoma.office.it.it_organization import (
    ITOrganizationAnalysis,
    ITOrganizationIntelligence,
    ITOrganization,
)
from yoma.office.it.it_projects import (
    ITProjectTaskAnalysis,
    ITProjectTaskIntelligence,
    ITProjectPortfolio,
)
from yoma.office.it.it_risk_escalation import (
    ITRiskEscalationAnalysis,
    ITRiskEscalationIntelligence,
    ITRiskPortfolio,
)
from yoma.office.it.it_tickets import (
    ITTicketIncidentAnalysis,
    ITTicketIncidentIntelligence,
    ITTicketIncidentPortfolio,
)
from yoma.office.it.it_workload_capacity import (
    ITWorkloadCapacityAnalysis,
    ITWorkloadCapacityIntelligence,
    ITWorkloadCapacityPortfolio,
)


@dataclass(frozen=True)
class YomaITEditionInput:
    organization: ITOrganization
    projects: ITProjectPortfolio
    tickets: ITTicketIncidentPortfolio
    devops: ITDevOpsPortfolio
    workload_capacity: ITWorkloadCapacityPortfolio
    dependencies: ITDependencyPortfolio
    risks: ITRiskPortfolio

    def __post_init__(self) -> None:
        organization_id = self.organization.organization_id

        values = (
            ("projects", self.projects.organization_id),
            ("tickets", self.tickets.organization_id),
            ("devops", self.devops.organization_id),
            ("workload_capacity", self.workload_capacity.organization_id),
            ("dependencies", self.dependencies.organization_id),
            ("risks", self.risks.organization_id),
        )

        for name, value in values:
            if value != organization_id:
                raise ValueError(
                    f"{name} organization_id mismatch"
                )


@dataclass(frozen=True)
class YomaITEditionAnalysis:
    organization_id: str
    organization: ITOrganizationAnalysis
    projects: ITProjectTaskAnalysis
    tickets: ITTicketIncidentAnalysis
    devops: ITDevOpsAnalysis
    workload_capacity: ITWorkloadCapacityAnalysis
    dependencies: ITDependencyAnalysis
    risks: ITRiskEscalationAnalysis
    total_issue_count: int
    critical_attention_required: bool
    human_attention_required: bool = True
    requires_human_approval: bool = True
    executable: bool = False


@dataclass(frozen=True)
class YomaITEditionRuntime:
    """
    Governed composition runtime for the YOMA IT Edition.

    The runtime composes the seven IT intelligence domains:

    1. Organization
    2. Projects / Tasks
    3. Tickets / Incidents / SLA
    4. DevOps / Deployment / Release
    5. Workload / Capacity
    6. Dependencies / Bottlenecks
    7. Risk / Escalation / Recommendations

    It observes and analyzes the supplied operational state only.
    It does not execute recommendations, alter operational records,
    reassign work, escalate incidents, deploy releases, or authorize
    actions.
    """

    organization_intelligence: ITOrganizationIntelligence = (
        ITOrganizationIntelligence()
    )
    project_intelligence: ITProjectTaskIntelligence = (
        ITProjectTaskIntelligence()
    )
    ticket_intelligence: ITTicketIncidentIntelligence = (
        ITTicketIncidentIntelligence()
    )
    devops_intelligence: ITDevOpsIntelligence = (
        ITDevOpsIntelligence()
    )
    workload_intelligence: ITWorkloadCapacityIntelligence = (
        ITWorkloadCapacityIntelligence()
    )
    dependency_intelligence: ITDependencyIntelligence = (
        ITDependencyIntelligence()
    )
    risk_intelligence: ITRiskEscalationIntelligence = (
        ITRiskEscalationIntelligence()
    )

    def analyze(
        self,
        operational_input: YomaITEditionInput,
    ) -> YomaITEditionAnalysis:
        if not isinstance(
            operational_input,
            YomaITEditionInput,
        ):
            raise TypeError(
                "operational_input must be YomaITEditionInput"
            )

        organization_result = self.organization_intelligence.analyze(
            operational_input.organization
        )

        project_result = self.project_intelligence.analyze(
            operational_input.projects
        )

        ticket_result = self.ticket_intelligence.analyze(
            operational_input.tickets
        )

        devops_result = self.devops_intelligence.analyze(
            operational_input.devops
        )

        workload_result = self.workload_intelligence.analyze(
            operational_input.workload_capacity
        )

        dependency_result = self.dependency_intelligence.analyze(
            operational_input.dependencies
        )

        risk_result = self.risk_intelligence.analyze(
            operational_input.risks
        )

        issue_count = (
            len(organization_result.issues)
            + len(project_result.issues)
            + len(ticket_result.issues)
            + len(devops_result.issues)
            + len(workload_result.issues)
            + len(dependency_result.issues)
            + len(risk_result.issues)
        )

        critical_attention = (
            risk_result.critical_risk_count > 0
            or ticket_result.critical_incident_count > 0
            or devops_result.failed_deployment_count > 0
            or devops_result.failed_release_count > 0
            or dependency_result.cycle_count > 0
            or workload_result.capacity_shortfall_hours > 0
        )

        return YomaITEditionAnalysis(
            organization_id=operational_input.organization.organization_id,
            organization=organization_result,
            projects=project_result,
            tickets=ticket_result,
            devops=devops_result,
            workload_capacity=workload_result,
            dependencies=dependency_result,
            risks=risk_result,
            total_issue_count=issue_count,
            critical_attention_required=critical_attention,
            human_attention_required=True,
            requires_human_approval=True,
            executable=False,
        )


def analyze_yoma_it_edition(
    operational_input: YomaITEditionInput,
) -> YomaITEditionAnalysis:
    return YomaITEditionRuntime().analyze(
        operational_input
    )
