#define AppName "YOMA"
#define AppVersion "0.55.0"

[Setup]
AppId={{55AA2026-YOMA-4C21-A55A-000000000001}}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\YOMA
DefaultGroupName=YOMA
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\release\staging\installer
OutputBaseFilename=YOMA-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop YomaControlServer', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
 end;

[Files]
Source: "..\release\staging\app\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "config\\*"

[InstallDelete]
Type: files; Name: "{app}\*.exe"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\installer"
Type: filesandordirs; Name: "{app}\src"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YOMA Voice Agent"; ValueData: """{app}\YOMA-Voice-Agent.exe"" --status"; Flags: uninsdeletevalue

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -File ""{app}\installer\install_service.ps1"" -InstallDir ""{app}"""; Flags: runhidden waituntilterminated
Filename: "{app}\YOMA-Voice-Agent.exe"; Flags: runhidden
Filename: "{app}\YOMA-Setup-Wizard.exe"; Description: "Launch YOMA Setup"; Flags: postinstall nowait
Filename: "http://127.0.0.1:8766/"; Flags: shellexec nowait

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -File ""{app}\installer\uninstall_service.ps1"" -InstallDir ""{app}"""; Flags: runhidden waituntilterminated
