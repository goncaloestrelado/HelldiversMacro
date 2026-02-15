; Inno Setup Script for Helldivers Numpad Macros
; https://jrsoftware.org/isinfo.php

#define MyAppName "Helldivers Numpad Macros"
#define MyAppVersion "0.1.7"
#define MyAppPublisher "Goncalo Estrelado"
#define MyAppURL "https://github.com/goncaloestrelado/HelldiversMacro"
#define MyAppExeName "HelldiversNumpadMacros.exe"
#define MyAppIconFile "assets\icon.ico"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{8F2A3D4E-5B6C-7D8E-9F0A-1B2C3D4E5F6A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=dist\installer
OutputBaseFilename=HelldiversNumpadMacros-Setup-beta{#MyAppVersion}
SetupIconFile={#MyAppIconFile}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Run at Windows startup"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
; Main executable (from dist folder created by PyInstaller)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Include all assets if they're bundled separately (uncomment if assets aren't embedded in EXE)
; Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Additional files
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
; Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create profiles directory with user permissions
Name: "{app}\profiles"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// Check if app is running and close it before installation
function InitializeSetup(): Boolean;
var
  AppRunning: Boolean;
begin
  Result := True;
  AppRunning := True;
  
  // Check if the app is running
  while AppRunning and (FindWindowByWindowName('Helldivers 2 - Numpad Commander') <> 0) do
  begin
    if MsgBox('Helldivers Numpad Macros is currently running. Please close it to continue installation.' + #13#10 + #13#10 + 
              'Click OK after closing the application, or Cancel to exit setup.', 
              mbConfirmation, MB_OKCANCEL) = IDOK then
    begin
      // Give user time to close
      Sleep(1000);
    end
    else
    begin
      Result := False;
      AppRunning := False;
    end;
  end;
end;

// Preserve user profiles during installation
procedure CurStepChanged(CurStep: TSetupStep);
var
  ProfilesDir: String;
  GeneralSettingsFile: String;
begin
  if CurStep = ssInstall then
  begin
    ProfilesDir := ExpandConstant('{app}\profiles');
    GeneralSettingsFile := ExpandConstant('{app}\general.json');
    
    // Backup profiles if they exist
    if DirExists(ProfilesDir) then
    begin
      RenameFile(ProfilesDir, ProfilesDir + '.backup');
    end;
    
    // Backup settings if exists
    if FileExists(GeneralSettingsFile) then
    begin
      RenameFile(GeneralSettingsFile, GeneralSettingsFile + '.backup');
    end;
  end;
  
  if CurStep = ssPostInstall then
  begin
    ProfilesDir := ExpandConstant('{app}\profiles');
    GeneralSettingsFile := ExpandConstant('{app}\general.json');
    
    // Restore profiles if backup exists
    if DirExists(ProfilesDir + '.backup') then
    begin
      if DirExists(ProfilesDir) then
        DelTree(ProfilesDir, True, True, True);
      RenameFile(ProfilesDir + '.backup', ProfilesDir);
    end;
    
    // Restore settings if backup exists
    if FileExists(GeneralSettingsFile + '.backup') then
    begin
      if FileExists(GeneralSettingsFile) then
        DeleteFile(GeneralSettingsFile);
      RenameFile(GeneralSettingsFile + '.backup', GeneralSettingsFile);
    end;
  end;
end;
