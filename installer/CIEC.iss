#define MyAppName "CIEC"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Projeto CIEC"
#define MyAppExeName "CIEC.exe"

; Ajuste o caminho do seu projeto:
#define ProjectDir "D:\Projetos\CIEC"

[Setup]
AppId={{B1A1C2D3-E4F5-46A7-8B90-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
OutputDir={#ProjectDir}\installer\output
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
SetupIconFile={#ProjectDir}\assets\images\ciec.ico
WizardStyle=modern

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; EXE do PyInstaller
Source: "{#ProjectDir}\dist\CIEC.exe"; DestDir: "{app}"; Flags: ignoreversion

; Assets (inclui manual, imagens, etc.)
Source: "{#ProjectDir}\assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs createallsubdirs ignoreversion

; (Opcional) arquivos extras, se existirem:
; Source: "{#ProjectDir}\VERSION.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Ajuda (Manual)"; Filename: "{app}\assets\docs\manual.pdf"; Flags: shellexec
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Opcional: apagar logs/config do usuário (se você salvar em {app} ou {localappdata})
Type: filesandordirs; Name: "{app}\logs"