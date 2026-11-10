; Script de instalador profissional para Inno Setup 6
; Sistema: Automação FGTS Digital

#define MyAppName "Automação FGTS Digital"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Alcides Diógenes"
#define MyAppURL "https://github.com/AlcidesDiogenes/automacao-fgts-digital"
#define MyAppExeName "FGTS_Digital.exe"
#define MyAppDebugExeName "FGTS_Digital_Console.exe"

[Setup]
AppId={{D37E8C12-58A2-4D91-8FB9-11C8407B692A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\FGTS Digital
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=FGTS_Digital_Instalador_v1.0.0
SetupIconFile=..\assets\icon.ico
WizardImageFile=..\assets\wizard_welcome.bmp
WizardSmallImageFile=..\assets\wizard_header.bmp
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=auto

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\FGTS_Digital\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: Arquivos de saída e dados gerados durante o uso ficam na pasta de dados do usuário

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{#MyAppName} (Modo Console - Diagnóstico)"; Filename: "{app}\{#MyAppDebugExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
