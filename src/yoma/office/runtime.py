from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRegistry,
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.decision import DecisionOrchestrator
from yoma.office.governance import PersistentGovernedActionExecutor
from yoma.office.identity import IdentityRegistryManager
from yoma.office.integration import (
    AdapterEventCollector,
    IntegrationEventBridge,
    IntegrationPersistence,
    IntegrationRuntimeManager,
)
from yoma.office.intelligence import OperationalIntelligenceEngine
from yoma.office.operations import OperationalEvent, OperationalEventBus
from yoma.office.runtime_state import RuntimeStatePersistence
from yoma.office.licensing.trial_subscription import TrialSubscriptionManager


@dataclass(frozen=True)
class EmbeddedRuntimeStatus:
    running: bool
    runtime_state: str
    adapter_count: int
    identity_provider: str | None
    subscriber_count: int
    scheduler_running: bool
    scheduler_cycle_count: int
    scheduler_events_collected: int
    scheduler_last_error: str | None
    integration_count: int


class YomaEmbeddedRuntime:
    def __init__(
        self,
        *,
        identity: IdentityRegistryManager | None = None,
        bus: OperationalEventBus | None = None,
        intelligence: OperationalIntelligenceEngine | None = None,
        decisions: DecisionOrchestrator | None = None,
        governed_executor: PersistentGovernedActionExecutor | None = None,
        collection_interval: float = 60.0,
        integration_runtime: IntegrationRuntimeManager | None = None,
        integration_persistence: IntegrationPersistence | None = None,
        runtime_state_persistence: RuntimeStatePersistence | None = None,
        trial_subscription: TrialSubscriptionManager | None = None,
    ) -> None:
        self.identity = identity
        self.bus = bus or OperationalEventBus()
        self.bridge = IntegrationEventBridge(self.bus)

        self.adapters = AdapterRegistry()
        self.adapter_runtime = AdapterRuntimeManager(self.adapters)
        self.collector = AdapterEventCollector(self.bridge)

        self.intelligence = intelligence or OperationalIntelligenceEngine()
        self.decisions = decisions or DecisionOrchestrator()
        self.governed_executor = governed_executor

        self.integration_runtime = (
            integration_runtime
            if integration_runtime is not None
            else IntegrationRuntimeManager(
                persistence=integration_persistence,
            )
        )

        self.runtime_state_persistence = runtime_state_persistence
        self.trial_subscription = trial_subscription
        self._license_blocked = False
        self._license_notification: str | None = None

        self.scheduler = AdapterCollectionScheduler(
            self.adapter_runtime,
            interval=collection_interval,
            on_events=self._handle_collected_events,
        )

        self._running = False
        self._runtime_state = "stopped"
        self._restored_integrations = False

    def register_adapter(self, adapter: YomaAdapter) -> None:
        self.adapters.register(adapter)

    def unregister_adapter(self, name: str) -> bool:
        return self.adapters.unregister(name)

    def publish(self, event: OperationalEvent) -> OperationalEvent:
        if not self._running:
            raise RuntimeError("YOMA embedded runtime is not running")

        self.bus.publish(event)
        return event

    def _handle_collected_events(
        self,
        events: list[OperationalEvent],
    ) -> None:
        if not events:
            return

        self.bus.publish_many(events)

    def collect_events(self) -> list[OperationalEvent]:
        if not self._running:
            raise RuntimeError("YOMA embedded runtime is not running")

        events, _results = self.adapter_runtime.collect_all()

        if events:
            self.bus.publish_many(events)

        return events

    def analyze(self, events: list[OperationalEvent]) -> list[Any]:
        if not self._running:
            raise RuntimeError("YOMA embedded runtime is not running")

        return self.intelligence.analyze(events)

    def decide(self, signals: list[Any]) -> list[Any]:
        if not self._running:
            raise RuntimeError("YOMA embedded runtime is not running")

        return self.decisions.evaluate_many(signals)

    def restore_integrations(self):
        if self._restored_integrations:
            return []

        restored = self.integration_runtime.restore()
        self._restored_integrations = True

        return restored

    def start(self) -> None:
        if self._running:
            return

        self._runtime_state = "booting"
        self._persist_runtime_state("booting", "startup_begin")

        try:
            self.restore_integrations()

            if self.trial_subscription is not None:
                if not self.trial_subscription.can_run_yoma():
                    self._license_blocked = True
                    self._license_notification = (
                        self.trial_subscription.notification()
                    )
                    self._runtime_state = "license_expired"
                    self._persist_runtime_state(
                        "license_expired",
                        self._license_notification or "license_blocked",
                    )
                    return

                self._license_blocked = False
                self._license_notification = None

            self._running = True
            self.scheduler.start()
            self._runtime_state = "running"
            self._persist_runtime_state("running", "startup_complete")
        except Exception as exc:
            self._running = False
            self._runtime_state = "failed"
            self._persist_runtime_state("failed", str(exc))
            raise

    def stop(self) -> None:
        if not self._running:
            self._runtime_state = "stopped"
            self._persist_runtime_state("stopped", "shutdown_complete")
            return

        self._runtime_state = "stopping"
        self._persist_runtime_state("stopping", "shutdown_begin")

        try:
            self.scheduler.stop()
        finally:
            self._running = False
            self._runtime_state = "stopped"
            self._persist_runtime_state("stopped", "shutdown_complete")

    @property
    def running(self) -> bool:
        return self._running

    @property
    def license_blocked(self) -> bool:
        return self._license_blocked

    @property
    def license_notification(self) -> str | None:
        return self._license_notification

    def _persist_runtime_state(self, state: str, reason: str) -> None:
        if self.runtime_state_persistence is not None:
            self.runtime_state_persistence.save(
                state=state,
                reason=reason,
            )

    def status(self) -> EmbeddedRuntimeStatus:
        scheduler_status = self.scheduler.status()

        return EmbeddedRuntimeStatus(
            running=self._running,
            runtime_state=self._runtime_state,
            adapter_count=len(self.adapters),
            identity_provider=(
                self.identity.provider
                if self.identity is not None
                else None
            ),
            subscriber_count=self.bus.subscriber_count,
            scheduler_running=scheduler_status.running,
            scheduler_cycle_count=scheduler_status.cycle_count,
            scheduler_events_collected=scheduler_status.events_collected,
            scheduler_last_error=scheduler_status.last_error,
            integration_count=len(self.integration_runtime.status()),
        )
