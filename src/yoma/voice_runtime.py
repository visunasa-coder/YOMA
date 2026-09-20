"""Local M55 voice runtime.

The runtime is deliberately split from the control server.  It owns audio
input/output and speech conversion only; it never plans or executes tools.
"""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
import wave
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .audio import AudioCapture, AudioCaptureDevice, AudioCaptureLimits
from .context import AssembledContext
from .provider import GenerationPolicy, YOMAProvider
from .voice import VoiceLimits, VoiceService


class VoiceRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoiceSecurityBoundary:
    execution_authority: bool = False
    self_authorized_execution: bool = False
    human_approval_required: bool = True
    role: str = "input_output_only"


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    root: Path
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    piper_executable: Path | None = None
    piper_model: Path | None = None
    piper_config: Path | None = None
    max_seconds: int = 30
    max_audio_bytes: int = 5 * 1024 * 1024
    max_transcript_chars: int = 4000
    timeout_seconds: float = 30.0

    @property
    def model_root(self) -> Path:
        return self.root / "models"

    @classmethod
    def from_root(cls, root: str | Path) -> "VoiceRuntimeConfig":
        root = Path(root).resolve()
        voice = root / "models" / "piper" / "en_US-lessac-medium"
        executable = root / "runtime" / "piper" / "piper.exe"
        if not executable.is_file():
            executable = None
        return cls(root=root, piper_executable=executable,
                   piper_model=voice / "en_US-lessac-medium.onnx",
                   piper_config=voice / "en_US-lessac-medium.onnx.json")


def _validate_wav(data: bytes) -> None:
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            if source.getnchannels() < 1 or source.getframerate() <= 0:
                raise ValueError
    except (wave.Error, EOFError, ValueError) as exc:
        raise VoiceRuntimeError("audio must be a valid WAV recording") from exc


class WhisperSTT:
    """Lazy faster-whisper adapter; model loading occurs on first request."""

    name = "faster-whisper"

    def __init__(self, config: VoiceRuntimeConfig, model_factory: Callable | None = None):
        self.config = config
        self._model = None
        self._model_factory = model_factory

    def _load(self):
        if self._model is not None:
            return self._model
        factory = self._model_factory
        if factory is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise VoiceRuntimeError("faster-whisper is not installed") from exc
            factory = WhisperModel
        model_path = self.config.model_root / "whisper" / self.config.whisper_model
        model = model_path if model_path.exists() else self.config.whisper_model
        self._model = factory(str(model), device=self.config.whisper_device,
                              compute_type=self.config.whisper_compute_type)
        return self._model

    def transcribe(self, audio: bytes) -> str:
        _validate_wav(audio)
        model = self._load()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            handle.write(audio)
            path = Path(handle.name)
        try:
            segments, _ = model.transcribe(str(path), vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            path.unlink(missing_ok=True)


class PiperTTS:
    """Piper subprocess adapter with an explicit executable/model allowlist."""

    name = "Piper"

    def __init__(self, config: VoiceRuntimeConfig):
        self.config = config

    def synthesize(self, text: str) -> bytes:
        executable = self.config.piper_executable
        model = self.config.piper_model
        voice_config = self.config.piper_config
        if not executable or not executable.exists():
            raise VoiceRuntimeError("Piper executable is not installed")
        if not model or not model.exists() or not voice_config or not voice_config.exists():
            raise VoiceRuntimeError("Piper voice model is not installed")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            output = Path(handle.name)
        try:
            subprocess.run([str(executable), "--model", str(model), "--config", str(voice_config),
                            "--output_file", str(output)], input=text.encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                           timeout=self.config.timeout_seconds, shell=False)
            audio = output.read_bytes()
            _validate_wav(audio)
            return audio
        except subprocess.TimeoutExpired as exc:
            raise VoiceRuntimeError("Piper synthesis timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise VoiceRuntimeError("Piper synthesis failed") from exc
        finally:
            output.unlink(missing_ok=True)


class WindowsSpeaker:
    """User-session speaker adapter.  Importing sounddevice remains lazy."""

    def play(self, audio: bytes) -> None:
        _validate_wav(audio)
        try:
            import sounddevice as sd
            import numpy as np
            with wave.open(io.BytesIO(audio), "rb") as source:
                frames = source.readframes(source.getnframes())
                samples = np.frombuffer(frames, dtype="<i2")
                if source.getnchannels() > 1:
                    samples = samples.reshape(-1, source.getnchannels())
                sd.play(samples, source.getframerate())
                sd.wait()
        except ImportError as exc:
            raise VoiceRuntimeError("speaker runtime is not installed") from exc
        except Exception as exc:
            raise VoiceRuntimeError("speaker output failed") from exc


class WindowsMicrophoneDevice(AudioCaptureDevice):
    """Bounded microphone capture in the interactive user session."""

    def __init__(self, device: int | str | None = None, sample_rate: int = 16000):
        self.device = device
        self.sample_rate = sample_rate

    def permission_status(self) -> dict:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
            return {"available": bool(inputs), "permission": "granted" if inputs else "denied",
                    "input_devices": len(inputs)}
        except Exception as exc:
            return {"available": False, "permission": "unknown", "reason": str(exc)}

    def record(self, max_seconds: int) -> bytes:
        try:
            import sounddevice as sd
            recording = sd.rec(self.sample_rate * max_seconds, samplerate=self.sample_rate,
                               channels=1, dtype="int16", device=self.device)
            sd.wait()
            with io.BytesIO() as output:
                with wave.open(output, "wb") as target:
                    target.setnchannels(1); target.setsampwidth(2); target.setframerate(self.sample_rate)
                    target.writeframes(recording.tobytes())
                return output.getvalue()
        except Exception as exc:
            raise VoiceRuntimeError("microphone capture or permission failed") from exc


class InteractiveVoiceAgent:
    """One-shot and interactive user-session voice loop."""

    security = VoiceSecurityBoundary()

    def __init__(self, *, microphone: AudioCaptureDevice, speaker, stt, tts,
                 answer: Callable[[str], str] | None = None,
                 config: VoiceRuntimeConfig | None = None):
        self.config = config or VoiceRuntimeConfig.from_root(Path.cwd())
        limits = VoiceLimits(self.config.max_audio_bytes, self.config.max_transcript_chars)
        self.voice = VoiceService(stt=stt, tts=tts, limits=limits)
        self.capture = AudioCapture(device=microphone,
                                     limits=AudioCaptureLimits(self.config.max_seconds, self.config.max_audio_bytes))
        self.speaker = speaker
        self.answer = answer or self._local_answer

    @staticmethod
    def _local_answer(query: str) -> str:
        context = AssembledContext(query=query, system_instructions="YOMA is governed; never execute actions without human approval.",
                                   blocks=(), character_count=len(query), conversation_messages=(), memory_blocks=())
        result = YOMAProvider().generate_answer(query, context, GenerationPolicy(external_egress_enabled=False))
        return result.answer or "YOMA could not answer that request."

    def run_once(self) -> dict:
        transcript = self.voice.transcribe(self.capture.record())
        answer = self.answer(transcript)
        output = self.voice.synthesize(answer)
        self.speaker.play(output)
        return {"transcript": transcript, "answer": answer, "stt": "faster-whisper",
                "tts": "Piper", "execution_authority": False, "human_approval_required": True}

    def run(self, stop: Callable[[], bool] | None = None, on_result: Callable[[dict], None] | None = None) -> None:
        while not (stop and stop()):
            result = self.run_once()
            if on_result:
                on_result(result)
