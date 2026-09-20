from dataclasses import replace

import pytest

from yoma.office.intelligence.organization_intelligence import (
    OrganizationIntelligenceResult as FoundationResult,
    OrganizationMember,
    OrganizationIntelligenceRuntime as FoundationRuntime,
)
from yoma.office.intelligence.organization_relationships import (
    WorkforceStructureRuntime,
)
from yoma.office.intelligence.organization_capacity import (
    OrganizationalCapacityRuntime,
)
from yoma.office.intelligence.organization_workload import (
    OrganizationalWorkloadRuntime,
)
from yoma.office.intelligence.organization_workload_risk import (
    OrganizationalWorkloadRiskRuntime,
)
from yoma.office.intelligence.organization_dependency import (
    OrganizationalDependencyRuntime,
)
from yoma.office.intelligence.organization_coverage import (
    OrganizationalCoverageRuntime,
)
from yoma.office.intelligence.organizational_intelligence_runtime import (
    OrganizationalIntelligenceResult,
    OrganizationalIntelligenceRuntime,
)


def members():
    return [
        OrganizationMember(
            member_id="ceo",
            organization_id="org-1",
            department="Executive",
            team="Leadership",
            location="Chennai",
            manager_id="",
            metadata={},
        ),
        OrganizationMember(
            member_id="manager",
            organization_id="org-1",
            department="Engineering",
            team="Platform",
            location="Chennai",
            manager_id="ceo",
            metadata={},
        ),
        OrganizationMember(
            member_id="u1",
            organization_id="org-1",
            department="Engineering",
            team="Platform",
            location="Chennai",
            manager_id="manager",
            metadata={},
        ),
        OrganizationMember(
            member_id="u2",
            organization_id="org-1",
            department="Engineering",
            team="Platform",
            location="Coimbatore",
            manager_id="manager",
            metadata={},
        ),
    ]


def build_components():
    items = members()
    workload_values = {
        "ceo": 1,
        "manager": 4,
        "u1": 2,
        "u2": 3,
    }

    foundation = FoundationRuntime().analyze(
        organization_id="org-1",
        members=items,
    )

    structure = WorkforceStructureRuntime().analyze(
        items,
        organization_id="org-1",
    )

    capacity = OrganizationalCapacityRuntime().analyze(
        items,
        organization_id="org-1",
    )

    workload = OrganizationalWorkloadRuntime().analyze(
        items,
        workload_values,
        organization_id="org-1",
    )

    workload_risk = OrganizationalWorkloadRiskRuntime().analyze(
        items,
        workload_values,
        organization_id="org-1",
    )

    dependency = OrganizationalDependencyRuntime().analyze(
        items,
        workload_values,
        organization_id="org-1",
    )

    coverage = OrganizationalCoverageRuntime().analyze(
        items,
        organization_id="org-1",
    )

    return (
        foundation,
        structure,
        capacity,
        workload,
        workload_risk,
        dependency,
        coverage,
    )


def test_composes_all_m36_components():
    components = build_components()

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is True
    assert result.validation_errors == ()
    assert result.foundation is components[0]
    assert result.structure is components[1]
    assert result.capacity is components[2]
    assert result.workload is components[3]
    assert result.workload_risk is components[4]
    assert result.dependency is components[5]
    assert result.coverage is components[6]


def test_result_has_correct_type():
    result = OrganizationalIntelligenceRuntime().build(
        *build_components(),
        organization_id="org-1",
    )

    assert isinstance(result, OrganizationalIntelligenceResult)


def test_validates_matching_organization():
    result = OrganizationalIntelligenceRuntime().build(
        *build_components(),
        organization_id="org-1",
    )

    assert result.organization_id == "org-1"
    assert result.validated is True


def test_rejects_missing_component():
    components = list(build_components())
    components[3] = None

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is False
    assert "workload component is missing" in result.validation_errors


def test_rejects_mismatched_organization():
    components = list(build_components())

    components[1] = replace(
        components[1],
        organization_id="org-2",
    )

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is False
    assert (
        "structure component organization_id does not match"
        in result.validation_errors
    )


def test_rejects_executable_component():
    components = list(build_components())

    components[2] = replace(
        components[2],
        executable=True,
    )

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is False
    assert "capacity component is executable" in result.validation_errors


def test_rejects_non_read_only_component():
    components = list(build_components())

    components[0] = replace(
        components[0],
        read_only=False,
    )

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is False
    assert "foundation component is not read-only" in result.validation_errors


def test_detects_member_count_mismatch():
    components = list(build_components())

    components[3] = replace(
        components[3],
        total_members=999,
    )

    result = OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    assert result.validated is False
    assert (
        "workload total_members does not match foundation"
        in result.validation_errors
    )


def test_validates_all_component_member_counts():
    result = OrganizationalIntelligenceRuntime().build(
        *build_components(),
        organization_id="org-1",
    )

    assert result.foundation.total_members == 4
    assert result.structure.total_members == 4
    assert result.capacity.total_members == 4
    assert result.workload.total_members == 4
    assert result.workload_risk.total_members == 4
    assert result.dependency.total_members == 4
    assert result.coverage.total_members == 4


def test_is_read_only_and_non_executable():
    result = OrganizationalIntelligenceRuntime().build(
        *build_components(),
        organization_id="org-1",
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["source"] == "M36.8"
    assert result.metadata["composition_only"] is True
    assert result.metadata["validation_only"] is True


def test_metadata_records_all_previous_components():
    result = OrganizationalIntelligenceRuntime().build(
        *build_components(),
        organization_id="org-1",
    )

    assert result.metadata["components"] == (
        "M36.1",
        "M36.2",
        "M36.3",
        "M36.4",
        "M36.5",
        "M36.6",
        "M36.7",
    )


def test_validation_errors_are_deterministic():
    components = list(build_components())
    components[1] = replace(
        components[1],
        organization_id="org-2",
    )
    components[3] = replace(
        components[3],
        total_members=99,
    )

    runtime = OrganizationalIntelligenceRuntime()

    first = runtime.build(
        *components,
        organization_id="org-1",
    )

    second = runtime.build(
        *components,
        organization_id="org-1",
    )

    assert first == second


def test_rejects_empty_organization():
    with pytest.raises(ValueError):
        OrganizationalIntelligenceRuntime().build(
            *build_components(),
            organization_id="",
        )


def test_component_objects_are_not_modified():
    components = build_components()

    before = tuple(repr(component) for component in components)

    OrganizationalIntelligenceRuntime().build(
        *components,
        organization_id="org-1",
    )

    after = tuple(repr(component) for component in components)

    assert before == after
