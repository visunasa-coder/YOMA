from pathlib import Path
import io
import wave

from yoma.voice_runtime import (
    InteractiveVoiceAgent, VoiceRuntimeConfig, VoiceSecurityBoundary,
    WhisperSTT, PiperTTS,
)


def wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"\0\0" * 160)
    return output.getvalue()


class FakeSTT:
    def transcribe(self, audio):
        assert audio.startswith(b"RIFF")
        return "status"


class FakeTTS:
    def synthesize(self, text):
        assert text
        return wav_bytes()


class FakeMic:
    def record(self, max_seconds):
        assert max_seconds > 0
        return wav_bytes()


class FakeSpeaker:
    def __init__(self):
        self.audio = None

    def play(self, audio):
        self.audio = audio


def test_m55_11_runtime_config_is_portable(tmp_path):
    config = VoiceRuntimeConfig.from_root(tmp_path)
    assert config.root == tmp_path.resolve()
    assert "VISHAL" not in str(config.piper_executable or "")


def test_m55_12_whisper_is_lazy_and_injectable(tmp_path):
    calls = []
    stt = WhisperSTT(VoiceRuntimeConfig.from_root(tmp_path),
                     model_factory=lambda *a, **k: calls.append((a, k)) or FakeModel())
    assert stt.transcribe(wav_bytes()) == "hello"
    assert len(calls) == 1


class FakeModel:
    def transcribe(self, path, vad_filter=True):
        return [type("Segment", (), {"text": " hello "})()], None


def test_m55_13_piper_does_not_execute_untrusted_path(tmp_path):
    config = VoiceRuntimeConfig.from_root(tmp_path)
    assert not config.piper_executable or config.piper_executable.is_absolute()
    assert PiperTTS(config).config.root == tmp_path.resolve()


def test_m55_14_to_17_user_session_pipeline_has_no_execution_authority(tmp_path):
    speaker = FakeSpeaker()
    agent = InteractiveVoiceAgent(
        microphone=FakeMic(), speaker=speaker, stt=FakeSTT(), tts=FakeTTS(),
        answer=lambda query: "YOMA is ready.", config=VoiceRuntimeConfig.from_root(tmp_path),
    )
    result = agent.run_once()
    assert result["transcript"] == "status"
    assert result["answer"] == "YOMA is ready."
    assert result["execution_authority"] is False
    assert speaker.audio.startswith(b"RIFF")


def test_m55_18_to_19_security_boundary_is_fail_closed():
    boundary = VoiceSecurityBoundary()
    assert boundary.execution_authority is False
    assert boundary.self_authorized_execution is False
    assert boundary.human_approval_required is True
