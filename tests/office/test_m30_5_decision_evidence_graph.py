from datetime import datetime, timezone

import pytest

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.decision_evidence_graph import (
    DecisionEvidenceEdge,
    DecisionEvidenceGraph,
    DecisionEvidenceGraphBuilder,
    DecisionEvidenceNode,
)


NOW = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_decision(
    decision_id="DINT-ORG1-U1-GLOBAL-SIG-1",
    current=True,
    historical=True,
    predictive=True,
    evidence=None,
):
    if evidence is None:
        evidence = (
            DecisionIntelligenceEvidence(
                evidence_id="CURRENT-SIG-1",
                evidence_type="current_decision",
                source_id="DEC-SIG-1",
                description="Current evidence.",
                weight=0.80,
                data={
                    "signal_id": "SIG-1",
                },
            ),
            DecisionIntelligenceEvidence(
                evidence_id="HIST-SIT-1",
                evidence_type="historical_intelligence",
                source_id="SIT-1",
                description="Historical evidence.",
                weight=0.70,
                data={
                    "occurrence_count": 3,
                },
            ),
            DecisionIntelligenceEvidence(
                evidence_id="PRED-PRED-1",
                evidence_type="predictive_decision_context",
                source_id="PCTX-1",
                description="Predictive evidence.",
                weight=0.75,
                data={
                    "probability": 0.80,
                    "confidence": 0.75,
                },
            ),
        )

    return DecisionIntelligence(
        decision_id=decision_id,
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=current,
        historical_intelligence_available=historical,
        predictive_intelligence_available=predictive,
        current_decision_ids=(
            "DEC-SIG-1",
        )
        if current
        else (),
        historical_context_ids=(
            "SIT-1",
        )
        if historical
        else (),
        predictive_context_ids=(
            "PCTX-1",
        )
        if predictive
        else (),
        evidence=tuple(evidence),
        recommendation_type="workload_review",
        recommendation_reason="Review workload.",
        requires_human_approval=True,
    )


def test_build_returns_graph():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    assert isinstance(
        graph,
        DecisionEvidenceGraph,
    )


def test_decision_node_exists():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    node = graph.node(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    assert node is not None
    assert node.node_type == "decision"


def test_current_context_node_exists():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    node = graph.node(
        "DEC-SIG-1"
    )

    assert node is not None
    assert node.node_type == "current_decision"


def test_historical_context_node_exists():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    node = graph.node("SIT-1")

    assert node is not None
    assert node.node_type == "historical_context"


def test_predictive_context_node_exists():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    node = graph.node("PCTX-1")

    assert node is not None
    assert node.node_type == "predictive_context"


def test_evidence_nodes_exist():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    assert graph.node(
        "CURRENT-SIG-1"
    ).node_type == "evidence"

    assert graph.node(
        "HIST-SIT-1"
    ).node_type == "evidence"

    assert graph.node(
        "PRED-PRED-1"
    ).node_type == "evidence"


def test_decision_has_current_edge():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    edges = graph.outgoing(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    assert any(
        edge.relationship == "CURRENT_DECISION"
        and edge.target_id == "DEC-SIG-1"
        for edge in edges
    )


def test_decision_has_historical_edge():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    edges = graph.outgoing(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    assert any(
        edge.relationship == "HISTORICAL_CONTEXT"
        and edge.target_id == "SIT-1"
        for edge in edges
    )


def test_decision_has_predictive_edge():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    edges = graph.outgoing(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    assert any(
        edge.relationship == "PREDICTIVE_CONTEXT"
        and edge.target_id == "PCTX-1"
        for edge in edges
    )


def test_decision_has_evidence_edges():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    edges = graph.outgoing(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    evidence_edges = [
        edge
        for edge in edges
        if edge.relationship == "EVIDENCE"
    ]

    assert len(evidence_edges) == 3


def test_incoming_edges_work():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    incoming = graph.incoming(
        "PRED-PRED-1"
    )

    assert len(incoming) == 1
    assert (
        incoming[0].relationship
        == "EVIDENCE"
    )


def test_related_nodes_work():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    related = graph.related_nodes(
        "DINT-ORG1-U1-GLOBAL-SIG-1"
    )

    assert {
        node.node_id
        for node in related
    } == {
        "DEC-SIG-1",
        "SIT-1",
        "PCTX-1",
        "CURRENT-SIG-1",
        "HIST-SIT-1",
        "PRED-PRED-1",
    }


def test_graph_counts():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    assert graph.node_count == 7
    assert graph.edge_count == 6


def test_evidence_data_is_preserved():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    node = graph.node(
        "PRED-PRED-1"
    )

    assert node.data["probability"] == 0.80
    assert node.data["confidence"] == 0.75


def test_node_ids_are_deterministic():
    first = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )
    second = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    assert first.node_ids == second.node_ids


def test_edge_ids_are_deterministic():
    first = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )
    second = DecisionEvidenceGraphBuilder.build(
        make_decision()
    )

    assert first.edge_ids == second.edge_ids


def test_build_many_is_deterministic():
    first = make_decision(
        decision_id="DINT-B"
    )
    second = make_decision(
        decision_id="DINT-A"
    )

    graphs = DecisionEvidenceGraphBuilder.build_many(
        (first, second)
    )

    assert tuple(
        graph.decision_id
        for graph in graphs
    ) == (
        "DINT-A",
        "DINT-B",
    )


def test_no_current_context_is_safe():
    decision = make_decision(
        current=False,
        historical=True,
        predictive=True,
    )

    graph = DecisionEvidenceGraphBuilder.build(
        decision
    )

    assert graph.node(
        "DEC-SIG-1"
    ) is None


def test_no_historical_context_is_safe():
    decision = make_decision(
        current=True,
        historical=False,
        predictive=True,
    )

    graph = DecisionEvidenceGraphBuilder.build(
        decision
    )

    assert graph.node("SIT-1") is None


def test_no_predictive_context_is_safe():
    decision = make_decision(
        current=True,
        historical=True,
        predictive=False,
    )

    graph = DecisionEvidenceGraphBuilder.build(
        decision
    )

    assert graph.node("PCTX-1") is None


def test_empty_evidence_is_safe():
    graph = DecisionEvidenceGraphBuilder.build(
        make_decision(
            evidence=()
        )
    )

    assert graph.edge_count == 3


def test_type_validation():
    with pytest.raises(TypeError):
        DecisionEvidenceGraphBuilder.build(
            object()
        )
