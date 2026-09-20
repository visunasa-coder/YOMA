from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import uvicorn

from ...runtime import YomaEmbeddedRuntime
from ...licensing.trial_persistence import TrialSubscriptionPersistence
from ...licensing.trial_subscription import TrialSubscriptionManager
from ...intelligence.operational_unified_runtime import OperationalUnifiedRuntime
from ..agent import ControlServerAgent
from ..api import create_control_server_app


class ControlServerRuntime:
    """Owns the lifecycle of the YOMA Control Server and embedded runtime."""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8766

    def __init__(
        self,
        agent: ControlServerAgent | None = None,
        embedded_runtime: YomaEmbeddedRuntime | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        intelligence_runtime: OperationalUnifiedRuntime | None = None,
        organization_id: str = "pilot",
        deployment_id: str = "local",
        subscription_persistence_path: str | Path | None = None,
    ) -> None:
        if intelligence_runtime is not None and not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an "
                "OperationalUnifiedRuntime or None"
            )

        if agent is not None and intelligence_runtime is not None:
            if agent.intelligence_runtime is not None:
                if agent.intelligence_runtime is not intelligence_runtime:
                    raise ValueError(
                        "agent already has a different intelligence_runtime"
                    )
            else:
                agent.intelligence_runtime = intelligence_runtime

        self.agent = agent or ControlServerAgent(
            intelligence_runtime=intelligence_runtime,
        )

        if subscription_persistence_path is None:
            from pathlib import Path as _Path
            import os as _os

            data_root = _Path(
                _os.environ.get(
                    "PROGRAMDATA",
                    _Path.home() / "AppData" / "Local",
                )
            ) / "YOMA"

            subscription_persistence_path = (
                data_root / "subscription.json"
            )

        self.subscription_persistence = TrialSubscriptionPersistence(
            subscription_persistence_path
        )

        self.trial_subscription = TrialSubscriptionManager(
            organization_id=organization_id,
            deployment_id=deployment_id,
            persistence=self.subscription_persistence,
        )

        self.trial_subscription.ensure_initialized()

        self.embedded_runtime = (
            embedded_runtime
            or YomaEmbeddedRuntime(
                trial_subscription=self.trial_subscription,
            )
        )

        self.host = host
        self.port = port

        self.app = create_control_server_app(self.agent)
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> None:
        if self.running:
            return

        self.agent.start()
        self.embedded_runtime.start()

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )

        self.server = uvicorn.Server(config)

        self.thread = threading.Thread(
            target=self.server.run,
            name="yoma-control-server-api",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)

        self.thread = None
        self.server = None

        if self.embedded_runtime.running:
            self.embedded_runtime.stop()

        if self.agent.running:
            self.agent.stop()

    def status(self) -> dict[str, Any]:
        runtime_status = self.embedded_runtime.status()

        subscription_status = self.trial_subscription.status()

        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "subscription": subscription_status.as_dict(),
            "agent_running": self.agent.running,
            "embedded_runtime": {
                "running": runtime_status.running,
                "adapter_count": runtime_status.adapter_count,
                "identity_provider": runtime_status.identity_provider,
                "subscriber_count": runtime_status.subscriber_count,
            },
            "intelligence": self.agent.intelligence_status(),
        }
