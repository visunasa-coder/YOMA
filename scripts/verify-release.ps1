param(
    [string]$Stage = (Join-Path (Split-Path $PSScriptRoot -Parent) 'release\staging'),
    [string]$ManifestPath,
    [string]$SignToolPath = $env:YOMA_SIGNTOOL_PATH,
    [string]$InstalledRoot
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'release-common.ps1')

if (-not $ManifestPath) { $ManifestPath = Join-Path $Stage 'release-manifest.json' }
if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Release manifest was not found: $ManifestPath" }
$manifest = Get-Content -Raw $ManifestPath | ConvertFrom-Json
$signTool = Find-YomaSignTool -ConfiguredPath $SignToolPath
$actual = @(Get-YomaPeFiles -Root $Stage)
$expected = @($manifest.files | ForEach-Object { $_.relative_path })
$required = @(
    'app\YOMA-ControlServer.exe',
    'app\YOMA-Setup-Wizard.exe',
    'app\YOMA-Voice-Agent.exe',
    'app\runtime\piper\piper.exe',
    'installer\YOMA-Setup.exe'
)
foreach ($requiredPath in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $Stage $requiredPath))) { throw "Required release file is missing: $requiredPath" }
}
foreach ($file in Get-ChildItem -LiteralPath $Stage -Recurse -File -Force) {
    if ($file.Extension.ToLowerInvariant() -in @('.exe','.dll','.pyd','.ocx','.sys','.cpl','.scr','.efi') -and
        $file.FullName -notmatch '\\(app|installer)\\') {
        throw "Unexpected PE/native file outside approved release roots: $($file.FullName)"
    }
}

if ($actual.Count -ne $expected.Count) { throw "PE inventory mismatch: expected $($expected.Count), found $($actual.Count)." }
foreach ($file in $actual) {
    $relative = Get-YomaRelativePath -Root $Stage -Path $file.FullName
    $record = @($manifest.files | Where-Object { $_.relative_path -eq $relative }) | Select-Object -First 1
    if (-not $record) { throw "Unexpected PE/native file: $relative" }
    $classification = Get-YomaPeClassification -Root $Stage -Path $file.FullName
    if ($classification.ownership -eq 'UNEXPECTED') { throw "Unexpected PE/native file: $relative" }
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    if ($hash -ne $record.sha256) { throw "Hash mismatch after signing: $relative" }
    $signature = Get-YomaSignatureInfo -Path $file.FullName
    if ($classification.signing_required) {
        if ($signature.status -ne 'Valid') { throw "Required YOMA signature is invalid: $relative ($($signature.status_message))" }
        Assert-YomaNotTestCertificate -Signature $signature
        if ($signature.certificate_subject -eq $signature.certificate_issuer) { throw "Self-signed certificate is not allowed: $relative" }
        if ($signature.public_key_algorithm -ne '1.2.840.113549.1.1.1') { throw "Non-RSA signer is not allowed: $relative" }
        $certificate = Get-ChildItem "Cert:\CurrentUser\My\$($signature.certificate_thumbprint)" -ErrorAction SilentlyContinue
        if (-not $certificate) { $certificate = Get-ChildItem "Cert:\LocalMachine\My\$($signature.certificate_thumbprint)" -ErrorAction SilentlyContinue }
        if ($certificate -and -not $certificate.GetRSAPublicKey()) { throw "Non-RSA signer is not allowed: $relative" }
        Invoke-YomaSignTool -SignTool $signTool -Arguments @('verify','/pa','/all','/tw',$file.FullName)
        $record.timestamp_status = 'verified'
    } else {
        if ($signature.certificate_thumbprint -eq 'BD0CFAB33E8BEDCD50754C3AD6065790590532B7' -or
            $signature.certificate_subject -eq 'CN=YOMA TEST Code Signing') {
            throw "The development YOMA test certificate is not permitted anywhere in a release: $relative"
        }
        $record.timestamp_status = if ($signature.status -eq 'Valid') { 'upstream_verified' } else { 'not_required_upstream_unsigned' }
    }
}

$installer = Join-Path $Stage 'installer\YOMA-Setup.exe'
if (-not (Test-Path -LiteralPath $installer)) { throw 'Final signed installer is missing from staging.' }
$appRoot = Join-Path $Stage 'app'
if ($InstalledRoot) {
    if (-not (Test-Path -LiteralPath $InstalledRoot)) { throw "Installed root was not found: $InstalledRoot" }
    $stagedFiles = @(Get-ChildItem -LiteralPath $appRoot -Recurse -File -Force | ForEach-Object { Get-YomaRelativePath -Root $appRoot -Path $_.FullName })
    $installedFiles = @(Get-ChildItem -LiteralPath $InstalledRoot -Recurse -File -Force | ForEach-Object { Get-YomaRelativePath -Root $InstalledRoot -Path $_.FullName } | Where-Object { $_ -notmatch '^config\\' })
    if ((@($stagedFiles | Sort-Object) -join "`n") -cne (@($installedFiles | Sort-Object) -join "`n")) { throw 'Installed file set does not match release staging.' }
    foreach ($relative in $stagedFiles) {
        $stagedPath = Join-Path $appRoot $relative
        $installedPath = Join-Path $InstalledRoot $relative
        $stagedHash = (Get-FileHash -LiteralPath $stagedPath -Algorithm SHA256).Hash
        $installedHash = (Get-FileHash -LiteralPath $installedPath -Algorithm SHA256).Hash
        if ($stagedHash -ne $installedHash) { throw "Installed file hash mismatch: $relative" }
    }
}
$manifest.generated_utc = (Get-Date).ToUniversalTime().ToString('o')
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
Write-Output "Verified $($actual.Count) PE/native files and the final installer."
