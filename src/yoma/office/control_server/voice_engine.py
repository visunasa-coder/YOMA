from __future__ import annotations

from pathlib import Path

from yoma.voice_runtime import PiperTTS, VoiceRuntimeConfig, WhisperSTT


class LocalVoiceEngine:
    def __init__(self, root: str | Path | None = None):
        root = Path(root) if root else Path(__file__).resolve().parents[4]
        self.config = VoiceRuntimeConfig.from_root(root)
        self.model_path = self.config.piper_model
        self.config_path = self.config.piper_config
        self._stt = WhisperSTT(self.config)
        self._tts = PiperTTS(self.config)

    @property
    def available(self):
        return bool(self.model_path and self.model_path.exists() and self.config_path and self.config_path.exists() and self.config.piper_executable and self.config.piper_executable.exists())

    def status(self):
        return {
            "available": self.available,
            "stt": "faster-whisper-local",
            "tts": "piper-local",
            "external_ai_required": False,
            "model": self.model_path.name if self.model_path and self.model_path.exists() else None,
            "execution_authority": False,
            "self_authorized_execution": False,
            "human_approval_required": True,
        }

    def transcribe(self, audio: bytes) -> str:
        return self._stt.transcribe(audio)

    def synthesize(self, text: str) -> bytes:
        return self._tts.synthesize(text)


voice_engine = LocalVoiceEngine()
