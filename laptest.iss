; Inno Setup Script for LapTest

#define VersionFileHandle FileOpen(AddBackslash(SourcePath) + "VERSION")
#define AppVersion Trim(FileRead(VersionFileHandle))
#expr FileClose(VersionFileHandle)
#undef VersionFileHandle

[Setup]
AppId={{A3F82C1D-5B7E-4D92-8F4A-C6E910B3D27F}
AppName=LapTest
AppVersion={#AppVersion}
AppPublisher=debeski
AppPublisherURL=https://github.com/debeski
DefaultDirName={autopf}\LapTest
DefaultGroupName=LapTest
UninstallDisplayIcon={app}\LapTest.exe
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=LapTest-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AppMutex=LapTest_SingleInstance_v1
CloseApplications=yes
RestartApplications=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic";  MessagesFile: "compiler:Languages\Arabic.isl"
Name: "french";  MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\LapTest\LapTest.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\LapTest\*";           DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md";                DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md";             DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\LapTest";           Filename: "{app}\LapTest.exe"
Name: "{group}\Uninstall LapTest"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LapTest";     Filename: "{app}\LapTest.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LapTest.exe"; Description: "{cm:LaunchProgram,LapTest}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}"
