from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrganizationalIntelligenceResult:
    organization_id: str
    foundation: Any
    structure: Any
    capacity: Any
    workload: Any
    workload_risk: Any
    dependency: Any
    coverage: Any
    validated: bool
    validation_errors: tuple[str, ...]
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalIntelligenceRuntime:
    """
    M36.8 — Organizational Intelligence Composition & Validation.

    Final read-only composition layer for M36.1–M36.7.

    Composition and validation only.
    No execution.
    No approval.
    No mutation.
    """

    def build(
        self,
        foundation: Any,
        structure: Any,
        capacity: Any,
        workload: Any,
        workload_risk: Any,
        dependency: Any,
        coverage: Any,
        *,
        organization_id: str,
    ) -> OrganizationalIntelligenceResult:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        components = {
            "foundation": foundation,
            "structure": structure,
            "capacity": capacity,
            "workload": workload,
            "workload_risk": workload_risk,
            "dependency": dependency,
            "coverage": coverage,
        }

        errors: list[str] = []

        for name, component in components.items():
            if component is None:
                errors.append(f"{name} component is missing")
                continue

            component_org = getattr(
                component,
                "organization_id",
                None,
            )

            if str(component_org).strip() != organization_id:
                errors.append(
                    f"{name} component organization_id does not match"
                )

            if getattr(component, "read_only", None) is not True:
                errors.append(
                    f"{name} component is not read-only"
                )

            if getattr(component, "executable", None) is not False:
                errors.append(
                    f"{name} component is executable"
                )

        foundation_members = getattr(
            foundation,
            "total_members",
            None,
        )

        component_member_counts = {
            "structure": getattr(structure, "total_members", None),
            "capacity": getattr(capacity, "total_members", None),
            "workload": getattr(workload, "total_members", None),
            "workload_risk": getattr(workload_risk, "total_members", None),
            "dependency": getattr(dependency, "total_members", None),
            "coverage": getattr(coverage, "total_members", None),
        }

        if foundation_members is not None:
            for name, count in component_member_counts.items():
                if count is not None and count != foundation_members:
                    errors.append(
                        f"{name} total_members does not match foundation"
                    )

        validated = not errors

        return OrganizationalIntelligenceResult(
            organization_id=organization_id,
            foundation=foundation,
            structure=structure,
            capacity=capacity,
            workload=workload,
            workload_risk=workload_risk,
            dependency=dependency,
            coverage=coverage,
            validated=validated,
            validation_errors=tuple(errors),
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.8",
                "composition_only": True,
                "validation_only": True,
                "analytics_only": True,
                "read_only": True,
                "executable": False,
                "components": (
                    "M36.1",
                    "M36.2",
                    "M36.3",
                    "M36.4",
                    "M36.5",
                    "M36.6",
                    "M36.7",
                ),
            },
        )
