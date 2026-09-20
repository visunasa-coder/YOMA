param(
    [string]$Version = '0.55.0',
    [string]$PythonExecutable,
    [switch]$SkipEnvironmentInstall,
    [switch]$PrepareSignPath
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$releaseRoot = Join-Path $root 'release'
$stage = Join-Path $releaseRoot 'staging'
$app = Join-Path $stage 'app'
$work = Join-Path $releaseRoot 'work'
$unsigned = Join-Path $releaseRoot 'unsigned'
$environment = Join-Path $root '.release-venv'

function Initialize-ReleaseEnvironment {
    if (Test-Path -LiteralPath (Join-Path $environment 'Scripts\python.exe')) { return }
    $base = $PythonExecutable
    if (-not $base) {
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            & $launcher.Source '-3.12' '-m' 'venv' $environment
            if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.12 release virtual environment.' }
            return
        }
        $baseCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($baseCommand) { $base = $baseCommand.Source }
    }
    if (-not $base -or -not (Test-Path -LiteralPath $base)) {
        throw 'Python 3.12 was not found. Install Python 3.12 or pass -PythonExecutable.'
    }
    & $base '-m' 'venv' $environment
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python release virtual environment.' }
}

function Resolve-Python {
    Initialize-ReleaseEnvironment
    $candidate = Join-Path $environment 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $candidate)) { throw "Release Python environment is missing: $candidate" }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Invoke-Python {
    param([string]$Python, [string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE." }
}

function Copy-ReleaseTree {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Source)) { throw "Required release input is missing: $Source" }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Recurse -File -Force) {
        $relative = $item.FullName.Substring((Resolve-Path $Source).Path.Length).TrimStart('\')
        $target = Join-Path $Destination $relative
        New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
        if (Test-Path -LiteralPath $target) {
            $sourceHash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
            $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            if ($sourceHash -ne $targetHash) { throw "Conflicting release files: $relative" }
        } else {
            Copy-Item -LiteralPath $item.FullName -Destination $target
        }
    }
}

