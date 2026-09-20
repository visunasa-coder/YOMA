from yoma.office.it.it_edition_runtime import (
    YomaITEditionAnalysis,
    YomaITEditionInput,
    YomaITEditionRuntime,
    analyze_yoma_it_edition,
)

from yoma.office.it.it_dependencies import (
    ITDependency,
    ITDependencyNode,
    ITDependencyPortfolio,
)

from yoma.office.it.it_devops import (
    ITDeployment,
    ITDevOpsPortfolio,
    ITRelease,
)

from yoma.office.it.it_organization import (
    ITMember,
    ITOrganization,
    ITService,
    ITTeam,
)

from yoma.office.it.it_projects import (
    ITProject,
    ITProjectPortfolio,
    ITTask,
)

from yoma.office.it.it_risk_escalation import (
    ITRiskPortfolio,
    ITRiskSignal,
)

from yoma.office.it.it_tickets import (
    ITIncident,
    ITServiceLevelAgreement,
    ITTicket,
    ITTicketIncidentPortfolio,
)

from yoma.office.it.it_workload_capacity import (
    ITCapacity,
    ITWorkload,
    ITWorkloadCapacityPortfolio,
)


def make_input():
    organization = ITOrganization(
        organization_id="org-1",
        name="YOMA IT Organization",
        members=(
            ITMember(
                member_id="u1",
                organization_id="org-1",
                name="Alice",
                role="developer",
                team_id="team-1",
            ),
        ),
        teams=(
            ITTeam(
                team_id="team-1",
                organization_id="org-1",
                name="Engineering",
                function="Engineering",
            ),
        ),
        services=(
            ITService(
                service_id="svc-1",
                organization_id="org-1",
                name="API",
            ),
        ),
    )

    projects = ITProjectPortfolio(
        "org-1",
        projects=(
            ITProject(
                "p1",
                "org-1",
                name="Platform",
            ),
        ),
        tasks=(
            ITTask(
                "t1",
                "org-1",
                project_id="p1",
                title="Build API",
                assignee_id="u1",
            ),
        ),
    )

    tickets = ITTicketIncidentPortfolio(
        "org-1",
        tickets=(
            ITTicket(
                "ticket-1",
                "org-1",
                title="API issue",
                assignee_id="u1",
            ),
        ),
        incidents=(
            ITIncident(
                "incident-1",
                "org-1",
                title="API incident",
                service_id="svc-1",
            ),
        ),
        slas=(
            ITServiceLevelAgreement(
                "sla-1",
                "org-1",
                "Production SLA",
                response_minutes=30,
                resolution_minutes=240,
            ),
        ),
    )

    devops = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                environment="production",
                status="succeeded",
                owner_id="u1",
            ),
        ),
        releases=(
            ITRelease(
                "r1",
                "org-1",
                "svc-1",
                "v1",
                status="released",
                owner_id="u1",
                target_environment="production",
            ),
        ),
    )

    workload_capacity = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                team_id="team-1",
                project_id="p1",
                service_id="svc-1",
                title="API work",
                estimated_hours=20,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                team_id="team-1",
                available_hours=40,
            ),
        ),
    )

    dependencies = ITDependencyPortfolio(
        "org-1",
        nodes=(
            ITDependencyNode(
                "n1",
                "org-1",
                "task",
                owner_id="u1",
            ),
            ITDependencyNode(
                "n2",
                "org-1",
                "service",
                owner_id="u1",
            ),
        ),
        dependencies=(
            ITDependency(
                "dep-1",
                "org-1",
                "n1",
                "n2",
            ),
        ),
    )

    risks = ITRiskPortfolio(
        "org-1",
        signals=(
            ITRiskSignal(
                "risk-1",
                "org-1",
                "project",
                "normal",
                "Routine review",
                owner_id="u1",
            ),
        ),
    )

    return YomaITEditionInput(
        organization=organization,
        projects=projects,
        tickets=tickets,
        devops=devops,
        workload_capacity=workload_capacity,
        dependencies=dependencies,
        risks=risks,
    )


def test_input_creation():
    operational_input = make_input()

    assert operational_input.organization.organization_id == "org-1"
    assert operational_input.projects.organization_id == "org-1"


def test_input_organization_consistency():
    operational_input = make_input()

    assert (
        operational_input.tickets.organization_id
        == operational_input.organization.organization_id
    )


def test_runtime_composes_all_layers():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.organization.organization_id == "org-1"
    assert result.projects.organization_id == "org-1"
    assert result.tickets.organization_id == "org-1"
    assert result.devops.organization_id == "org-1"
    assert result.workload_capacity.organization_id == "org-1"
    assert result.dependencies.organization_id == "org-1"
    assert result.risks.organization_id == "org-1"


def test_organization_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.organization.member_count >= 1


def test_project_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.projects.project_count == 1
    assert result.projects.task_count == 1


def test_ticket_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.tickets.ticket_count == 1
    assert result.tickets.incident_count == 1


def test_devops_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.devops.deployment_count == 1
    assert result.devops.release_count == 1


def test_workload_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.workload_capacity.workload_count == 1
    assert result.workload_capacity.capacity_member_count == 1


def test_dependency_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.dependencies.node_count == 2
    assert result.dependencies.dependency_count == 1


def test_risk_analysis_present():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.risks.signal_count == 1


