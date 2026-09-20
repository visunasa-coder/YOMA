param(
    [Parameter(Mandatory)][string]$SignedOwnedRoot,
    [string]$Version = '0.55.0',
    [string]$SignToolPath = $env:YOMA_SIGNTOOL_PATH,
    [string]$InnoSetupPath = $env:YOMA_ISCC_PATH
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'release-common.ps1')
$stage = Join-Path $root 'release\staging'
$app = Join-Path $stage 'app'
$installerDir = Join-Path $stage 'installer'
if (-not (Test-Path -LiteralPath $SignedOwnedRoot)) { throw "Signed SignPath executable directory was not found: $SignedOwnedRoot" }
if (-not (Test-Path -LiteralPath $app)) { throw "Unsigned application staging was not found: $app" }

$signTool = Find-YomaSignTool -ConfiguredPath $SignToolPath
foreach ($name in @('YOMA-ControlServer.exe','YOMA-Setup-Wizard.exe','YOMA-Voice-Agent.exe')) {
    $source = Join-Path $SignedOwnedRoot $name
    if (-not (Test-Path -LiteralPath $source)) { throw "SignPath did not return required signed executable: $name" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $app $name) -Force
    $signature = Get-YomaSignatureInfo -Path (Join-Path $app $name)
    if ($signature.status -ne 'Valid') { throw "Returned SignPath executable is not validly signed: $name" }
    Assert-YomaNotTestCertificate -Signature $signature
    Invoke-YomaSignTool -SignTool $signTool -Arguments @('verify','/pa','/all','/tw',(Join-Path $app $name))
}

New-YomaReleaseManifest -Root $app -ManifestPath (Join-Path $root 'release\signpath-signed-app-manifest.json') -Version $Version -Stage 'signpath-signed-app' | Out-Null
New-Item -ItemType Directory -Path $installerDir -Force | Out-Null
$iscc = Find-YomaInnoCompiler -ConfiguredPath $InnoSetupPath
& $iscc "/DAppVersion=$Version" (Join-Path $root 'installer\YOMA.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }
$installer = Join-Path $installerDir 'YOMA-Setup.exe'
if (-not (Test-Path -LiteralPath $installer)) { throw "Inno Setup did not produce $installer" }

$installerInput = Join-Path $root 'release\signpath-installer-input'
if (Test-Path -LiteralPath $installerInput) { Remove-Item -LiteralPath $installerInput -Recurse -Force }
New-Item -ItemType Directory -Path $installerInput -Force | Out-Null
Copy-Item -LiteralPath $installer -Destination (Join-Path $installerInput 'YOMA-Setup.exe')
Write-Output "Prepared unsigned SignPath installer input: $installerInput"
