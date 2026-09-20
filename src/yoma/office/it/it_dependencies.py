from __future__ import annotations

from dataclasses import dataclass


_VALID_TYPES = {
    "task",
    "project",
    "service",
    "member",
    "ticket",
    "incident",
}

_VALID_STATUSES = {
    "open",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
}


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ITDependencyNode:
    node_id: str
    organization_id: str
    node_type: str
    status: str = "open"
    owner_id: str | None = None
    title: str = ""

    def __post_init__(self) -> None:
        _text(self.node_id, "node_id")
        _text(self.organization_id, "organization_id")

        if self.node_type not in _VALID_TYPES:
            raise ValueError(f"invalid node_type: {self.node_type}")

        if self.status not in _VALID_STATUSES:
            raise ValueError(f"invalid status: {self.status}")

        if self.owner_id is not None:
            _text(self.owner_id, "owner_id")

        if not isinstance(self.title, str):
            raise ValueError("title must be a string")


@dataclass(frozen=True)
class ITDependency:
    dependency_id: str
    organization_id: str
    source_node_id: str
    target_node_id: str
    dependency_type: str = "blocks"

    def __post_init__(self) -> None:
        _text(self.dependency_id, "dependency_id")
        _text(self.organization_id, "organization_id")
        _text(self.source_node_id, "source_node_id")
        _text(self.target_node_id, "target_node_id")
        _text(self.dependency_type, "dependency_type")

        if self.source_node_id == self.target_node_id:
            raise ValueError("source_node_id and target_node_id must differ")


@dataclass(frozen=True)
class ITDependencyPortfolio:
    organization_id: str
    nodes: tuple[ITDependencyNode, ...] = ()
    dependencies: tuple[ITDependency, ...] = ()

    def __post_init__(self) -> None:
        _text(self.organization_id, "organization_id")

        if not isinstance(self.nodes, tuple):
            raise ValueError("nodes must be a tuple")

        if not isinstance(self.dependencies, tuple):
            raise ValueError("dependencies must be a tuple")

        node_ids: set[str] = set()

        for node in self.nodes:
            if not isinstance(node, ITDependencyNode):
                raise ValueError(
                    "nodes must contain ITDependencyNode instances"
                )

            if node.organization_id != self.organization_id:
                raise ValueError("node organization_id mismatch")

            if node.node_id in node_ids:
                raise ValueError(
                    f"duplicate node_id: {node.node_id}"
                )

            node_ids.add(node.node_id)

        dependency_ids: set[str] = set()

        for dependency in self.dependencies:
            if not isinstance(dependency, ITDependency):
                raise ValueError(
                    "dependencies must contain ITDependency instances"
                )

            if dependency.organization_id != self.organization_id:
                raise ValueError(
                    "dependency organization_id mismatch"
                )

            if dependency.dependency_id in dependency_ids:
                raise ValueError(
                    f"duplicate dependency_id: {dependency.dependency_id}"
                )

            dependency_ids.add(dependency.dependency_id)

            if dependency.source_node_id not in node_ids:
                raise ValueError(
                    f"unknown source node: {dependency.source_node_id}"
                )

            if dependency.target_node_id not in node_ids:
                raise ValueError(
                    f"unknown target node: {dependency.target_node_id}"
                )


@dataclass(frozen=True)
class ITDependencyAnalysis:
    organization_id: str
    node_count: int
    dependency_count: int
    blocked_dependency_count: int
    critical_dependency_count: int
    dependency_hotspot_node_id: str | None
    dependency_hotspot_count: int
    bottleneck_node_count: int
    cycle_count: int
    missing_owner_node_count: int
    upstream_impact_node_count: int
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


