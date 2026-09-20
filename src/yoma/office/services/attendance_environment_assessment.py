from __future__ import annotations

from typing import Any, Mapping

from .attendance_adapter_planner import AttendanceAdapterCandidatePlanner
from .attendance_discovery import AttendanceEnvironmentDiscovery


class AttendanceEnvironmentAssessment:
    """
    Safe end-to-end assessment of the local attendance environment.

    Discovery and adapter planning only.
    No probing, authentication, connection, configuration,
    activation, or device modification is performed.
    """

    def __init__(
        self,
        discovery: AttendanceEnvironmentDiscovery | None = None,
        planner: AttendanceAdapterCandidatePlanner | None = None,
    ) -> None:
        self.discovery = discovery or AttendanceEnvironmentDiscovery()
        self.planner = planner or AttendanceAdapterCandidatePlanner()

    def assess(self, environment: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(environment, Mapping):
            raise TypeError("environment must be a mapping")

        discovered = self.discovery.classify(environment)
        plans = self.planner.plan_all(discovered)

        return {
            "category": "attendance",
            "platform": environment.get("platform"),
            "candidate_count": len(discovered),
            "candidates": plans,
            "discovery_only": True,
            "requires_human_approval": True,
            "executable": False,
            "activation_allowed": False,
        }
