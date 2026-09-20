from __future__ import annotations

import re
from typing import Any


class HardwareClassifier:
    """
    Classifies Windows Plug-and-Play devices into YOMA categories.

    Classification is heuristic only. It does not activate or connect
    to any device.
    """

    def _contains_term(self, name: str, term: str) -> bool:
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        return re.search(pattern, name, re.IGNORECASE) is not None

    def classify(self, device: dict[str, Any]) -> str:
        device_class = str(device.get("class") or "").strip().lower()
        name = str(device.get("name") or "").strip().lower()
        instance_id = str(device.get("instance_id") or "").strip().upper()

        attendance_terms = (
            "fingerprint",
            "biometric",
            "time attendance",
            "attendance terminal",
            "access control",
            "zkteco",
            "essl",
            "matrix",
            "suprema",
        )

        if any(self._contains_term(name, term) for term in attendance_terms):
            return "attendance"

        security_terms = (
            "camera",
            "cctv",
            "ip camera",
            "webcam",
            "video capture",
            "dvr",
            "nvr",
        )

        if any(self._contains_term(name, term) for term in security_terms):
            return "security"

        if device_class == "ports" or "USB\\VID_" in instance_id:
            return "serial_or_usb"

        if device_class == "bluetooth" or instance_id.startswith("BTH"):
            return "bluetooth"

        if device_class == "net":
            return "network"

        return "other"

    def classify_all(
        self,
        devices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        classified = []

        for device in devices:
            item = dict(device)
            item["yoma_category"] = self.classify(device)
            classified.append(item)

        return classified

    def office_devices(
        self,
        devices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        classified = self.classify_all(devices)

        return [
            device
            for device in classified
            if device["yoma_category"]
            in {
                "attendance",
                "security",
                "serial_or_usb",
                "bluetooth",
                "network",
            }
        ]
