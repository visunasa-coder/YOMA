from dataclasses import dataclass
from enum import Enum


class DeviceTrustDecision(str, Enum):
    TRUSTED = "trusted"
    LIMITED = "limited"
    DENIED = "denied"


@dataclass(frozen=True)
class DevicePosture:
    device_id: str
    managed: bool
    integrity_ok: bool
    security_controls_ok: bool
    known: bool


@dataclass(frozen=True)
class DeviceTrustResult:
    decision: DeviceTrustDecision
    device_id: str
    reason: str
    requires_human_approval: bool = True
    executable: bool = False


class DeviceTrustEngine:
    def assess(self, posture: DevicePosture) -> DeviceTrustResult:
        if not posture.known:
            return DeviceTrustResult(
                DeviceTrustDecision.DENIED,
                posture.device_id,
                "unknown device",
            )

        if not posture.integrity_ok:
            return DeviceTrustResult(
                DeviceTrustDecision.DENIED,
                posture.device_id,
                "device integrity failure",
            )

        if not posture.managed or not posture.security_controls_ok:
            return DeviceTrustResult(
                DeviceTrustDecision.LIMITED,
                posture.device_id,
                "device posture is limited",
            )

        return DeviceTrustResult(
            DeviceTrustDecision.TRUSTED,
            posture.device_id,
            "device posture trusted",
        )
