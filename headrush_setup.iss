; Script generated for HeadRush NAM Studio Pro
; Professional Windows Installer via Inno Setup 6

#define MyAppName "HeadRush NAM Studio Pro"
#define MyAppVersion "1.3.4"
#define MyAppPublisher "Tiago Soares"
#define MyAppURL "https://github.com/tiagojsoares/headrush-nam-studio"
#define MyAppExeName "HeadRush_NAM_Studio_Pro.exe"

#ifndef SourceExePath
  #define SourceExePath "C:\VM\HeadRush_NAM_Studio_Pro.exe"
#endif
#ifndef OutputDir
  #define OutputDir "C:\VM"
#endif

[Setup]
AppId={{E8D79A22-3C4B-4E89-9A82-D08B48B925C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=HeadRush_NAM_Studio_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=commandline dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=1.3.4.0
VersionInfoCompany=Tiago Soares
VersionInfoDescription=HeadRush NAM Studio Pro Installer
VersionInfoProductVersion=1.3.4.0

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceExePath}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
