$ErrorActionPreference = "Stop"

$YomaRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $YomaRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $YomaRoot "data\logs"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path $Python)) {
    throw "YOMA Python environment not found: $Python"
}

$env:YOMA_AI_PROVIDER = "yoma-native"
$env:YOMA_EXTERNAL_AI_EGRESS_ENABLED = "false"

Set-Location $YomaRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "        YOMA EMBEDDED LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root: $YomaRoot"
Write-Host "Provider: $env:YOMA_AI_PROVIDER"
Write-Host "External AI egress: $env:YOMA_EXTERNAL_AI_EGRESS_ENABLED"
Write-Host ""

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $logFile = Join-Path $LogDir "yoma-$timestamp.log"

    Write-Host "Starting YOMA API..." -ForegroundColor Green
    Write-Host "Log: $logFile"

    & $Python -m uvicorn yoma.app:app `
        --host 127.0.0.1 `
        --port 8765 `
        --log-level info `
        *> $logFile

    $exitCode = $LASTEXITCODE

    Write-Host "YOMA API exited with code $exitCode" -ForegroundColor Yellow

    if ($exitCode -eq 0) {
        break
    }

    Write-Host "YOMA crashed. Restarting in 3 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}
