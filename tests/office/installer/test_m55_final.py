from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]

def test_installer_files():
    assert (ROOT/"installer"/"YOMA.iss").exists()
    assert (ROOT/"installer"/"Open-YOMA.ps1").exists()

def test_browser_page():
    assert (ROOT/"installer"/"download-page"/"index.html").exists()

def test_voice_agent():
    assert (ROOT/"installer"/"voice"/"yoma_voice_agent.py").exists()
    assert (ROOT/"installer"/"voice"/"SECURITY-BOUNDARY.json").exists()

def test_voice_security():
    data=json.loads(
        (ROOT/"installer"/"voice"/"SECURITY-BOUNDARY.json")
        .read_text(encoding="utf-8-sig")
    )
    assert data["voice_execution_authority"] is False
    assert data["self_authorized_execution"] is False
    assert data["human_approval_required"] is True

def test_voice_stack():
    data=json.loads(
        (ROOT/"installer"/"voice"/"SECURITY-BOUNDARY.json")
        .read_text(encoding="utf-8-sig")
    )
    assert data["stt"]=="faster-whisper"
    assert data["tts"]=="Piper"
