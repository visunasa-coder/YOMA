"""Enterprise upgrade and recovery safety for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class UpgradeRecoveryResult:
    safe: bool
    installed: bool
    lifecycle: str
    recovery_required: bool
    upgrade_allowed: bool
    repair_allowed: bool
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "installed": self.installed,
            "lifecycle": self.lifecycle,
            "recovery_required": self.recovery_required,
            "upgrade_allowed": self.upgrade_allowed,
            "repair_allowed": self.repair_allowed,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class UpgradeRecoverySafety:
    """Read-only safety assessment for deployment upgrades and recovery."""

    def assess(
        self,
        *,
        installed: bool,
        lifecycle: str,
        service_state: str,
        runtime_state: str,
        startup_diagnostics: Mapping[str, Any] | None = None,
    ) -> UpgradeRecoveryResult:
        diagnostics = startup_diagnostics or {}

        recovery_required = bool(diagnostics.get("recovery_required", False))

        if not installed:
            return UpgradeRecoveryResult(
                safe=True,
                installed=False,
                lifecycle=lifecycle,
                recovery_required=False,
                upgrade_allowed=False,
                repair_allowed=True,
                reason="deployment is not installed",
            )

        if recovery_required or service_state == "failed" or runtime_state == "failed":
            return UpgradeRecoveryResult(
                safe=False,
                installed=True,
                lifecycle=lifecycle,
                recovery_required=True,
                upgrade_allowed=False,
                repair_allowed=True,
                reason="recovery required before upgrade",
            )

        if service_state == "running" or runtime_state == "running":
            return UpgradeRecoveryResult(
                safe=True,
                installed=True,
                lifecycle=lifecycle,
                recovery_required=False,
                upgrade_allowed=True,
                repair_allowed=False,
                reason="deployment is operational",
            )

        return UpgradeRecoveryResult(
            safe=True,
            installed=True,
            lifecycle=lifecycle,
            recovery_required=False,
            upgrade_allowed=True,
            repair_allowed=True,
            reason="deployment is installed but stopped",
        )
