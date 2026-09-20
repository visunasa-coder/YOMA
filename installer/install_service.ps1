param(
 [string]$InstallDir="$env:ProgramFiles\YOMA"
)

$ErrorActionPreference="Stop"

$service="YomaControlServer"
$exe=Join-Path $InstallDir "YOMA-ControlServer.exe"

if(-not(Test-Path $exe)){
 throw "Missing $exe"
}

$s=Get-Service $service -ErrorAction SilentlyContinue

if($s){
 if($s.Status -ne "Stopped"){
  Stop-Service $service -Force -ErrorAction SilentlyContinue
  Start-Sleep 2
 }
 sc.exe delete $service | Out-Null
 Start-Sleep 2
}

New-Service `
 -Name $service `
 -DisplayName "YOMA Control Server" `
 -Description "YOMA Enterprise AI Workplace Control Server" `
 -BinaryPathName "`"$exe`"" `
 -StartupType Automatic | Out-Null

Start-Service $service
