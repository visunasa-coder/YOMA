param(
    [string]$InstallDir="$env:ProgramFiles\YOMA"
)

$voice = Join-Path $InstallDir "YOMA-Voice-Agent.exe"

if(Test-Path $voice){
    Start-Process $voice -ArgumentList "--status" -WindowStyle Hidden
}
