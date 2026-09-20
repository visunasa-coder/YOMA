from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.organization_graph import (
    OrganizationGraph,
)
from yoma.office.intelligence.operational_situation_runtime import (
    OperationalSituationResult,
)
from yoma.office.intelligence.operational_situation_context_runtime import (
    OperationalSituationContextRuntime,
)
from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)
from yoma.office.operations import OperationalSituation


def situation(
    situation_id: str = "SIT-001",
    user_id: str | None = "U001",
    organization_id: str | None = "ORG001",
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=datetime.now(timezone.utc),
        organization_id=organization_id,
        user_id=user_id,
        severity="high",
        score=0.85,
        signal_ids=("SIG001",),
        evidence_event_ids=("EV001",),
    )


def make_graph():
    return OrganizationGraph(
        organizations=[
            Organization(
                organization_id="ORG001",
                name="YOMA Corp",
            )
        ],
        locations=[
            Location(
                location_id="LOC001",
                organization_id="ORG001",
                name="Chennai",
            )
        ],
        departments=[
            Department(
                department_id="DEP001",
                organization_id="ORG001",
                name="Engineering",
                location_id="LOC001",
            )
        ],
        teams=[
            Team(
                team_id="TEAM001",
                organization_id="ORG001",
                name="AI Team",
                department_id="DEP001",
            )
        ],
        employees=[
            Employee(
                employee_id="U001",
                name="Employee One",
                organization_id="ORG001",
                department_id="DEP001",
                team_id="TEAM001",
                location_id="LOC001",
            )
        ],
    )


def make_result(situations):
    return OperationalSituationResult(
        events=(),
        signals=(),
        situations=tuple(situations),
    )


def test_context_runtime_resolves_employee_context():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    result = runtime.process(
        make_result([situation()])
    )

    assert len(result.contexts) == 1

    context = result.contexts[0]

    assert context.employee_id == "U001"
    assert context.team.node_id == "TEAM001"
    assert context.department.node_id == "DEP001"
    assert context.location.node_id == "LOC001"
    assert context.organization.node_id == "ORG001"


def test_context_runtime_preserves_situations():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    situations = [
        situation("SIT-001"),
        situation("SIT-002"),
    ]

    result = runtime.process(make_result(situations))

    assert result.situations == tuple(situations)


def test_context_runtime_preserves_situation_identity():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    source = situation("SIT-XYZ")

    result = runtime.process(make_result([source]))

    assert result.contexts[0].situation_id == "SIT-XYZ"
    assert result.contexts[0].situation is source


def test_context_runtime_handles_unknown_employee():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    source = situation(
        user_id="UNKNOWN",
        organization_id="ORG001",
    )

    result = runtime.process(make_result([source]))

    context = result.contexts[0]

    assert context.employee_id == "UNKNOWN"
    assert context.team is None
    assert context.department is None
    assert context.location is None
    assert context.organization is None


def test_context_runtime_resolves_explicit_organization_for_system_situation():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    source = situation(
        user_id=None,
        organization_id="ORG001",
    )

    result = runtime.process(make_result([source]))

    context = result.contexts[0]

    assert context.employee_id is None
    assert context.organization.node_id == "ORG001"


def test_context_runtime_handles_empty_result():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    result = runtime.process(make_result([]))

    assert result.situations == ()
    assert result.contexts == ()


def test_context_runtime_rejects_invalid_input():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    with pytest.raises(TypeError):
        runtime.process("invalid")


def test_context_runtime_rejects_invalid_graph():
    with pytest.raises(TypeError):
        OperationalSituationContextRuntime(
            graph="invalid"
        )


def test_context_runtime_tracks_last_result():
    runtime = OperationalSituationContextRuntime(
        graph=make_graph()
    )

    result = runtime.process(
        make_result([situation()])
    )

    assert runtime.last_result is result
