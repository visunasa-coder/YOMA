from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.decision_dependencies import (
    DecisionDependency,
    DecisionDependencyEngine,
    DecisionDependencyMap,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


def make_plan():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-5",
        decision_type="workload_review",
        created_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-1",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M31-5",
                evidence_type="current_signal",
                source_id="SIG-M31-5",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    return ActionPlanningEngine().build(decision)


def test_dependency_map_builds():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert isinstance(dependency_map, DecisionDependencyMap)
    assert dependency_map.dependency_map_id == "DMAP-APLAN-DINT-M31-5"
    assert dependency_map.plan_id == "APLAN-DINT-M31-5"
    assert dependency_map.decision_id == "DINT-M31-5"


def test_user_dependency_is_created():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    user_dependencies = [
        dependency
        for dependency in dependency_map.dependencies
        if dependency.dependency_type == "user"
    ]

    assert len(user_dependencies) >= 1
    assert user_dependencies[0].entity_id == "U1"


def test_system_dependency_is_created():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    system_dependencies = [
        dependency
        for dependency in dependency_map.dependencies
        if dependency.dependency_type == "system"
    ]

    assert len(system_dependencies) >= 1
    assert system_dependencies[0].entity_id == "SYS1"


def test_dependency_ids_are_deterministic():
    engine = DecisionDependencyEngine()

    first = engine.analyze(make_plan())
    second = engine.analyze(make_plan())

    assert first.dependencies == second.dependencies


def test_dependency_counts():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert dependency_map.dependency_count >= 2
    assert dependency_map.user_dependency_count >= 1
    assert dependency_map.system_dependency_count >= 1


def test_affected_entities_are_preserved():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert dependency_map.affected_user_ids == ("U1",)
    assert dependency_map.affected_system_ids == ("SYS1",)


def test_dependency_depth():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert dependency_map.dependency_depth == 1


def test_human_approval_required():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert dependency_map.requires_human_approval is True
    assert dependency_map.requires_review is True


def test_dependency_analysis_is_not_executable():
    dependency_map = DecisionDependencyEngine().analyze(make_plan())

    assert dependency_map.executable is False
    assert not hasattr(dependency_map, "execute")
    assert not hasattr(DecisionDependencyEngine, "execute")


def test_invalid_input():
    with pytest.raises(TypeError):
        DecisionDependencyEngine().analyze(object())
