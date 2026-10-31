#define MyAppName "Atelpix Secure Client Dashboard"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Atelpix"
#define MyAppExeName "Atelpix Secure Dashboard.exe"
[Setup]
AppId={{C5A8A2D9-19C6-4A25-A7D0-8A7E20261031}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Atelpix Secure Client Dashboard
DefaultGroupName=Atelpix Secure Client Dashboard
OutputDir=installer-output
OutputBaseFilename=Atelpix-Secure-Client-Dashboard-Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
[Files]
Source: "dist\Atelpix Secure Dashboard.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Atelpix Owner Dashboard"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Atelpix Team Viewer"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--team"
Name: "{autodesktop}\Atelpix Owner Dashboard"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\Atelpix Team Viewer"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--team"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Additional shortcuts:"
[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=Atelpix-LAN-HTTPS"; Flags: runhidden waituntilterminated
[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=Atelpix-LAN-HTTPS dir=in action=allow protocol=TCP localport=8765 profile=private"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Atelpix Owner Dashboard"; Flags: postinstall nowait skipifsilent