def test_issue_count_is_composed():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    expected = (
        len(result.organization.issues)
        + len(result.projects.issues)
        + len(result.tickets.issues)
        + len(result.devops.issues)
        + len(result.workload_capacity.issues)
        + len(result.dependencies.issues)
        + len(result.risks.issues)
    )

    assert result.total_issue_count == expected


def test_critical_attention_detected_for_critical_risk():
    operational_input = make_input()

    risks = ITRiskPortfolio(
        "org-1",
        signals=(
            ITRiskSignal(
                "risk-critical",
                "org-1",
                "incident",
                "critical",
                "Production outage",
                owner_id="u1",
            ),
        ),
    )

    operational_input = YomaITEditionInput(
        organization=operational_input.organization,
        projects=operational_input.projects,
        tickets=operational_input.tickets,
        devops=operational_input.devops,
        workload_capacity=operational_input.workload_capacity,
        dependencies=operational_input.dependencies,
        risks=risks,
    )

    result = YomaITEditionRuntime().analyze(
        operational_input
    )

    assert result.critical_attention_required is True


def test_critical_attention_detected_for_failed_deployment():
    operational_input = make_input()

    devops = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                environment="production",
                status="failed",
                owner_id="u1",
            ),
        ),
    )

    operational_input = YomaITEditionInput(
        organization=operational_input.organization,
        projects=operational_input.projects,
        tickets=operational_input.tickets,
        devops=devops,
        workload_capacity=operational_input.workload_capacity,
        dependencies=operational_input.dependencies,
        risks=operational_input.risks,
    )

    result = YomaITEditionRuntime().analyze(
        operational_input
    )

    assert result.critical_attention_required is True


def test_critical_attention_detected_for_dependency_cycle():
    operational_input = make_input()

    dependencies = ITDependencyPortfolio(
        "org-1",
        nodes=(
            ITDependencyNode("n1", "org-1", "task"),
            ITDependencyNode("n2", "org-1", "task"),
        ),
        dependencies=(
            ITDependency(
                "d1",
                "org-1",
                "n1",
                "n2",
            ),
            ITDependency(
                "d2",
                "org-1",
                "n2",
                "n1",
            ),
        ),
    )

    operational_input = YomaITEditionInput(
        organization=operational_input.organization,
        projects=operational_input.projects,
        tickets=operational_input.tickets,
        devops=operational_input.devops,
        workload_capacity=operational_input.workload_capacity,
        dependencies=dependencies,
        risks=operational_input.risks,
    )

    result = YomaITEditionRuntime().analyze(
        operational_input
    )

    assert result.critical_attention_required is True


def test_critical_attention_detected_for_capacity_shortfall():
    operational_input = make_input()

    workload_capacity = ITWorkloadCapacityPortfolio(
        "org-1",
        workloads=(
            ITWorkload(
                "w1",
                "org-1",
                member_id="u1",
                estimated_hours=60,
            ),
        ),
        capacities=(
            ITCapacity(
                "u1",
                "org-1",
                available_hours=40,
            ),
        ),
    )

    operational_input = YomaITEditionInput(
        organization=operational_input.organization,
        projects=operational_input.projects,
        tickets=operational_input.tickets,
        devops=operational_input.devops,
        workload_capacity=workload_capacity,
        dependencies=operational_input.dependencies,
        risks=operational_input.risks,
    )

    result = YomaITEditionRuntime().analyze(
        operational_input
    )

    assert result.critical_attention_required is True


def test_governance_boundary():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert result.human_attention_required is True
    assert result.requires_human_approval is True
    assert result.executable is False

    assert result.organization.requires_human_approval is True
    assert result.projects.requires_human_approval is True
    assert result.tickets.requires_human_approval is True
    assert result.devops.requires_human_approval is True
    assert result.workload_capacity.requires_human_approval is True
    assert result.dependencies.requires_human_approval is True
    assert result.risks.requires_human_approval is True


def test_runtime_is_deterministic():
    runtime = YomaITEditionRuntime()

    first = runtime.analyze(make_input())
    second = runtime.analyze(make_input())

    assert first == second


def test_helper_function():
    result = analyze_yoma_it_edition(
        make_input()
    )

    assert isinstance(
        result,
        YomaITEditionAnalysis,
    )
    assert result.organization_id == "org-1"


def test_invalid_input_type():
    try:
        YomaITEditionRuntime().analyze(None)
    except TypeError:
        pass
    else:
        raise AssertionError(
            "invalid input type must fail"
        )


def test_cross_layer_mismatch_rejected():
    operational_input = make_input()

    try:
        YomaITEditionInput(
            organization=operational_input.organization,
            projects=operational_input.projects,
            tickets=operational_input.tickets,
            devops=operational_input.devops,
            workload_capacity=operational_input.workload_capacity,
            dependencies=operational_input.dependencies,
            risks=ITRiskPortfolio("org-2"),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "cross-layer organization mismatch must fail"
        )


def test_analysis_is_frozen():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    try:
        result.executable = True
    except Exception:
        pass
    else:
        raise AssertionError(
            "analysis must be immutable"
        )


def test_no_execution_authority():
    result = YomaITEditionRuntime().analyze(
        make_input()
    )

    assert not hasattr(result, "execute")
    assert not hasattr(result, "authorize")
    assert not hasattr(result, "approve")
