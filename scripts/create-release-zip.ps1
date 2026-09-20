param(
    [string]$Stage = (Join-Path (Split-Path $PSScriptRoot -Parent) 'release\staging'),
    [string]$OutputDirectory = (Join-Path (Split-Path $PSScriptRoot -Parent) 'release\zip'),
    [string]$Version = '0.55.0'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'release-common.ps1')

$verify = Join-Path $PSScriptRoot 'verify-release.ps1'
& $verify -Stage $Stage
if ($LASTEXITCODE -ne 0) { throw 'Release verification failed; ZIP was not created.' }

$installer = Join-Path $Stage 'installer\YOMA-Setup.exe'
$manifest = Join-Path $Stage 'release-manifest.json'
$checksum = Join-Path $Stage 'SHA256SUMS.txt'
$environmentRecord = Join-Path $Stage 'build-environment.txt'
if (-not (Test-Path -LiteralPath $installer)) { throw 'Final installer is missing.' }
if (-not (Test-Path -LiteralPath $manifest)) { throw 'Final manifest is missing.' }
$hashInputs = @($installer, $manifest, $environmentRecord) + @(Get-ChildItem -LiteralPath $Stage -Filter '*.md' -File | Select-Object -ExpandProperty FullName)
$hashInputs | Sort-Object | ForEach-Object {
    $name = Split-Path $_ -Leaf
    "$((Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash)  $name"
} | Set-Content -LiteralPath $checksum -Encoding ASCII

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$zip = Join-Path $OutputDirectory "YOMA-$Version-Windows-x64.zip"
if (Test-Path -LiteralPath $zip) { throw "Refusing to overwrite an existing release ZIP: $zip" }
$include = @($installer, $manifest, $checksum, $environmentRecord)
$docs = Get-ChildItem -LiteralPath $Stage -Filter '*.md' -File -ErrorAction SilentlyContinue
$include += @($docs.FullName)
$entryNames = @{
    $installer = 'YOMA-Setup.exe'
    $manifest = 'release-manifest.json'
    $checksum = 'SHA256SUMS.txt'
    $environmentRecord = 'build-environment.txt'
}
foreach ($doc in $docs) { $entryNames[$doc.FullName] = $doc.Name }

Add-Type -AssemblyName System.IO.Compression
$zipStream = [System.IO.File]::Open($zip, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try {
    $archive = [System.IO.Compression.ZipArchive]::new($zipStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        $fixedTime = [DateTimeOffset]::new([DateTime]::SpecifyKind([DateTime]::new(2020, 1, 1), [DateTimeKind]::Utc))
        foreach ($path in ($include | Sort-Object)) {
            $entry = $archive.CreateEntry($entryNames[$path], [System.IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $fixedTime
            $input = [System.IO.File]::OpenRead($path)
            $output = $entry.Open()
            try { $input.CopyTo($output) } finally { $output.Dispose(); $input.Dispose() }
        }
    } finally { $archive.Dispose() }
} finally { $zipStream.Dispose() }
Write-Output "Created $zip"
