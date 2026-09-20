from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]

def test_m55_voice_spec_exists():
    p = ROOT / "installer" / "voice" / "M55-VOICE-SPEC.json"
    assert p.exists()

def test_m55_voice_spec():
    p = ROOT / "installer" / "voice" / "M55-VOICE-SPEC.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["browser_setup"] is True
    assert data["local_url"] == "http://127.0.0.1:8766/"
    assert data["voice"]["stt"] == "faster-whisper"
    assert data["voice"]["tts"] == "Piper"
    assert data["voice"]["microphone"] is True

def test_m55_security_boundary():
    p = ROOT / "installer" / "voice" / "M55-VOICE-SPEC.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["security"]["execution_authority"] is False
    assert data["security"]["self_authorized_execution"] is False
    assert data["security"]["human_approval_required"] is True

def test_m55_browser_launcher():
    assert (ROOT / "installer" / "Open-YOMA.ps1").exists()
