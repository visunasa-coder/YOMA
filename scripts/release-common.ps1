$ErrorActionPreference = 'Stop'

function Get-YomaRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-YomaPeFiles {
    param([Parameter(Mandatory)][string]$Root)

    $extensions = @('.exe', '.dll', '.pyd', '.ocx', '.sys', '.cpl', '.scr', '.efi')
    Get-ChildItem -LiteralPath $Root -Recurse -File -Force -ErrorAction Stop |
        Where-Object {
            if ($_.Extension.ToLowerInvariant() -in $extensions) { return $true }
            if ($_.Length -lt 2) { return $false }
            $stream = [System.IO.File]::OpenRead($_.FullName)
            try {
                $bytes = New-Object byte[] 2
                [void]$stream.Read($bytes, 0, 2)
                return ($bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A)
            } finally {
                $stream.Dispose()
            }
        } |
        Sort-Object FullName
}

function Get-YomaRelativePath {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Path)
    $rootUri = [Uri]((Resolve-Path -LiteralPath $Root).Path.TrimEnd('\') + '\')
    $pathUri = [Uri](Resolve-Path -LiteralPath $Path).Path
    return [Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString()).Replace('/', '\')
}

function Get-YomaSignatureInfo {
    param([Parameter(Mandatory)][string]$Path)

    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    $subject = $null
    $issuer = $null
    $thumbprint = $null
    $publicKeyAlgorithm = $null
    if ($signature.SignerCertificate) {
        $subject = $signature.SignerCertificate.Subject
        $issuer = $signature.SignerCertificate.Issuer
        $thumbprint = $signature.SignerCertificate.Thumbprint
        $publicKeyAlgorithm = $signature.SignerCertificate.PublicKey.Oid.Value
    }
    [pscustomobject]@{
        status = [string]$signature.Status
        status_message = [string]$signature.StatusMessage
        certificate_subject = $subject
        certificate_issuer = $issuer
        certificate_thumbprint = $thumbprint
        public_key_algorithm = $publicKeyAlgorithm
        timestamp_status = 'not_checked'
    }
}

function Get-YomaPeClassification {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Path
    )

    $relative = Get-YomaRelativePath -Root $Root -Path $Path
    $normalized = $relative.Replace('/', '\')
    $owned = @(
        'YOMA-ControlServer.exe',
        'YOMA-Setup-Wizard.exe',
        'YOMA-Voice-Agent.exe',
        'YOMA-Setup.exe',
        'app\YOMA-ControlServer.exe',
        'app\YOMA-Setup-Wizard.exe',
        'app\YOMA-Voice-Agent.exe',
        'installer\YOMA-Setup.exe'
    )
    $upstreamRoots = @(
        'control_internal\',
        'voice_internal\',
        'setup_internal\',
        'runtime\piper\',
        'app\control_internal\',
        'app\voice_internal\',
        'app\setup_internal\',
        'app\runtime\piper\'
    )

    if ($owned -contains $normalized) {
        return [pscustomobject]@{
            ownership = 'YOMA'
            signing_required = $true
            signing_reason = 'YOMA-authored release executable or installer'
        }
    }
    foreach ($rootPrefix in $upstreamRoots) {
        if ($normalized.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return [pscustomobject]@{
                ownership = 'UPSTREAM'
                signing_required = $false
                signing_reason = 'Upstream runtime/native dependency; included but not signed with YOMA certificate'
            }
        }
    }
    return [pscustomobject]@{
        ownership = 'UNEXPECTED'
        signing_required = $false
        signing_reason = 'Native file is outside the approved YOMA and upstream release roots'
    }
}

function Get-YomaSigningTargets {
    param([Parameter(Mandatory)][string]$Root)
    foreach ($file in Get-YomaPeFiles -Root $Root) {
        $classification = Get-YomaPeClassification -Root $Root -Path $file.FullName
        if ($classification.ownership -eq 'UNEXPECTED') {
            $relative = Get-YomaRelativePath -Root $Root -Path $file.FullName
            throw "Unexpected PE/native file in release staging: $relative"
        }
        if ($classification.signing_required) { $file }
    }
}

function New-YomaReleaseManifest {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$ManifestPath,
        [string]$Product = 'YOMA',
        [string]$Version = '0.55.0',
        [string]$Stage = 'staging'
    )

    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
    $records = @(
        foreach ($file in Get-YomaPeFiles -Root $resolvedRoot) {
            $relative = Get-YomaRelativePath -Root $resolvedRoot -Path $file.FullName
            $signature = Get-YomaSignatureInfo -Path $file.FullName
            $classification = Get-YomaPeClassification -Root $resolvedRoot -Path $file.FullName
            [pscustomobject]@{
                relative_path = $relative
                file_type = $file.Extension.TrimStart('.').ToUpperInvariant()
                ownership = $classification.ownership
                signing_required = $classification.signing_required
                signing_reason = $classification.signing_reason
                size = [int64]$file.Length
                sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                signing_status = $signature.status
                signing_status_message = $signature.status_message
                certificate_subject = $signature.certificate_subject
                certificate_issuer = $signature.certificate_issuer
                certificate_thumbprint = $signature.certificate_thumbprint
                timestamp_status = $signature.timestamp_status
            }
        }
    )

    $manifest = [ordered]@{
        schema = 'yoma.release-manifest.v1'
        product = $Product
        version = $Version
        stage = $Stage
        generated_utc = (Get-Date).ToUniversalTime().ToString('o')
        root = $resolvedRoot
        files = $records
    }
    $parent = Split-Path -Parent $ManifestPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
    return $manifest
}

function Find-YomaSignTool {
    param([string]$ConfiguredPath)
    if ($ConfiguredPath) {
        if (-not (Test-Path -LiteralPath $ConfiguredPath)) { throw "Configured SignTool was not found: $ConfiguredPath" }
        return (Resolve-Path -LiteralPath $ConfiguredPath).Path
    }
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $kits = @(
        "$env:ProgramFiles\Windows Kits\10\bin\*",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*")
    $candidate = Get-ChildItem -Path $kits -Filter signtool.exe -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
    throw 'SignTool.exe was not found. Install the Windows SDK or set YOMA_SIGNTOOL_PATH.'
}

function Find-YomaInnoCompiler {
    param([string]$ConfiguredPath)
    if ($ConfiguredPath) {
        if (-not (Test-Path -LiteralPath $ConfiguredPath)) { throw "Configured ISCC.exe was not found: $ConfiguredPath" }
        return (Resolve-Path -LiteralPath $ConfiguredPath).Path
    }
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $root = Get-YomaRoot
    $candidates = @(
        (Join-Path $root '.release-inno\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 7\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $candidate = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    throw 'ISCC.exe was not found. Install Inno Setup or set YOMA_ISCC_PATH.'
}

function Invoke-YomaSignTool {
    param([Parameter(Mandatory)][string]$SignTool, [Parameter(Mandatory)][string[]]$Arguments)
    & $SignTool @Arguments
    if ($LASTEXITCODE -ne 0) { throw "SignTool failed with exit code $LASTEXITCODE." }
}

function Assert-YomaNotTestCertificate {
    param([Parameter(Mandatory)]$Signature)
    if ($Signature.certificate_subject -eq 'CN=YOMA TEST Code Signing' -or
        $Signature.certificate_thumbprint -eq 'BD0CFAB33E8BEDCD50754C3AD6065790590532B7') {
        throw 'The YOMA TEST Code Signing certificate is prohibited for production release.'
    }
}
