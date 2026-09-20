param(
    [string]$Version="0.55.0",
    [string]$SigningCertificateThumbprint,
    [switch]$UseTestSigningCertificate,
    [string]$TimestampServer
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
if(-not (Test-Path $python)){ throw "YOMA virtual environment is missing: $python" }
Push-Location $root
try {
    if(-not (Test-Path (Join-Path $root "models\piper\en_US-lessac-medium\en_US-lessac-medium.onnx"))){ throw "Piper voice model is missing" }
    if(-not (Test-Path (Join-Path $root "models\whisper\base"))){ throw "faster-whisper model is missing: provision models\\whisper\\base before packaging" }
    if(-not (Test-Path (Join-Path $root "runtime\piper\piper.exe"))){ throw "Piper runtime is missing: provision runtime\\piper\\piper.exe before packaging" }
    & $python -m PyInstaller --noconfirm YOMA-ControlServer.spec
    & $python -m PyInstaller --noconfirm YOMA-Voice-Agent.spec
    & $python -m PyInstaller --noconfirm YOMA-Setup-Wizard.spec
    if ($SigningCertificateThumbprint -or $UseTestSigningCertificate) {
        $signer = Join-Path $root "scripts\sign_yoma_artifacts.ps1"
        $signParameters = @{
            Path = @(
                (Join-Path $root "dist\YOMA-ControlServer.exe"),
                (Join-Path $root "dist\YOMA-Voice-Agent.exe"),
                (Join-Path $root "dist\YOMA-Setup-Wizard.exe")
            )
        }
        if ($SigningCertificateThumbprint) { $signParameters.CertificateThumbprint = $SigningCertificateThumbprint }
        if ($UseTestSigningCertificate) { $signParameters.CreateTestCertificate = $true }
        if ($TimestampServer) { $signParameters.TimestampServer = $TimestampServer }
        & $signer @signParameters
    }
    if(-not (Get-Command ISCC.exe -ErrorAction SilentlyContinue)){ throw "Inno Setup ISCC.exe is required to build YOMA-Setup.exe" }
    & ISCC.exe "/DAppVersion=$Version" installer\YOMA.iss
    $installer = Join-Path $root "dist\YOMA-Setup.exe"
    $hash = (Get-FileHash $installer -Algorithm SHA256).Hash
    [pscustomobject]@{ product="YOMA"; milestone="M55"; version=$Version; installer="YOMA-Setup.exe"; installer_sha256=$hash; execution_authority=$false; self_authorized_execution=$false; requires_human_approval=$true } |
        ConvertTo-Json | Set-Content (Join-Path $root "installer\download-page\YOMA-M55-RELEASE.json") -Encoding UTF8
    $hash | Set-Content (Join-Path $root "dist\YOMA-Setup.exe.sha256") -Encoding ASCII
} finally { Pop-Location }
