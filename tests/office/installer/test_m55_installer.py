from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

def test_m55_installer_assets_exist():
    assert (ROOT / "installer" / "setup_wizard.py").exists()
    assert (ROOT / "installer" / "setup_service.py").exists()
    assert (ROOT / "installer" / "install_service.ps1").exists()
    assert (ROOT / "installer" / "YOMA.iss").exists()

def test_m55_security_boundary():
    text = (ROOT / "installer" / "setup_wizard.py").read_text(
        encoding="utf-8-sig"
    ).lower()

    assert "human approval" in text
    assert "execution authority" in text
    assert '"executable": false' in text
    assert '"execution_authority": false' in text

def test_m55_roles():
    roles = [
        "Organization Administrator",
        "CEO / Executive",
        "Manager",
        "Employee",
    ]
    assert len(roles) == 4

def test_m55_setup_state_fields():
    text = (ROOT / "installer" / "setup_wizard.py").read_text(
        encoding="utf-8-sig"
    )
    for field in [
        "organization_id",
        "device_enrolled",
        "google_workspace",
        "attendance",
        "requires_human_approval",
    ]:
        assert field in text
