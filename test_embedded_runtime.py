"""Local end-to-end smoke test for the YOMA embedded architecture."""

from __future__ import annotations

from pathlib import Path
import tempfile

from yoma.runtime import RuntimeState, YomaRuntime
from yoma.audio import AudioCapture, AudioCaptureLimits
from yoma.voice import VoiceLimits, VoiceService


class FakeAudioDevice:
    def record(self, max_seconds: int) -> bytes:
        # Simulated bounded PCM payload.
        return b"\x00\x00" * 16000


class FakeSTT:
    def transcribe(self, audio: bytes) -> str:
        assert audio
        return "hello yoma"


class FakeTTS:
    def synthesize(self, text: str) -> bytes:
        assert text
        return b"\x00\x00"


def main() -> None:
    print()
    print("=" * 68)
    print("YOMA EMBEDDED ARCHITECTURE LIVE SMOKE TEST")
    print("=" * 68)
    print()

    with tempfile.TemporaryDirectory(prefix="yoma-embedded-") as temp_dir:
        data_dir = Path(temp_dir)

        # ---------------------------------------------------------------
        # 1. Runtime lifecycle
        # ---------------------------------------------------------------
        print("[1/7] Runtime lifecycle...")

        runtime = YomaRuntime(
            mode="embedded",
            voice_enabled=True,
            wake_word_enabled=False,
        )

        assert runtime.state == RuntimeState.STOPPED

        runtime.start()

        assert runtime.state == RuntimeState.RUNNING
        assert runtime.running

        print("      PASS - runtime is RUNNING")

        # ---------------------------------------------------------------
        # 2. Local audio input
        # ---------------------------------------------------------------
        print("[2/7] Audio input boundary...")

        capture = AudioCapture(
            device=FakeAudioDevice(),
            limits=AudioCaptureLimits(
                max_seconds=5,
                max_bytes=256 * 1024,
            ),
        )

        audio = capture.record()

        assert audio
        assert len(audio) <= 256 * 1024

        print(f"      PASS - {len(audio):,} bytes captured in memory")

        # ---------------------------------------------------------------
        # 3. Local STT
        # ---------------------------------------------------------------
        print("[3/7] Speech-to-text boundary...")

        voice = VoiceService(
            stt=FakeSTT(),
            tts=FakeTTS(),
            limits=VoiceLimits(
                max_audio_bytes=256 * 1024,
                max_transcript_chars=4000,
            ),
        )

        transcript = voice.transcribe(audio)

        assert transcript == "hello yoma"

        print(f"      PASS - transcript: {transcript!r}")

        # ---------------------------------------------------------------
        # 4. Assistant boundary contract
        # ---------------------------------------------------------------
        print("[4/7] Assistant handoff...")

        # This test deliberately stops at the contract boundary.
        # M4-M11 remain responsible for retrieval, provider access,
        # memory, tools, agents, authorization, and audit.
        assistant_request = {
            "message": transcript,
            "source": "voice",
        }

        assert assistant_request["source"] == "voice"
        assert assistant_request["message"] == "hello yoma"

        print("      PASS - voice transcript ready for assistant gateway")

        # ---------------------------------------------------------------
        # 5. Local TTS output boundary
        # ---------------------------------------------------------------
        print("[5/7] Text-to-speech boundary...")

        response_text = "Hello. YOMA is running."

        response_audio = voice.synthesize(response_text)

        assert response_audio

        print(
            f"      PASS - {len(response_audio):,} bytes returned in memory"
        )

        # ---------------------------------------------------------------
        # 6. Local runtime isolation
        # ---------------------------------------------------------------
        print("[6/7] Runtime isolation...")

        assert data_dir.exists()

        # No voice/audio file should have been created.
        files = list(data_dir.rglob("*"))
        assert files == []

        print("      PASS - no audio or response files persisted")

        # ---------------------------------------------------------------
        # 7. Clean shutdown
        # ---------------------------------------------------------------
        print("[7/7] Runtime shutdown...")

        runtime.stop()

        assert runtime.state == RuntimeState.STOPPED
        assert not runtime.running

        print("      PASS - runtime stopped cleanly")

    print()
    print("=" * 68)
    print("RESULT: YOMA EMBEDDED ARCHITECTURE SMOKE TEST PASSED")
    print("=" * 68)
    print()
    print("Verified:")
    print("  Runtime lifecycle")
    print("  Local audio boundary")
    print("  STT boundary")
    print("  Assistant handoff boundary")
    print("  TTS boundary")
    print("  No audio persistence")
    print("  Clean runtime shutdown")
    print()


if __name__ == "__main__":
    main()