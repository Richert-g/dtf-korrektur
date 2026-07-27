; Inno Setup Skript für den DTF-Korrektur-Installer.
; Erzeugt aus dem PyInstaller-Onedir-Build (dist\DTF-Korrektur) ein echtes
; Setup.exe mit Startmenü-Verknüpfung, optionalem Desktop-Icon und Uninstaller.
;
; Wird von scripts\build_windows.ps1 automatisch aufgerufen, sofern Inno Setup
; (ISCC.exe) installiert ist. Manuell kompilierbar mit:
;   ISCC.exe scripts\installer.iss /DMyAppVersion=1.0.0

#define MyAppName "DTF Korrektur"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "DTF Korrektur"
#define MyAppExeName "DTF-Korrektur.exe"

[Setup]
; Feste GUID (nicht ändern) - wird von Windows zur Update-/Deinstallations-Erkennung genutzt.
AppId={{2224C571-C75E-4CD2-B43C-A54D2E627662}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=DTF-Korrektur-Setup
SetupIconFile=..\resources\icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Bild ausschließlich lokal ausgeliefert, keine Internetverbindung nötig
DisableWelcomePage=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\DTF-Korrektur\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Kommandozeilen-/Automatisierungsmodus (siehe README, Abschnitt
; "Kommandozeilen-/Automatisierungsmodus") - bewusst in einem eigenen
; Unterordner "cli" statt direkt in {app}, da es sich um einen komplett
; separaten PyInstaller-Onedir-Build mit eigenem _internal-Ordner handelt
; (kein Qt, siehe scripts\build_windows.ps1) - eine Vermischung der beiden
; _internal-Ordner würde zu DLL-Konflikten führen. Optional: wird
; übersprungen, falls der CLI-Build fehlgeschlagen ist (siehe dortiges
; "skipifsourcedoesntexist").
Source: "..\dist\DTF-Korrektur-CLI\*"; DestDir: "{app}\cli"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Räumt lokale Konfiguration/Cache/Logs beim Deinstallieren NICHT automatisch weg
; (Profile/Einstellungen des Benutzers unter %LOCALAPPDATA%\DTFKorrektur bleiben
; bewusst erhalten, falls die App später erneut installiert wird).
