"""Runtime failure isolation policy for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class FailureIsolationResult:
    isolated: bool
    total_components: int
    failed_components: tuple[str, ...]
    healthy_components: tuple[str, ...]
    failures: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "isolated": self.isolated,
            "total_components": self.total_components,
            "failed_components": list(self.failed_components),
            "healthy_components": list(self.healthy_components),
            "failures": list(self.failures),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class RuntimeFailureIsolation:
    """Read-only assessment of component-level runtime failures."""

    def assess(
        self,
        *,
        components: Iterable[str],
        failed_components: Iterable[str] = (),
        failures: Iterable[str] = (),
    ) -> FailureIsolationResult:
        component_set = tuple(dict.fromkeys(str(item) for item in components))
        failed_set = tuple(
            dict.fromkeys(
                str(item)
                for item in failed_components
                if str(item) in component_set
            )
        )

        healthy = tuple(
            component
            for component in component_set
            if component not in failed_set
        )

        failure_messages = tuple(dict.fromkeys(str(item) for item in failures))

        return FailureIsolationResult(
            isolated=True,
            total_components=len(component_set),
            failed_components=failed_set,
            healthy_components=healthy,
            failures=failure_messages,
        )
