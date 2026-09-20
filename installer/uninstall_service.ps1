param(
    [string]$InstallDir = "$env:ProgramFiles\YOMA"
)

$ErrorActionPreference = 'Stop'
$service = 'YomaControlServer'
$existing = Get-Service $service -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -ne 'Stopped') {
        Stop-Service $service -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    sc.exe delete $service | Out-Null
}
