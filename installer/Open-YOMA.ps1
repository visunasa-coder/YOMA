param(
 [string]$Url="http://127.0.0.1:8766/"
)

$s=Get-Service "YomaControlServer" -ErrorAction SilentlyContinue

if(-not $s){
 throw "YomaControlServer not installed."
}

if($s.Status -ne "Running"){
 Start-Service "YomaControlServer"
 Start-Sleep 3
}

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if($chrome){ Start-Process $chrome -ArgumentList $Url } else { Start-Process $Url }