@dataclass(frozen=True)
class ITDependencyIntelligence:
    """
    Read-only dependency and bottleneck intelligence.

    This component detects structural dependency risks and bottlenecks.
    It never changes dependencies, assignments, priorities, status,
    scheduling, or execution state.
    """

    bottleneck_threshold: int = 3

    def __post_init__(self) -> None:
        if isinstance(self.bottleneck_threshold, bool):
            raise ValueError("bottleneck_threshold must be an integer")

        if not isinstance(self.bottleneck_threshold, int):
            raise ValueError("bottleneck_threshold must be an integer")

        if self.bottleneck_threshold < 1:
            raise ValueError(
                "bottleneck_threshold must be at least 1"
            )

    def analyze(
        self,
        portfolio: ITDependencyPortfolio,
    ) -> ITDependencyAnalysis:
        if not isinstance(portfolio, ITDependencyPortfolio):
            raise TypeError(
                "portfolio must be ITDependencyPortfolio"
            )

        nodes = tuple(
            sorted(
                portfolio.nodes,
                key=lambda node: node.node_id,
            )
        )

        dependencies = tuple(
            sorted(
                portfolio.dependencies,
                key=lambda dependency: dependency.dependency_id,
            )
        )

        node_map = {
            node.node_id: node
            for node in nodes
        }

        blocked_dependencies = 0
        critical_dependencies = 0

        incoming: dict[str, list[str]] = {
            node.node_id: []
            for node in nodes
        }

        outgoing: dict[str, list[str]] = {
            node.node_id: []
            for node in nodes
        }

        for dependency in dependencies:
            source = node_map[dependency.source_node_id]
            target = node_map[dependency.target_node_id]

            incoming[target.node_id].append(source.node_id)
            outgoing[source.node_id].append(target.node_id)

            if (
                source.status == "blocked"
                or target.status == "blocked"
            ):
                blocked_dependencies += 1

            if (
                source.status in {"blocked", "open", "in_progress"}
                and target.status in {"open", "in_progress"}
            ):
                critical_dependencies += 1

        dependency_counts = {
            node.node_id: len(incoming[node.node_id])
            + len(outgoing[node.node_id])
            for node in nodes
        }

        hotspot_node_id = None
        hotspot_count = 0

        if dependency_counts:
            hotspot_node_id, hotspot_count = max(
                dependency_counts.items(),
                key=lambda item: (item[1], item[0]),
            )

        bottleneck_node_count = sum(
            1
            for count in dependency_counts.values()
            if count >= self.bottleneck_threshold
        )

        missing_owner = sum(
            1
            for node in nodes
            if node.status not in {"completed", "cancelled"}
            and node.owner_id is None
        )

        cycles = self._find_cycles(
            tuple(node.node_id for node in nodes),
            outgoing,
        )

        upstream_impact = self._count_upstream_impact(
            nodes,
            incoming,
            node_map,
        )

        issues: list[str] = []

        if blocked_dependencies:
            issues.append(
                f"{blocked_dependencies} dependencies involve blocked nodes"
            )

        if critical_dependencies:
            issues.append(
                f"{critical_dependencies} active dependencies require attention"
            )

        if hotspot_node_id is not None and hotspot_count > 0:
            if hotspot_count >= self.bottleneck_threshold:
                issues.append(
                    f"dependency hotspot detected at node "
                    f"{hotspot_node_id}"
                )

        if bottleneck_node_count:
            issues.append(
                f"{bottleneck_node_count} nodes meet the configured "
                f"dependency bottleneck threshold"
            )

        if cycles:
            issues.append(
                f"{len(cycles)} dependency cycles detected"
            )

        if missing_owner:
            issues.append(
                f"{missing_owner} active dependency nodes have no owner"
            )

        if upstream_impact:
            issues.append(
                f"{upstream_impact} downstream nodes have upstream dependency impact"
            )

        return ITDependencyAnalysis(
            organization_id=portfolio.organization_id,
            node_count=len(nodes),
            dependency_count=len(dependencies),
            blocked_dependency_count=blocked_dependencies,
            critical_dependency_count=critical_dependencies,
            dependency_hotspot_node_id=hotspot_node_id,
            dependency_hotspot_count=hotspot_count,
            bottleneck_node_count=bottleneck_node_count,
            cycle_count=len(cycles),
            missing_owner_node_count=missing_owner,
            upstream_impact_node_count=upstream_impact,
            issues=tuple(issues),
            requires_human_approval=True,
            executable=False,
        )

    @staticmethod
    def _find_cycles(
        node_ids: tuple[str, ...],
        outgoing: dict[str, list[str]],
    ) -> tuple[tuple[str, ...], ...]:
        cycles: set[tuple[str, ...]] = set()

        def canonical_cycle(path: list[str]) -> tuple[str, ...]:
            minimum = min(range(len(path)), key=lambda i: path[i])
            rotated = path[minimum:] + path[:minimum]
            return tuple(rotated)

        def visit(
            start: str,
            current: str,
            path: list[str],
            active: set[str],
        ) -> None:
            for target in sorted(outgoing.get(current, [])):
                if target == start and len(path) >= 2:
                    cycles.add(canonical_cycle(path))
                elif target not in active and len(path) < len(node_ids):
                    active.add(target)
                    path.append(target)

                    visit(
                        start,
                        target,
                        path,
                        active,
                    )

                    path.pop()
                    active.remove(target)

        for start in node_ids:
            visit(
                start,
                start,
                [start],
                {start},
            )

        return tuple(
            sorted(cycles)
        )

    @staticmethod
    def _count_upstream_impact(
        nodes: tuple[ITDependencyNode, ...],
        incoming: dict[str, list[str]],
        node_map: dict[str, ITDependencyNode],
    ) -> int:
        impacted: set[str] = set()

        for node in nodes:
            if node.status != "blocked":
                continue

            stack = list(incoming.get(node.node_id, []))
            visited: set[str] = set()

            while stack:
                current = stack.pop()

                if current in visited:
                    continue

                visited.add(current)
                impacted.add(current)

                stack.extend(
                    incoming.get(current, [])
                )

        return len(impacted)


def analyze_it_dependencies(
    portfolio: ITDependencyPortfolio,
) -> ITDependencyAnalysis:
    return ITDependencyIntelligence().analyze(portfolio)
