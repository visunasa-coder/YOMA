from pathlib import Path
import json, os, subprocess, sys, winreg

APP_NAME = "YOMA"
SERVICE_NAME = "YomaControlServer"
INSTALL_ROOT = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "YOMA"
CONFIG_DIR = INSTALL_ROOT / "config"
STATE_FILE = CONFIG_DIR / "first_run.json"

FEATURES = [
    "AI Workplace Assistant",
    "Attendance & Device Intelligence",
    "Google Workspace Integration",
    "Enterprise Security",
    "Data Protection",
    "Organization Governance",
]

def is_first_run():
    return not STATE_FILE.exists()

def ensure_directories():
    INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return True

def save_setup_state(role, organization=None, completed=False):
    ensure_directories()
    data = {
        "application": APP_NAME,
        "role": role,
        "organization": organization,
        "completed": bool(completed),
        "google_workspace": False,
        "attendance": "pending",
        "device_enrolled": False,
    }
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def setup_status():
    if not STATE_FILE.exists():
        return {"first_run": True, "completed": False}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        data["first_run"] = False
        return data
    except Exception:
        return {"first_run": True, "completed": False}

def main():
    print("YOMA First-Run Setup")
    print("Features:")
    for feature in FEATURES:
        print(" -", feature)
    print()
    print("Installer/setup backend ready.")
    print("First run:", is_first_run())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
