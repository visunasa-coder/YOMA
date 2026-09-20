@echo off
cd /d "%~dp0"

set YOMA_AI_PROVIDER=yoma-native
set YOMA_EXTERNAL_AI_EGRESS_ENABLED=false

if not exist "data\logs" mkdir "data\logs"

".venv\Scripts\python.exe" -m uvicorn yoma.app:app --host 127.0.0.1 --port 8765 >> "data\logs\yoma-startup.log" 2>&1
