; 键盘 → 虚拟手柄 映射工具 —— Inno Setup 6 安装脚本
;
; 由 build.py 调用 ISCC.exe 编译（推荐），也可用 Inno Setup IDE 直接编译。
;
; 构建参数（程序名/版本/源目录）由 build.py 写入 build_defines.iss（UTF-8 BOM），
; 本脚本存在该文件时自动引入；直接用 IDE 编译时使用下面的内置默认值。

#if FileExists(AddBackslash(SourcePath) + "build_defines.iss")
  #include "build_defines.iss"
#endif

#ifndef AppName
  #define AppName "键盘 → 虚拟手柄 映射工具"
#endif
#ifndef AppVersion
  #define AppVersion "0.1.1.1"
#endif
#ifndef AppPublisher
  #define AppPublisher "KbdToPad Project"
#endif
#ifndef ExeName
  #define ExeName "KbdToPad.exe"
#endif
#ifndef DistSource
  #define DistSource "..\dist\KbdToPad\*"
#endif

#define VendorDir AddBackslash(SourcePath) + "vendor"
#define ViGEmBusFile AddBackslash(SourcePath) + "vendor\ViGEmBusSetup.exe"
#define VCRedistFile AddBackslash(SourcePath) + "vendor\VC_redist.x64.exe"
#define ChineseISLFile AddBackslash(SourcePath) + "vendor\ChineseSimplified.isl"

[Setup]
AppId={{8E2C1F3A-6C4B-4C7E-9B7E-2E7F0C6B3A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\KbdToPad
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=KbdToPad-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName}
AppMutex=Local\KbdToPad_SingleInstance
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(ChineseISLFile)
Name: "chinesesimplified"; MessagesFile: "{#ChineseISLFile}"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "开机自动启动（最小化到系统托盘并自动开始监听）"; GroupDescription: "附加选项："; Flags: unchecked

[Files]
; 主程序（文件夹版：{DistSource}\*；单文件版：直接指向 exe）
Source: {#DistSource}; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if FileExists(ViGEmBusFile)
Source: "{#ViGEmBusFile}"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedViGEmBus
#endif
#if FileExists(VCRedistFile)
Source: "{#VCRedistFile}"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedVCRedist
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon
Name: "{commonstartup}\KbdToPad"; Filename: "{app}\{#ExeName}"; Parameters: "--tray --listen"; Tasks: autostart

[Run]
Filename: "{tmp}\ViGEmBusSetup.exe"; Parameters: "/quiet /norestart"; StatusMsg: "正在安装 ViGEmBus 虚拟手柄驱动（约 1 分钟）..."; Flags: waituntilterminated; Check: ShouldInstallViGEmBus
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "正在安装 Microsoft Visual C++ 运行库..."; Flags: waituntilterminated; Check: ShouldInstallVCRedist
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\config.json"

[Code]
const
  ViGEmBusService = 'SYSTEM\CurrentControlSet\Services\ViGEmBus';
  VCRedistKey = 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';

function IsViGEmBusInstalled: Boolean;
begin
  Result := RegKeyExists(HKLM, ViGEmBusService);
end;

function IsVCRedistInstalled: Boolean;
begin
  Result := RegKeyExists(HKLM64, VCRedistKey);
end;

function NeedViGEmBus: Boolean;
begin
  Result := not IsViGEmBusInstalled;
end;

function NeedVCRedist: Boolean;
begin
  Result := not IsVCRedistInstalled;
end;

function ShouldInstallViGEmBus: Boolean;
begin
  Result := NeedViGEmBus and FileExists(ExpandConstant('{tmp}\ViGEmBusSetup.exe'));
end;

function ShouldInstallVCRedist: Boolean;
begin
  Result := NeedVCRedist and FileExists(ExpandConstant('{tmp}\VC_redist.x64.exe'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if NeedViGEmBus and not FileExists(ExpandConstant('{tmp}\ViGEmBusSetup.exe')) then
    MsgBox('未随包附带 ViGEmBus 驱动安装包，请安装完成后手动安装驱动，否则程序无法创建虚拟手柄：'
      + #13#10 + #13#10
      + 'https://github.com/nefarius/ViGEmBus/releases', mbInformation, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    // 结束正在运行的程序，避免文件占用导致卸载失败
    Exec('taskkill.exe', '/im {#ExeName} /f', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end
  else if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\KbdToPad');
    if DirExists(DataDir) then
      if MsgBox('是否同时删除配置与日志？' + #13#10 + DataDir,
        mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
