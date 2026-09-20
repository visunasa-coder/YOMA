"""Bounded audio-capture boundary for the embedded YOMA runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AudioCaptureError(Exception):
    """Base error for audio capture failures."""


class AudioLimitError(AudioCaptureError):
    """Raised when captured audio exceeds configured limits."""


class AudioCaptureDevice(Protocol):
    """Hardware-facing microphone abstraction."""

    def record(self, max_seconds: int) -> bytes:
        ...


class UnavailableAudioDevice:
    """Safe device used when microphone hardware is unavailable."""

    def record(self, max_seconds: int) -> bytes:
        raise AudioCaptureError("audio capture device is unavailable")


@dataclass(frozen=True)
class AudioCaptureLimits:
    max_seconds: int
    max_bytes: int


class AudioCapture:
    """Validate and bound microphone input.

    This class deliberately does not implement OS-specific microphone access.
    Hardware adapters can be injected later without changing YOMA's security
    or assistant layers.
    """

    def __init__(
        self,
        *,
        device: AudioCaptureDevice,
        limits: AudioCaptureLimits,
    ) -> None:
        self._device = device
        self._limits = limits

    def record(self) -> bytes:
        if self._limits.max_seconds <= 0:
            raise AudioLimitError("audio duration limit is invalid")

        if self._limits.max_bytes <= 0:
            raise AudioLimitError("audio size limit is invalid")

        audio = self._device.record(self._limits.max_seconds)

        if not isinstance(audio, bytes):
            raise AudioCaptureError("audio device returned invalid data")

        if not audio:
            raise AudioCaptureError("audio capture returned empty data")

        if len(audio) > self._limits.max_bytes:
            raise AudioLimitError("captured audio exceeds configured limit")

        return audio