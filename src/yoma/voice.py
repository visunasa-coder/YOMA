"""Provider-neutral voice input/output boundaries for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class VoiceError(Exception):
    """Base error for voice subsystem failures."""


class VoiceLimitError(VoiceError):
    """Raised when an audio or transcript limit is exceeded."""


class SpeechToTextProvider(Protocol):
    """Convert bounded audio input into text."""

    def transcribe(self, audio: bytes) -> str:
        ...


class TextToSpeechProvider(Protocol):
    """Convert bounded text into audio output."""

    def synthesize(self, text: str) -> bytes:
        ...


class NoneSpeechToTextProvider:
    """Safe provider used when STT is not configured."""

    def transcribe(self, audio: bytes) -> str:
        raise VoiceError("speech-to-text provider is unavailable")


class NoneTextToSpeechProvider:
    """Safe provider used when TTS is not configured."""

    def synthesize(self, text: str) -> bytes:
        raise VoiceError("text-to-speech provider is unavailable")


@dataclass(frozen=True)
class VoiceLimits:
    max_audio_bytes: int
    max_transcript_chars: int


class VoiceService:
    """Bounded voice boundary.

    This service does not access files, databases, tools, agents, or the
    network. Providers are explicitly injected by the application.
    """

    def __init__(
        self,
        *,
        stt: SpeechToTextProvider,
        tts: TextToSpeechProvider,
        limits: VoiceLimits,
    ) -> None:
        self._stt = stt
        self._tts = tts
        self._limits = limits

    def transcribe(self, audio: bytes) -> str:
        if not isinstance(audio, bytes):
            raise VoiceError("audio input is invalid")

        if not audio:
            raise VoiceError("audio input is empty")

        if len(audio) > self._limits.max_audio_bytes:
            raise VoiceLimitError("audio input exceeds configured limit")

        transcript = self._stt.transcribe(audio)

        if not isinstance(transcript, str):
            raise VoiceError("speech-to-text provider returned invalid data")

        transcript = transcript.strip()

        if not transcript:
            raise VoiceError("speech-to-text provider returned empty text")

        if len(transcript) > self._limits.max_transcript_chars:
            raise VoiceLimitError("transcript exceeds configured limit")

        return transcript

    def synthesize(self, text: str) -> bytes:
        if not isinstance(text, str):
            raise VoiceError("speech text is invalid")

        text = text.strip()

        if not text:
            raise VoiceError("speech text is empty")

        if len(text) > self._limits.max_transcript_chars:
            raise VoiceLimitError("speech text exceeds configured limit")

        audio = self._tts.synthesize(text)

        if not isinstance(audio, bytes):
            raise VoiceError("text-to-speech provider returned invalid data")

        return audio