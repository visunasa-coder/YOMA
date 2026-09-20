from __future__ import annotations

import re
from typing import Any, Mapping


class AttendanceEnvironmentDiscovery:
    """
    Safe attendance-environment discovery.

    Discovery only identifies possible attendance devices.
    It does not connect, authenticate, configure, control,
    or modify any discovered device.
    """

    _attendance_keywords = (
        "attendance",
        "biometric",
        "zkteco",
        "zktech",
        "fingerprint",
        "time attendance",
        "access control",
        "punch",
        "clocking",
        "employee",
    )

    @staticmethod
    def _text(*values: Any) -> str:
        return " ".join(
            str(value).strip()
            for value in values
            if value is not None and str(value).strip()
        )

    @classmethod
    def _is_attendance(cls, *values: Any) -> bool:
        text = cls._text(*values).lower()
        return any(keyword in text for keyword in cls._attendance_keywords)

    @classmethod
    def _is_windows_attendance(cls, device: Mapping[str, Any]) -> bool:
        """
        Conservative Windows PnP attendance classification.

        Generic Windows hardware must not become an attendance candidate
        from loose substring matches. Classification requires a strong
        biometric, attendance-terminal, access-control, or known-vendor
        signal.
        """
        device_class = cls._text(device.get("class")).lower()
        name = cls._text(device.get("name")).lower()
        description = cls._text(device.get("description")).lower()

        strong_classes = {
            "biometric",
            "fingerprint",
        }

        if device_class in strong_classes:
            return True

        identity_text = " ".join(
            value for value in (name, description)
            if value
        )

        strong_phrases = (
            "zkteco",
            "zktech",
            "fingerprint",
            "biometric",
            "time attendance",
            "attendance terminal",
            "attendance device",
            "attendance reader",
            "access control terminal",
            "access control device",
            "access control reader",
            "punch terminal",
            "punch device",
            "clocking terminal",
        )

        # Match complete phrases rather than arbitrary substrings.
        padded = f" {identity_text} "

        return any(
            f" {phrase} " in padded
            for phrase in strong_phrases
        )

    @staticmethod
    def _hardware_ids(candidate: Mapping[str, Any]):
        vid = candidate.get("vid")
        pid = candidate.get("pid")

        if vid is not None and pid is not None:
            return int(vid), int(pid)

        instance_id = str(candidate.get("instance_id") or "").upper()

        match = re.search(
            r"VID_([0-9A-F]{4}).*PID_([0-9A-F]{4})",
            instance_id,
        )

        if match:
            return (
                int(match.group(1), 16),
                int(match.group(2), 16),
            )

        return None, None

    @classmethod
    def _device_key(cls, candidate: Mapping[str, Any]):
        manufacturer = cls._text(
            candidate.get("manufacturer")
        ).lower()

        name = cls._text(
            candidate.get("name")
        ).lower()

        # Prefer a stable human-readable identity when available.
        # This allows Windows PnP and serial discovery paths to
        # identify the same physical attendance device.
        if manufacturer and name:
            return ("named", manufacturer, name)

        # Otherwise use hardware identifiers.
        vid, pid = cls._hardware_ids(candidate)

        if vid is not None and pid is not None:
            return ("hardware", vid, pid)

        instance_id = cls._text(
            candidate.get("instance_id")
        ).lower()

        if instance_id:
            return ("instance", instance_id)

        return (
            "fallback",
            cls._text(
                candidate.get("device_class"),
                candidate.get("description"),
                candidate.get("name"),
            ).lower(),
        )
    @classmethod
    def _deduplicate(cls, candidates):
        unique = {}
        name_index = {}

        for candidate in candidates:
            name = cls._text(candidate.get("name")).lower()
            manufacturer = cls._text(
                candidate.get("manufacturer")
            ).lower()

            # Discovery mechanisms may expose different metadata for
            # the same physical device. When the device name matches,
            # treat the observations as one candidate.
            if name:
                name_key = ("attendance_name", manufacturer, name)

                # Also allow a Windows PnP observation without
                # manufacturer metadata to match a serial observation.
                generic_name_key = ("attendance_name", "", name)

                existing_key = name_index.get(name_key)

                if existing_key is None:
                    existing_key = name_index.get(generic_name_key)

                if existing_key is not None:
                    existing = unique[existing_key]

                    # Prefer the richer serial representation because
                    # it contains an actionable transport endpoint.
                    if (
                        existing.get("transport") == "windows_device"
                        and candidate.get("transport") == "serial"
                    ):
                        unique[existing_key] = candidate

                    continue

                unique[name_key] = candidate
                name_index[name_key] = name_key

                if manufacturer:
                    name_index[generic_name_key] = name_key

                continue

            key = cls._device_key(candidate)

            if key not in unique:
                unique[key] = candidate

        return list(unique.values())

    def classify(self, environment: Mapping[str, Any]):
        if not isinstance(environment, Mapping):
            raise TypeError("environment must be a mapping")

        candidates = []

        # Serial attendance devices
        for device in environment.get("serial_ports", ()) or ():
            if not isinstance(device, Mapping):
                continue

            if not self._is_attendance(
                device.get("name"),
                device.get("description"),
                device.get("manufacturer"),
            ):
                continue

            candidates.append(
                {
                    "category": "attendance",
                    "transport": "serial",
                    "port": device.get("port"),
                    "name": device.get("name"),
                    "description": device.get("description"),
                    "manufacturer": device.get("manufacturer"),
                    "vid": device.get("vid"),
                    "pid": device.get("pid"),
                    "confidence": "possible",
                    "source": "local_environment",
                    "requires_human_approval": True,
                    "executable": False,
                }
            )

        # Windows PnP attendance/biometric devices
        for device in environment.get("windows_devices", ()) or ():
            if not isinstance(device, Mapping):
                continue

            if not self._is_windows_attendance(device):
                continue

            candidates.append(
                {
                    "category": "attendance",
                    "transport": "windows_device",
                    "name": device.get("name"),
                    "device_class": device.get("class"),
                    "status": device.get("status"),
                    "instance_id": device.get("instance_id"),
                    "confidence": "possible",
                    "source": "local_environment",
                    "requires_human_approval": True,
                    "executable": False,
                }
            )

        return self._deduplicate(candidates)
