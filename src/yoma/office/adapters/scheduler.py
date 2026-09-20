from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from yoma.office.adapters.runtime import (
    AdapterRuntimeManager,
    AdapterRuntimeResult,
)
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class AdapterSchedulerStatus:
    adapter: str
    status: str
    collection_count: int
    success_count: int
    failure_count: int
    events_collected: int
    last_collection_at: float | None
    last_error: str | None


@dataclass(frozen=True)
class SchedulerStatus:
    running: bool
    enabled: bool
    interval: float
    cycle_count: int
    events_collected: int
    last_cycle_at: float | None
    last_error: str | None
    adapters: tuple[AdapterSchedulerStatus, ...] = ()


class AdapterCollectionScheduler:
    """
    Runs provider-neutral adapter collection continuously in the background.

    The scheduler owns timing, lifecycle and observability.
    Adapter connection, retry and failure isolation remain the responsibility
    of AdapterRuntimeManager.
    """

    def __init__(
        self,
        manager: AdapterRuntimeManager,
        *,
        interval: float = 60.0,
        enabled: bool = True,
        on_events: Callable[[list[OperationalEvent]], None] | None = None,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be > 0")

        self.manager = manager
        self.interval = interval
        self.enabled = enabled
        self.on_events = on_events

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._lock = threading.Lock()
        self._cycle_count = 0
        self._events_collected = 0
        self._last_cycle_at: float | None = None
        self._last_error: str | None = None

        self._adapter_stats: dict[str, AdapterSchedulerStatus] = {}

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)

        with self._lock:
            self.enabled = enabled

        if not enabled:
            self.stop()

    def set_interval(self, interval: float) -> None:
        if interval <= 0:
            raise ValueError("interval must be > 0")

        with self._lock:
            self.interval = interval

    def _update_adapter_stats(
        self,
        result: AdapterRuntimeResult,
    ) -> None:
        previous = self._adapter_stats.get(result.adapter)

        collection_count = (
            previous.collection_count if previous else 0
        ) + 1

        success_count = (
            previous.success_count if previous else 0
        )

        failure_count = (
            previous.failure_count if previous else 0
        )

        if result.status == "collected":
            success_count += 1
        else:
            failure_count += 1

        events_collected = (
            previous.events_collected if previous else 0
        ) + result.events_collected

        self._adapter_stats[result.adapter] = AdapterSchedulerStatus(
            adapter=result.adapter,
            status=result.status,
            collection_count=collection_count,
            success_count=success_count,
            failure_count=failure_count,
            events_collected=events_collected,
            last_collection_at=time.time(),
            last_error=result.error,
        )

    def _run_cycle(self) -> None:
        try:
            events, results = self.manager.collect_all()

            with self._lock:
                self._cycle_count += 1
                self._events_collected += len(events)
                self._last_cycle_at = time.time()

                cycle_errors: list[str] = []

                for result in results:
                    self._update_adapter_stats(result)

                    if result.error is not None:
                        cycle_errors.append(
                            f"{result.adapter}:{result.error}"
                        )

                self._last_error = (
                    ";".join(cycle_errors)
                    if cycle_errors
                    else None
                )

            if events and self.on_events is not None:
                self.on_events(events)

        except Exception as exc:
            with self._lock:
                self._cycle_count += 1
                self._last_cycle_at = time.time()
                self._last_error = type(exc).__name__

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self.interval):
            self._run_cycle()

    def start(self) -> None:
        if not self.enabled:
            return

        if self.running:
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run_loop,
            name="yoma-adapter-collection-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        self._thread = None

    def run_once(self) -> None:
        """Run exactly one collection cycle synchronously."""
        self._run_cycle()

    def status(self) -> SchedulerStatus:
        with self._lock:
            return SchedulerStatus(
                running=self.running,
                enabled=self.enabled,
                interval=self.interval,
                cycle_count=self._cycle_count,
                events_collected=self._events_collected,
                last_cycle_at=self._last_cycle_at,
                last_error=self._last_error,
                adapters=tuple(self._adapter_stats.values()),
            )

    def adapter_status(
        self,
        adapter_name: str,
    ) -> AdapterSchedulerStatus | None:
        with self._lock:
            return self._adapter_stats.get(adapter_name)
