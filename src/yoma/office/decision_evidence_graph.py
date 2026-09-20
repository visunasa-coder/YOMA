from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


@dataclass(frozen=True)
class DecisionEvidenceNode:
    """One node in the M30.5 decision evidence graph."""

    node_id: str
    node_type: str
    label: str = ""
    data: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id is required")

        if not self.node_type:
            raise ValueError("node_type is required")

        if self.data is None:
            object.__setattr__(self, "data", {})


@dataclass(frozen=True)
class DecisionEvidenceEdge:
    """Explicit directed relationship between two evidence nodes."""

    edge_id: str
    source_id: str
    target_id: str
    relationship: str

    def __post_init__(self) -> None:
        if not self.edge_id:
            raise ValueError("edge_id is required")

        if not self.source_id:
            raise ValueError("source_id is required")

        if not self.target_id:
            raise ValueError("target_id is required")

        if not self.relationship:
            raise ValueError("relationship is required")


@dataclass(frozen=True)
class DecisionEvidenceGraph:
    """Immutable evidence graph for one DecisionIntelligence result."""

    decision_id: str
    nodes: tuple[DecisionEvidenceNode, ...] = ()
    edges: tuple[DecisionEvidenceEdge, ...] = ()

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.nodes)

    @property
    def edge_ids(self) -> tuple[str, ...]:
        return tuple(edge.edge_id for edge in self.edges)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def node(
        self,
        node_id: str,
    ) -> Optional[DecisionEvidenceNode]:
        for item in self.nodes:
            if item.node_id == node_id:
                return item
        return None

    def outgoing(
        self,
        node_id: str,
    ) -> tuple[DecisionEvidenceEdge, ...]:
        return tuple(
            edge
            for edge in self.edges
            if edge.source_id == node_id
        )

    def incoming(
        self,
        node_id: str,
    ) -> tuple[DecisionEvidenceEdge, ...]:
        return tuple(
            edge
            for edge in self.edges
            if edge.target_id == node_id
        )

    def related_nodes(
        self,
        node_id: str,
    ) -> tuple[DecisionEvidenceNode, ...]:
        related_ids = []

        for edge in self.edges:
            if edge.source_id == node_id:
                related_ids.append(edge.target_id)
            elif edge.target_id == node_id:
                related_ids.append(edge.source_id)

        return tuple(
            node
            for node in self.nodes
            if node.node_id in related_ids
        )


class DecisionEvidenceGraphBuilder:
    """
    M30.5 Decision Evidence Graph.

    Explicit graph:

        Decision
           |
           +-- Current Decision
           |
           +-- Historical Context
           |
           +-- Predictive Context
           |
           +-- Evidence

    Evidence nodes are connected only through relationships explicitly
    represented by DecisionIntelligence.
    """

    @staticmethod
    def _decision_node(
        decision: DecisionIntelligence,
    ) -> DecisionEvidenceNode:
        return DecisionEvidenceNode(
            node_id=decision.decision_id,
            node_type="decision",
            label=decision.decision_type,
            data={
                "priority": decision.priority,
                "confidence": decision.confidence,
                "situation_type": decision.situation_type,
                "requires_human_approval": (
                    decision.requires_human_approval
                ),
            },
        )

    @staticmethod
    def _current_nodes(
        decision: DecisionIntelligence,
    ) -> list[DecisionEvidenceNode]:
        return [
            DecisionEvidenceNode(
                node_id=current_id,
                node_type="current_decision",
                label=current_id,
            )
            for current_id in sorted(
                set(decision.current_decision_ids)
            )
        ]

    @staticmethod
    def _historical_nodes(
        decision: DecisionIntelligence,
    ) -> list[DecisionEvidenceNode]:
        return [
            DecisionEvidenceNode(
                node_id=context_id,
                node_type="historical_context",
                label=context_id,
            )
            for context_id in sorted(
                set(decision.historical_context_ids)
            )
        ]

    @staticmethod
    def _predictive_nodes(
        decision: DecisionIntelligence,
    ) -> list[DecisionEvidenceNode]:
        return [
            DecisionEvidenceNode(
                node_id=context_id,
                node_type="predictive_context",
                label=context_id,
            )
            for context_id in sorted(
                set(decision.predictive_context_ids)
            )
        ]

    @staticmethod
    def _evidence_nodes(
        decision: DecisionIntelligence,
    ) -> list[DecisionEvidenceNode]:
        return [
            DecisionEvidenceNode(
                node_id=evidence.evidence_id,
                node_type="evidence",
                label=evidence.evidence_type,
                data={
                    "source_id": evidence.source_id,
                    "description": evidence.description,
                    "weight": evidence.weight,
                    **dict(evidence.data),
                },
            )
            for evidence in sorted(
                decision.evidence,
                key=lambda item: item.evidence_id,
            )
        ]

    @staticmethod
    def _edge(
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> DecisionEvidenceEdge:
        edge_id = (
            f"EDGE-{source_id}-{relationship}-{target_id}"
        )

        return DecisionEvidenceEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
        )

    @classmethod
    def build(
        cls,
        decision: DecisionIntelligence,
    ) -> DecisionEvidenceGraph:
        if not isinstance(
            decision,
            DecisionIntelligence,
        ):
            raise TypeError(
                "decision must be a DecisionIntelligence"
            )

        decision_node = cls._decision_node(
            decision
        )

        current_nodes = cls._current_nodes(
            decision
        )
        historical_nodes = cls._historical_nodes(
            decision
        )
        predictive_nodes = cls._predictive_nodes(
            decision
        )
        evidence_nodes = cls._evidence_nodes(
            decision
        )

        nodes = [
            decision_node,
            *current_nodes,
            *historical_nodes,
            *predictive_nodes,
            *evidence_nodes,
        ]

        node_ids = set()

        unique_nodes = []

        for node in nodes:
            if node.node_id in node_ids:
                continue

            node_ids.add(node.node_id)
            unique_nodes.append(node)

        edges = []

        for node in current_nodes:
            edges.append(
                cls._edge(
                    decision.decision_id,
                    node.node_id,
                    "CURRENT_DECISION",
                )
            )

        for node in historical_nodes:
            edges.append(
                cls._edge(
                    decision.decision_id,
                    node.node_id,
                    "HISTORICAL_CONTEXT",
                )
            )

        for node in predictive_nodes:
            edges.append(
                cls._edge(
                    decision.decision_id,
                    node.node_id,
                    "PREDICTIVE_CONTEXT",
                )
            )

        for evidence in evidence_nodes:
            edges.append(
                cls._edge(
                    decision.decision_id,
                    evidence.node_id,
                    "EVIDENCE",
                )
            )

        unique_edges = {
            edge.edge_id: edge
            for edge in edges
        }

        ordered_nodes = tuple(
            sorted(
                unique_nodes,
                key=lambda item: (
                    item.node_type,
                    item.node_id,
                ),
            )
        )

        ordered_edges = tuple(
            sorted(
                unique_edges.values(),
                key=lambda item: item.edge_id,
            )
        )

        return DecisionEvidenceGraph(
            decision_id=decision.decision_id,
            nodes=ordered_nodes,
            edges=ordered_edges,
        )

    @classmethod
    def build_many(
        cls,
        decisions: Iterable[DecisionIntelligence],
    ) -> tuple[DecisionEvidenceGraph, ...]:
        graphs = [
            cls.build(decision)
            for decision in decisions
        ]

        return tuple(
            sorted(
                graphs,
                key=lambda graph: graph.decision_id,
            )
        )
