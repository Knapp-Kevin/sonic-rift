; Inno Setup script for the Sonic Rift Windows installer.
; Build it with build-installer.ps1, which stages the files and passes the
; defines below. The installer is small: Python, PyTorch and the models are
; downloaded by the app on first launch, as in a source checkout.

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef NumericVersion
  #define NumericVersion "0.0.0"
#endif
#ifndef StageDir
  #define StageDir "..\..\build\windows\stage"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

[Setup]
AppId={{6B0D7C3E-5A41-4F8B-9C2D-1E7A3B9F4D20}
AppName=Sonic Rift
AppVersion={#AppVersion}
AppVerName=Sonic Rift {#AppVersion}
AppPublisher=MythologIQ Labs, LLC
AppPublisherURL=https://mythologiq.studio
AppSupportURL=https://github.com/Knapp-Kevin/sonic-rift/issues
AppUpdatesURL=https://github.com/Knapp-Kevin/sonic-rift/releases
VersionInfoVersion={#NumericVersion}
VersionInfoProductName=Sonic Rift
VersionInfoCompany=MythologIQ Labs, LLC
; Per-user install: the app writes its .venv and logs next to itself.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Sonic Rift
DefaultGroupName=Sonic Rift
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
InfoAfterFile=first-launch.txt
SetupIconFile=..\..\assets\branding\sonic-rift.ico
UninstallDisplayIcon={app}\assets\branding\sonic-rift.ico
OutputDir={#OutputDir}
OutputBaseFilename=SonicRift-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
#ifdef SignToolName
SignTool={#SignToolName}
SignedUninstaller=yes
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Excludes: "\models.json"; Flags: recursesubdirs createallsubdirs ignoreversion
; The model list is the user's once they add or remove a model on the Models page, so an
; upgrade must not reset it: install it only when there is none, and keep it on uninstall.
Source: "{#StageDir}\models.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\Sonic Rift"; Filename: "{app}\launch-sonic-rift.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\assets\branding\sonic-rift.ico"
Name: "{autodesktop}\Sonic Rift"; Filename: "{app}\launch-sonic-rift.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\assets\branding\sonic-rift.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\launch-sonic-rift.cmd"; WorkingDir: "{app}"; Description: "Start Sonic Rift and finish setup now"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove what first launch generated. Generated audio and other user files stay.
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
