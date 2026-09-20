from __future__ import annotations

import io
import time
import wave
from dataclasses import dataclass

from yoma.provider import GenerationPolicy, YOMAProvider
from yoma.context import AssembledContext


@dataclass(frozen=True)
class VoiceAssistantResult:
    transcript: str
    answer: str
    provider: str
    stt_engine: str
    tts_engine: str
    external_ai_required: bool
    latency_ms: float


class VoiceAssistant:
    """Local voice -> YOMA AI -> local voice orchestration."""

    def __init__(self, voice_engine) -> None:
        self.voice_engine = voice_engine
        self.provider = YOMAProvider()

    @staticmethod
    def _context(query: str) -> AssembledContext:
        return AssembledContext(
            query=query,
            system_instructions=(
                "You are YOMA, a local workplace AI assistant. "
                "Operate locally. Never bypass governance or human approval."
            ),
            blocks=(),
            character_count=len(query),
            conversation_messages=(),
            memory_blocks=(),
        )

    def process(self, audio: bytes) -> tuple[VoiceAssistantResult, bytes]:
        started = time.perf_counter()

        transcript = self.voice_engine.transcribe(audio)

        if not transcript.strip():
            raise ValueError("No speech was detected")

        context = self._context(transcript)

        result = self.provider.generate_answer(
            transcript,
            context,
            GenerationPolicy(external_egress_enabled=False),
        )

        if not result.answer:
            raise RuntimeError(result.reason or "YOMA did not produce an answer")

        output_audio = self.voice_engine.synthesize(result.answer)

        latency_ms = (time.perf_counter() - started) * 1000.0

        return (
            VoiceAssistantResult(
                transcript=transcript,
                answer=result.answer,
                provider=result.provider,
                stt_engine="faster-whisper-local",
                tts_engine="piper-local",
                external_ai_required=False,
                latency_ms=round(latency_ms, 2),
            ),
            output_audio,
        )


voice_assistant = VoiceAssistant
