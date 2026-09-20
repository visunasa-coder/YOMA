from __future__ import annotations

import json
import platform
import socket
import subprocess
from typing import Any


class HardwareDiscoveryService:
    """
    Safe hardware discovery for YOMA.

    Discovery only identifies possible devices.
    It does not automatically authenticate, control,
    configure, or modify them.
    """

    def discover_windows_devices(self) -> list[dict[str, Any]]:
        if platform.system() != "Windows":
            return []

        command = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "[Console]::OutputEncoding = "
                "[System.Text.Encoding]::UTF8; "
                "Get-PnpDevice -PresentOnly | "
                "Select-Object Class,FriendlyName,Status,InstanceId | "
                "ConvertTo-Json -Compress"
            ),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []

        stdout = result.stdout or ""

        if result.returncode != 0 or not stdout.strip():
            return []

        try:
            data = json.loads(stdout)

            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list):
                return []

            return [
                {
                    "class": item.get("Class"),
                    "name": item.get("FriendlyName"),
                    "status": item.get("Status"),
                    "instance_id": item.get("InstanceId"),
                }
                for item in data
                if isinstance(item, dict)
            ]

        except (ValueError, TypeError):
            return []

    def discover_serial_ports(self) -> list[dict[str, Any]]:
        try:
            import serial.tools.list_ports
        except ImportError:
            return []

        devices = []

        for port in serial.tools.list_ports.comports():
            devices.append(
                {
                    "transport": "serial",
                    "port": port.device,
                    "name": port.name,
                    "description": port.description,
                    "manufacturer": port.manufacturer,
                    "vid": port.vid,
                    "pid": port.pid,
                    "serial_number": port.serial_number,
                }
            )

        return devices

    def local_network_identity(self) -> dict[str, Any]:
        try:
            hostname = socket.gethostname()
            address = socket.gethostbyname(hostname)
        except OSError:
            hostname = "unknown"
            address = "unknown"

        return {
            "hostname": hostname,
            "address": address,
        }

    def discover(self) -> dict[str, Any]:
        return {
            "platform": platform.system(),
            "windows_devices": self.discover_windows_devices(),
            "serial_ports": self.discover_serial_ports(),
            "network_identity": self.local_network_identity(),
        }
