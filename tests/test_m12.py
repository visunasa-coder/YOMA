from yoma.audio import (
    AudioCapture,
    AudioCaptureError,
    AudioCaptureLimits,
    AudioLimitError,
    UnavailableAudioDevice,
)
from yoma.runtime import RuntimeState, RuntimeError, YomaRuntime
from yoma.voice import (
    NoneSpeechToTextProvider,
    NoneTextToSpeechProvider,
    VoiceError,
    VoiceLimitError,
    VoiceLimits,
    VoiceService,
)


# ---------------------------------------------------------------------------
# Runtime tests
# ---------------------------------------------------------------------------

def test_runtime_starts_and_stops() -> None:
    events: list[str] = []

    runtime = YomaRuntime(
        mode="embedded",
        voice_enabled=False,
        wake_word_enabled=False,
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
    )

    assert runtime.state == RuntimeState.STOPPED
    assert not runtime.running

    runtime.start()

    assert runtime.state == RuntimeState.RUNNING
    assert runtime.running
    assert events == ["start"]

    runtime.start()

    assert runtime.state == RuntimeState.RUNNING
    assert events == ["start"]

    runtime.stop()

    assert runtime.state == RuntimeState.STOPPED
    assert not runtime.running
    assert events == ["start", "stop"]

    runtime.stop()

    assert events == ["start", "stop"]


def test_runtime_status() -> None:
    runtime = YomaRuntime(
        mode="embedded",
        voice_enabled=True,
        wake_word_enabled=True,
    )

    status = runtime.status()

    assert status.mode == "embedded"
    assert status.state == RuntimeState.STOPPED
    assert status.voice_enabled is True
    assert status.wake_word_enabled is True


def test_runtime_start_failure_fails_closed() -> None:
    def fail_start() -> None:
        raise RuntimeError("simulated startup failure")

    runtime = YomaRuntime(
        mode="embedded",
        on_start=fail_start,
    )

    try:
        runtime.start()
    except RuntimeError as exc:
        assert str(exc) == "runtime startup failed"
    else:
        raise AssertionError("runtime startup should have failed")

    assert runtime.state == RuntimeState.FAILED
    assert not runtime.running


def test_runtime_stop_failure_fails_closed() -> None:
    def fail_stop() -> None:
        raise Exception("shutdown failure")

    runtime = YomaRuntime(
        mode="embedded",
        on_start=lambda: None,
        on_stop=fail_stop,
    )

    runtime.start()

    try:
        runtime.stop()
    except RuntimeError as exc:
        assert str(exc) == "runtime shutdown failed"
    else:
        raise AssertionError("runtime shutdown should have failed")

    assert runtime.state == RuntimeState.FAILED
    assert not runtime.running


# ---------------------------------------------------------------------------
# Voice tests
# ---------------------------------------------------------------------------

class FakeSTT:
    def transcribe(self, audio: bytes) -> str:
        return "hello YOMA"


class FakeTTS:
    def synthesize(self, text: str) -> bytes:
        return b"audio"


def test_voice_transcription_is_bounded() -> None:
    service = VoiceService(
        stt=FakeSTT(),
        tts=FakeTTS(),
        limits=VoiceLimits(
            max_audio_bytes=10,
            max_transcript_chars=100,
        ),
    )

    assert service.transcribe(b"audio") == "hello YOMA"


def test_voice_rejects_empty_and_oversized_audio() -> None:
    service = VoiceService(
        stt=FakeSTT(),
        tts=FakeTTS(),
        limits=VoiceLimits(
            max_audio_bytes=4,
            max_transcript_chars=100,
        ),
    )

    try:
        service.transcribe(b"")
    except VoiceError:
        pass
    else:
        raise AssertionError("empty audio should be rejected")

    try:
        service.transcribe(b"12345")
    except VoiceLimitError:
        pass
    else:
        raise AssertionError("oversized audio should be rejected")


def test_voice_rejects_oversized_transcript() -> None:
    class LargeSTT:
        def transcribe(self, audio: bytes) -> str:
            return "x" * 101

    service = VoiceService(
        stt=LargeSTT(),
        tts=FakeTTS(),
        limits=VoiceLimits(
            max_audio_bytes=100,
            max_transcript_chars=100,
        ),
    )

    try:
        service.transcribe(b"audio")
    except VoiceLimitError:
        pass
    else:
        raise AssertionError("oversized transcript should be rejected")


def test_voice_tts_is_bounded() -> None:
    service = VoiceService(
        stt=FakeSTT(),
        tts=FakeTTS(),
        limits=VoiceLimits(
            max_audio_bytes=100,
            max_transcript_chars=100,
        ),
    )

    assert service.synthesize("hello") == b"audio"


def test_none_voice_providers_fail_safely() -> None:
    service = VoiceService(
        stt=NoneSpeechToTextProvider(),
        tts=NoneTextToSpeechProvider(),
        limits=VoiceLimits(
            max_audio_bytes=100,
            max_transcript_chars=100,
        ),
    )

    try:
        service.transcribe(b"audio")
    except VoiceError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("none STT should be unavailable")

    try:
        service.synthesize("hello")
    except VoiceError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("none TTS should be unavailable")


# ---------------------------------------------------------------------------
# Audio capture tests
# ---------------------------------------------------------------------------

class FakeAudioDevice:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.requested_seconds: int | None = None

    def record(self, max_seconds: int) -> bytes:
        self.requested_seconds = max_seconds
        return self.data


def test_audio_capture_is_bounded() -> None:
    device = FakeAudioDevice(b"audio")

    capture = AudioCapture(
        device=device,
        limits=AudioCaptureLimits(
            max_seconds=30,
            max_bytes=100,
        ),
    )

    assert capture.record() == b"audio"
    assert device.requested_seconds == 30


def test_audio_capture_rejects_oversized_audio() -> None:
    device = FakeAudioDevice(b"12345")

    capture = AudioCapture(
        device=device,
        limits=AudioCaptureLimits(
            max_seconds=30,
            max_bytes=4,
        ),
    )

    try:
        capture.record()
    except AudioLimitError:
        pass
    else:
        raise AssertionError("oversized captured audio should be rejected")


def test_audio_capture_rejects_empty_audio() -> None:
    device = FakeAudioDevice(b"")

    capture = AudioCapture(
        device=device,
        limits=AudioCaptureLimits(
            max_seconds=30,
            max_bytes=100,
        ),
    )

    try:
        capture.record()
    except AudioCaptureError:
        pass
    else:
        raise AssertionError("empty captured audio should be rejected")


def test_unavailable_audio_device_fails_safely() -> None:
    capture = AudioCapture(
        device=UnavailableAudioDevice(),
        limits=AudioCaptureLimits(
            max_seconds=30,
            max_bytes=100,
        ),
    )

    try:
        capture.record()
    except AudioCaptureError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("unavailable device should fail safely")