foreach ($directory in @($app, $work, $unsigned)) {
    if (Test-Path -LiteralPath $directory) { Remove-Item -LiteralPath $directory -Recurse -Force }
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$python = Resolve-Python
if (-not $SkipEnvironmentInstall) {
    Invoke-Python -Python $python -Arguments @('-m','pip','install','--disable-pip-version-check','--requirement',(Join-Path $root 'requirements-release.txt'))
}
$environmentRecord = Join-Path $releaseRoot 'build-environment.txt'
$versionInfo = Join-Path $work 'yoma-version.txt'
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($($Version -replace '\.', ','),0), prodvers=($($Version -replace '\.', ','),0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'YOMA'),
        StringStruct('FileDescription', 'YOMA Office Management'),
        StringStruct('FileVersion', '$Version'),
        StringStruct('InternalName', 'YOMA'),
        StringStruct('OriginalFilename', 'YOMA'),
        StringStruct('ProductName', 'YOMA'),
        StringStruct('ProductVersion', '$Version')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -LiteralPath $versionInfo -Encoding ASCII
$recordLines = @('YOMA release build environment', "python=$((& $python --version 2>&1) -join ' ')", 'packages=')
$recordLines += @(& $python -m pip freeze 2>&1)
$recordLines | Set-Content -LiteralPath $environmentRecord -Encoding UTF8

Push-Location $root
try {
    foreach ($spec in @('YOMA-ControlServer.spec','YOMA-Voice-Agent.spec','YOMA-Setup-Wizard.spec')) {
        Invoke-Python -Python $python -Arguments @('-m','PyInstaller','--clean','--noconfirm','--distpath',$unsigned,'--workpath',$work,$spec)
    }

    Copy-ReleaseTree -Source (Join-Path $unsigned 'YOMA-ControlServer') -Destination $app
    Copy-ReleaseTree -Source (Join-Path $unsigned 'YOMA-Voice-Agent') -Destination $app
    Copy-ReleaseTree -Source (Join-Path $unsigned 'YOMA-Setup-Wizard') -Destination $app
    Copy-ReleaseTree -Source (Join-Path $root 'runtime\piper') -Destination (Join-Path $app 'runtime\piper')
    Copy-ReleaseTree -Source (Join-Path $root 'models') -Destination (Join-Path $app 'models')
    New-Item -ItemType Directory -Path (Join-Path $app 'installer') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $root 'installer\install_service.ps1') -Destination (Join-Path $app 'installer\install_service.ps1')
    Copy-Item -LiteralPath (Join-Path $root 'installer\uninstall_service.ps1') -Destination (Join-Path $app 'installer\uninstall_service.ps1')
    Copy-Item -LiteralPath (Join-Path $root 'installer\Open-YOMA.ps1') -Destination (Join-Path $app 'installer\Open-YOMA.ps1')

    . (Join-Path $root 'scripts\release-common.ps1')
    New-YomaReleaseManifest -Root $app -ManifestPath (Join-Path $releaseRoot 'app-unsigned-manifest.json') -Version $Version -Stage 'unsigned' | Out-Null
    if ($PrepareSignPath) {
        $signPathInput = Join-Path $releaseRoot 'signpath-input\yoma-owned'
        if (Test-Path -LiteralPath (Split-Path $signPathInput -Parent)) {
            Remove-Item -LiteralPath (Split-Path $signPathInput -Parent) -Recurse -Force
        }
        New-Item -ItemType Directory -Path $signPathInput -Force | Out-Null
        foreach ($name in @('YOMA-ControlServer.exe','YOMA-Setup-Wizard.exe','YOMA-Voice-Agent.exe')) {
            Copy-Item -LiteralPath (Join-Path $app $name) -Destination (Join-Path $signPathInput $name)
        }
        Copy-Item -LiteralPath (Join-Path $releaseRoot 'app-unsigned-manifest.json') -Destination (Join-Path $releaseRoot 'signpath-input\app-unsigned-manifest.json')
        Write-Output "Prepared unsigned SignPath input: $signPathInput"
        return
    }
    & (Join-Path $root 'scripts\sign-release.ps1') -Stage $app -ManifestPath (Join-Path $releaseRoot 'app-signing-manifest.json')
    if ($LASTEXITCODE -ne 0) { throw 'Application signing failed.' }

    $isccPath = Find-YomaInnoCompiler -ConfiguredPath $env:YOMA_ISCC_PATH
    & $isccPath "/DAppVersion=$Version" (Join-Path $root 'installer\YOMA.iss')
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }

    $installer = Join-Path $stage 'installer\YOMA-Setup.exe'
    if (-not (Test-Path -LiteralPath $installer)) { throw "Inno Setup did not produce $installer" }
    & (Join-Path $root 'scripts\sign-release.ps1') -Stage (Split-Path $installer -Parent) -ManifestPath (Join-Path $stage 'installer-signing-manifest.json')
    if ($LASTEXITCODE -ne 0) { throw 'Installer signing failed.' }

    Copy-Item -LiteralPath (Join-Path $root 'docs\RELEASE_WINDOWS.md') -Destination (Join-Path $stage 'RELEASE_WINDOWS.md')
    Copy-Item -LiteralPath $environmentRecord -Destination (Join-Path $stage 'build-environment.txt')
    New-YomaReleaseManifest -Root $stage -ManifestPath (Join-Path $stage 'release-manifest.json') -Version $Version -Stage 'final' | Out-Null
    & (Join-Path $root 'scripts\verify-release.ps1') -Stage $stage -ManifestPath (Join-Path $stage 'release-manifest.json')
    if ($LASTEXITCODE -ne 0) { throw 'Final release verification failed.' }
    & (Join-Path $root 'scripts\create-release-zip.ps1') -Stage $stage -Version $Version
    if ($LASTEXITCODE -ne 0) { throw 'Final release ZIP creation failed.' }
} finally {
    Pop-Location
}
