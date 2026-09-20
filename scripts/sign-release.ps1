param(
    [string]$Stage = (Join-Path (Split-Path $PSScriptRoot -Parent) 'release\staging\app'),
    [string]$ManifestPath,
    [string]$SignToolPath = $env:YOMA_SIGNTOOL_PATH,
    [string]$CertificateThumbprint = $env:YOMA_PRODUCTION_SIGNING_THUMBPRINT,
    [string]$TimestampUrl = $env:YOMA_RFC3161_TIMESTAMP_URL
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'release-common.ps1')

if (-not $ManifestPath) { $ManifestPath = Join-Path $Stage 'release-manifest.json' }
if (-not (Test-Path -LiteralPath $Stage)) { throw "Release staging directory was not found: $Stage" }
if (-not $CertificateThumbprint) { throw 'Production signing is required. Set YOMA_PRODUCTION_SIGNING_THUMBPRINT.' }
if (-not $TimestampUrl) { throw 'RFC3161 timestamping is required. Set YOMA_RFC3161_TIMESTAMP_URL.' }

$signTool = Find-YomaSignTool -ConfiguredPath $SignToolPath
$normalizedThumbprint = $CertificateThumbprint.Replace(' ', '')
$certificate = Get-ChildItem "Cert:\CurrentUser\My\$normalizedThumbprint" -ErrorAction SilentlyContinue
if (-not $certificate) { $certificate = Get-ChildItem "Cert:\LocalMachine\My\$normalizedThumbprint" -ErrorAction SilentlyContinue }
if (-not $certificate) { throw "Production signing certificate was not found in the certificate stores: $CertificateThumbprint" }
if (-not $certificate.HasPrivateKey) { throw 'The production signing certificate has no accessible private key.' }
if ($certificate.Subject -eq 'CN=YOMA TEST Code Signing' -or $certificate.Thumbprint -eq 'BD0CFAB33E8BEDCD50754C3AD6065790590532B7') {
    throw 'The YOMA TEST Code Signing certificate is prohibited for production release.'
}
if ($certificate.Subject -eq $certificate.Issuer) { throw 'A self-signed certificate is prohibited for production release.' }
if (-not $certificate.GetRSAPublicKey()) { throw 'The production certificate must have an RSA public key.' }
$manifest = if (Test-Path -LiteralPath $ManifestPath) { Get-Content -Raw $ManifestPath | ConvertFrom-Json } else { New-YomaReleaseManifest -Root $Stage -ManifestPath $ManifestPath }
$files = @(Get-YomaSigningTargets -Root $Stage)
if (-not $files) { throw 'No PE/native files were found in release staging.' }

foreach ($file in $files) {
    $beforeHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    Invoke-YomaSignTool -SignTool $signTool -Arguments @('sign','/fd','SHA256','/td','SHA256','/tr',$TimestampUrl,'/sha1',$CertificateThumbprint,$file.FullName)
    $signature = Get-YomaSignatureInfo -Path $file.FullName
    if ($signature.status -ne 'Valid') { throw "Signature verification failed for $($file.FullName): $($signature.status_message)" }
    Assert-YomaNotTestCertificate -Signature $signature
    Invoke-YomaSignTool -SignTool $signTool -Arguments @('verify','/pa','/all','/tw',$file.FullName)
    $afterHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    Write-Output "$($file.FullName): signed; pre-sign hash $beforeHash; final hash $afterHash"
}

New-YomaReleaseManifest -Root $Stage -ManifestPath $ManifestPath -Stage 'signed' | Out-Null
