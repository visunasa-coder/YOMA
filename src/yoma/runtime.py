"""Embedded YOMA runtime lifecycle and task execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import threading
from typing import Any, Callable


class RuntimeState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeStatus:
    mode: str
    state: RuntimeState
    voice_enabled: bool
    wake_word_enabled: bool


class RuntimeError(Exception):
    """Base error for embedded runtime failures."""


class YomaRuntime:
    """Lifecycle and execution facade for the embedded YOMA runtime.

    The runtime owns lifecycle and delegates task execution to an injected
    executor. It does not directly access databases, files, tools, agents,
    or external providers.
    """

    def __init__(
        self,
        *,
        mode: str = "embedded",
        voice_enabled: bool = False,
        wake_word_enabled: bool = False,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
        executor: Callable[[Any], Any] | None = None,
    ) -> None:
        self._mode = mode
        self._voice_enabled = voice_enabled
        self._wake_word_enabled = wake_word_enabled
        self._on_start = on_start
        self._on_stop = on_stop
        self._executor = executor
        self._state = RuntimeState.STOPPED
        self._lock = threading.RLock()

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state

    @property
    def running(self) -> bool:
        return self.state == RuntimeState.RUNNING

    def start(self) -> None:
        with self._lock:
            if self._state == RuntimeState.RUNNING:
                return

            if self._state in {
                RuntimeState.STARTING,
                RuntimeState.STOPPING,
            }:
                raise RuntimeError(
                    "runtime transition already in progress"
                )

            self._state = RuntimeState.STARTING

            try:
                if self._on_start is not None:
                    self._on_start()
            except Exception as exc:
                self._state = RuntimeState.FAILED
                raise RuntimeError("runtime startup failed") from exc

            self._state = RuntimeState.RUNNING

    def stop(self) -> None:
        with self._lock:
            if self._state == RuntimeState.STOPPED:
                return

            if self._state == RuntimeState.STOPPING:
                return

            self._state = RuntimeState.STOPPING

            try:
                if self._on_stop is not None:
                    self._on_stop()
            except Exception as exc:
                self._state = RuntimeState.FAILED
                raise RuntimeError("runtime shutdown failed") from exc

            self._state = RuntimeState.STOPPED

    def execute(self, task: Any) -> Any:
        """Execute a task through the configured runtime executor."""
        with self._lock:
            if self._state != RuntimeState.RUNNING:
                raise RuntimeError("runtime is not running")

            executor = self._executor

        if executor is None:
            raise RuntimeError("runtime executor is not configured")

        try:
            return executor(task)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("runtime task execution failed") from exc

    def status(self) -> RuntimeStatus:
        with self._lock:
            return RuntimeStatus(
                mode=self._mode,
                state=self._state,
                voice_enabled=self._voice_enabled,
                wake_word_enabled=self._wake_word_enabled,
            )