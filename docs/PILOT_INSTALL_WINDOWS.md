# YOMA Windows Pilot Installation

Use Python 3.12 and a project-local virtual environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Set pilot configuration in the PowerShell session or a protected local launcher. Never commit the values:

```powershell
$env:YOMA_BOOTSTRAP_USERNAME = "pilot-admin"
$env:YOMA_BOOTSTRAP_PASSWORD = "use-a-unique-local-password"
$env:YOMA_HOST = "127.0.0.1"
$env:YOMA_PORT = "8765"
$env:YOMA_EXTERNAL_AI_EGRESS_ENABLED = "false"
$env:YOMA_EXTERNAL_INTEGRATION_EGRESS_ENABLED = "false"
```

Start and check the service:

```powershell
.\.venv\Scripts\python.exe -m uvicorn yoma.app:app --host 127.0.0.1 --port 8765
Invoke-RestMethod http://127.0.0.1:8765/healthz
Invoke-RestMethod http://127.0.0.1:8765/readyz
Invoke-RestMethod http://127.0.0.1:8765/version
```

Stop with `Ctrl+C`. Keep the first pilot on synthetic or non-confidential data and localhost only.
