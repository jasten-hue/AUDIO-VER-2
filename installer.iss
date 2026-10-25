#define AppName "Audio Test Log Analyzer"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{B7D2A1C4-5E3F-4A6B-9C8D-1F2E3A4B5C6D}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\AudioTestLogAnalyzer
DefaultGroupName={#AppName}
OutputDir=installer_output
OutputBaseFilename=AudioTestLogAnalyzer-Setup
SetupIconFile=app.ico
UninstallDisplayIcon={app}\AudioTestLogAnalyzer.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\AudioTestLogAnalyzer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\AudioTestLogAnalyzer.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\AudioTestLogAnalyzer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Run]
Filename: "{app}\AudioTestLogAnalyzer.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
