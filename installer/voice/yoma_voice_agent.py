"""YOMA interactive user-session voice agent entry point."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from yoma.voice_runtime import (  # noqa: E402
    InteractiveVoiceAgent, PiperTTS, VoiceRuntimeConfig, WindowsMicrophoneDevice, WindowsSpeaker, WhisperSTT,
)


def config_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    return base / "YOMA"


def status() -> dict:
    config = VoiceRuntimeConfig.from_root(ROOT)
    microphone = WindowsMicrophoneDevice()
    return {
        "voice_agent": True,
        "stt": "faster-whisper",
        "tts": "Piper",
        "microphone": microphone.permission_status(),
        "models": {
            "piper": bool(config.piper_model and config.piper_model.exists() and config.piper_config and config.piper_config.exists()),
            "whisper": (config.model_root / "whisper" / config.whisper_model).exists(),
        },
        "execution_authority": False,
        "self_authorized_execution": False,
        "requires_human_approval": True,
        "executable": False,
    }


def write_state(data: dict) -> None:
    target = config_dir() / "voice.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="YOMA user-session voice agent")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    current = status()
    write_state(current)
    if args.status:
        print(json.dumps(current, indent=2))
        return 0
    agent = InteractiveVoiceAgent(
        microphone=WindowsMicrophoneDevice(), speaker=WindowsSpeaker(),
        stt=WhisperSTT(VoiceRuntimeConfig.from_root(ROOT)),
        tts=PiperTTS(VoiceRuntimeConfig.from_root(ROOT)),
    )
    if args.once:
        print(json.dumps(agent.run_once(), indent=2))
        return 0
    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
