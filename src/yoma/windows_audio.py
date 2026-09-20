"""Windows microphone adapter for the embedded YOMA runtime."""

from __future__ import annotations

import sounddevice as sd


class WindowsMicrophoneError(Exception):
    """Raised when Windows microphone capture fails."""


class WindowsMicrophone:
    """Capture bounded microphone audio using sounddevice."""

    def __init__(
        self,
        *,
        device: int | str | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
    ) -> None:
        self._device = device
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype

    def record(self, max_seconds: int) -> bytes:
        if max_seconds <= 0:
            raise WindowsMicrophoneError(
                "recording duration must be positive"
            )

        frames = self._sample_rate * max_seconds

        try:
            recording = sd.rec(
                frames,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                device=self._device,
            )
            sd.wait()
        except Exception as exc:
            raise WindowsMicrophoneError(
                "microphone capture failed"
            ) from exc

        try:
            return recording.tobytes()
        except Exception as exc:
            raise WindowsMicrophoneError(
                "microphone data conversion failed"
            ) from exc