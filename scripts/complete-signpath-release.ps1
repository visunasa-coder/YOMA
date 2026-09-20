param(
    [Parameter(Mandatory)][string]$SignedInstallerPath,
    [string]$Version = '0.55.0',
    [string]$SignToolPath = $env:YOMA_SIGNTOOL_PATH
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'release-common.ps1')
$stage = Join-Path $root 'release\staging'
$installer = Join-Path $stage 'installer\YOMA-Setup.exe'
if (-not (Test-Path -LiteralPath $SignedInstallerPath)) { throw "Signed SignPath installer was not found: $SignedInstallerPath" }
if (-not (Test-Path -LiteralPath (Join-Path $stage 'app'))) { throw 'Signed application staging is missing.' }

New-Item -ItemType Directory -Path (Split-Path $installer -Parent) -Force | Out-Null
Copy-Item -LiteralPath $SignedInstallerPath -Destination $installer -Force
$signTool = Find-YomaSignTool -ConfiguredPath $SignToolPath
$signature = Get-YomaSignatureInfo -Path $installer
if ($signature.status -ne 'Valid') { throw 'Returned SignPath installer is not validly signed.' }
Assert-YomaNotTestCertificate -Signature $signature
Invoke-YomaSignTool -SignTool $signTool -Arguments @('verify','/pa','/all','/tw',$installer)

Copy-Item -LiteralPath (Join-Path $root 'docs\RELEASE_WINDOWS.md') -Destination (Join-Path $stage 'RELEASE_WINDOWS.md') -Force
Copy-Item -LiteralPath (Join-Path $root 'release\build-environment.txt') -Destination (Join-Path $stage 'build-environment.txt') -Force
New-YomaReleaseManifest -Root $stage -ManifestPath (Join-Path $stage 'release-manifest.json') -Version $Version -Stage 'final-signpath' | Out-Null
& (Join-Path $root 'scripts\verify-release.ps1') -Stage $stage -ManifestPath (Join-Path $stage 'release-manifest.json') -SignToolPath $SignToolPath
if ($LASTEXITCODE -ne 0) { throw 'Final SignPath release verification failed.' }
& (Join-Path $root 'scripts\create-release-zip.ps1') -Stage $stage -Version $Version
if ($LASTEXITCODE -ne 0) { throw 'Final release ZIP creation failed.' }
Write-Output 'Completed verified SignPath release.'
