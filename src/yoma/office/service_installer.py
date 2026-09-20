from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yoma.office.windows_service import WindowsServiceAdapter


class ServiceInstaller:
    """Provider-neutral installation lifecycle manager for the YOMA service."""

    def __init__(
        self,
        adapter: WindowsServiceAdapter,
        *,
        state_path: str | Path,
    ) -> None:
        if adapter is None:
            raise ValueError("Service adapter is required")

        self.adapter = adapter
        self.state_path = Path(state_path)

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}

        try:
            data = json.loads(self.state_path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

        return data if isinstance(data, dict) else {}

    def _write_state(self, data: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(data, indent=2)
        )

    def installed(self) -> bool:
        return bool(self._read_state().get("installed", False))

    def install(self) -> None:
        """Install the service state without starting the service."""
        data = self._read_state()

        data["installed"] = True
        data.setdefault("auto_start", False)
        data.setdefault("lifecycle", "installed")

        self._write_state(data)

    def upgrade(
        self,
        *,
        version: str | None = None,
    ) -> None:
        """Upgrade an existing installation while preserving its state."""
        data = self._read_state()

        if not data.get("installed", False):
            raise RuntimeError("cannot upgrade an uninstalled service")

        if version is not None:
            if not isinstance(version, str) or not version.strip():
                raise ValueError("version must not be empty")
            data["version"] = version

        data["installed"] = True
        data["lifecycle"] = "upgraded"

        self._write_state(data)

    def repair(self) -> None:
        """Repair missing installation markers without starting the service."""
        data = self._read_state()

        data["installed"] = True
        data.setdefault("auto_start", False)
        data["lifecycle"] = "repaired"

        self._write_state(data)

    def uninstall(self) -> None:
        """Remove installation state without destroying the service adapter."""
        if not self.state_path.exists():
            return

        self.state_path.unlink()

    def auto_start(self) -> bool:
        return bool(self._read_state().get("auto_start", False))

    def set_auto_start(self, enabled: bool) -> None:
        data = self._read_state()
        data["auto_start"] = bool(enabled)
        self._write_state(data)

    def status(self) -> dict[str, Any]:
        service_status = self.adapter.status()

        return {
            "installed": self.installed(),
            "auto_start": self.auto_start(),
            "service_state": service_status["state"],
            "runtime_state": service_status["runtime_state"],
        }
