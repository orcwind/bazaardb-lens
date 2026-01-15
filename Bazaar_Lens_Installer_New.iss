[Setup]
AppName=Bazaar Lens
AppId={{BazaarLensAppId-1234-5678-90AB-CDEF12345678}}
#define MyAppVersion "1.0.2"
AppVersion={#MyAppVersion}
AppPublisher=Tempo Storm Tools
AppPublisherURL=https://space.bilibili.com/35110142
DefaultDirName={pf}\Bazaar_Lens
DefaultGroupName=Bazaar Lens
OutputBaseFilename=Bazaar_Lens_Installer_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
; 安装前检查并关闭运行中的程序
RestartIfNeededByRun=no
AllowNoIcons=yes
CloseApplications=yes
RestartApplications=no
; 需要管理员权限
PrivilegesRequired=admin
; 安装程序图标
SetupIconFile=Bazaar_Lens.ico
; 安装程序窗口标题
WizardImageFile=
WizardSmallImageFile=
; 卸载信息
UninstallDisplayIcon={app}\Bazaar_Lens.exe

[Code]
var
  HelpPage: TWizardPage;
  HelpMemo: TMemo;

// 获取默认的帮助文本（作为备用）- 必须在 LoadHelpText 之前定义
function GetDefaultHelpText(): String;
begin
  Result := 'Bazaar Lens 1.0.2 使用说明' + #13#10 + #13#10;
  Result := Result + '   - 功能： 大巴扎游戏中按住 Ctrl 键可以查看鼠标指向位置的怪物或事件信息;' + #13#10;
  Result := Result + '   - 如果未显示或未识别，请多尝试几次。' + #13#10 + #13#10;
  Result := Result + '   - 暂时只支持中文版本！！！' + #13#10 + #13#10;
  Result := Result + ' 📞 支持与反馈' + #13#10;
  Result := Result + '   如有Bug或其他问题，请联系：bazaarlens@gmail.com' + #13#10;
  Result := Result + '   或前往B站主页留言：https://space.bilibili.com/35110142' + #13#10;
  Result := Result + '   欢迎提交反馈，帮助我们改进！' + #13#10 + #13#10;
  Result := Result + '   🔍 同时推荐一下个人做的流放之路工具网站：poe2lens' + #13#10;
  Result := Result + '   ✨ 提供实时物价、倒货计算、宝石利润、Boss收益等一站式数据工具' + #13#10;
  Result := Result + '   ⚡️ 免费使用，帮助你在POE1/POE2每个赛季高效赚取通货。' + #13#10;
  Result := Result + '   👉 地址：https://poe2lens.com' + #13#10 + #13#10 + #13#10;
  Result := Result + '更新历史：' + #13#10;
  Result := Result + 'v1.0.2 [2026-1-15]' + #13#10;
  Result := Result + '-增加支持中文，显示中文' + #13#10;
  Result := Result + '-取消支持英文，不显示英文' + #13#10 + #13#10;
  Result := Result + 'v1.0.1 [2025-10-13]' + #13#10;
  Result := Result + '-更新所有怪物，事件信息' + #13#10 + #13#10;
  Result := Result + 'v1.0.0 [2025-5-11]' + #13#10;
  Result := Result + '-发布';
end;

// 读取 Help.txt 文件内容
function LoadHelpText(): String;
var
  HelpFilePath: String;
  HelpLines: TArrayOfString;
  I: Integer;
  ScriptDir: String;
  TempPath: String;
begin
  Result := '';
  
  // 方法1: 尝试从安装程序所在目录读取（编译后的安装程序运行时）
  ScriptDir := ExtractFilePath(ExpandConstant('{srcexe}'));
  HelpFilePath := ScriptDir + 'Help.txt';
  
  // 方法2: 如果方法1失败，尝试使用 {src} 常量（安装程序所在目录）
  if not FileExists(HelpFilePath) then
  begin
    HelpFilePath := ExpandConstant('{src}\Help.txt');
  end;
  
  // 方法3: 如果方法2也失败，尝试当前工作目录
  if not FileExists(HelpFilePath) then
  begin
    HelpFilePath := ExtractFilePath(ExpandConstant('{srcexe}')) + 'Help.txt';
  end;
  
  // 如果找到文件，读取内容
  if FileExists(HelpFilePath) then
  begin
    try
      if LoadStringsFromFile(HelpFilePath, HelpLines) then
      begin
        for I := 0 to GetArrayLength(HelpLines) - 1 do
        begin
          Result := Result + HelpLines[I] + #13#10;
        end;
      end
      else
      begin
        // 如果 LoadStringsFromFile 失败，尝试使用备用内容
        Result := GetDefaultHelpText();
      end;
    except
      Result := GetDefaultHelpText();
    end;
  end
  else
  begin
    // 如果文件不存在，使用嵌入的默认内容
    Result := GetDefaultHelpText();
  end;
end;

// 创建帮助说明页面
procedure CreateHelpPage;
begin
  // 在欢迎页面之后创建帮助页面
  HelpPage := CreateCustomPage(wpWelcome, 
    '使用说明', 
    '请仔细阅读以下使用说明');
    
  // 创建 Memo 控件显示帮助内容
  HelpMemo := TMemo.Create(HelpPage);
  HelpMemo.Parent := HelpPage.Surface;
  HelpMemo.Left := 0;
  HelpMemo.Top := 0;
  HelpMemo.Width := HelpPage.SurfaceWidth;
  HelpMemo.Height := ScaleY(350);
  HelpMemo.ReadOnly := True;
  HelpMemo.ScrollBars := ssVertical;
  HelpMemo.Font.Size := 9;
  HelpMemo.Font.Name := 'Microsoft YaHei';
  
  // 加载并显示 Help.txt 内容
  HelpMemo.Text := LoadHelpText();
end;

// 比较版本号
// 返回值: -1 表示 version1 < version2, 0 表示相等, 1 表示 version1 > version2
function CompareVersions(version1, version2: String): Integer;
var
  v1Major, v1Minor, v1Patch: Integer;
  v2Major, v2Minor, v2Patch: Integer;
  Pos1, Pos2: Integer;
  TempStr: String;
begin
  Result := 0;
  
  // 解析版本号 (格式: "1.0.2")
  // 解析 version1
  TempStr := version1;
  Pos1 := Pos('.', TempStr);
  if Pos1 > 0 then
  begin
    v1Major := StrToIntDef(Copy(TempStr, 1, Pos1 - 1), 0);
    Delete(TempStr, 1, Pos1);
    Pos1 := Pos('.', TempStr);
    if Pos1 > 0 then
    begin
      v1Minor := StrToIntDef(Copy(TempStr, 1, Pos1 - 1), 0);
      Delete(TempStr, 1, Pos1);
      v1Patch := StrToIntDef(TempStr, 0);
    end
    else
    begin
      v1Minor := StrToIntDef(TempStr, 0);
      v1Patch := 0;
    end;
  end
  else
  begin
    v1Major := StrToIntDef(TempStr, 0);
    v1Minor := 0;
    v1Patch := 0;
  end;
  
  // 解析 version2
  TempStr := version2;
  Pos2 := Pos('.', TempStr);
  if Pos2 > 0 then
  begin
    v2Major := StrToIntDef(Copy(TempStr, 1, Pos2 - 1), 0);
    Delete(TempStr, 1, Pos2);
    Pos2 := Pos('.', TempStr);
    if Pos2 > 0 then
    begin
      v2Minor := StrToIntDef(Copy(TempStr, 1, Pos2 - 1), 0);
      Delete(TempStr, 1, Pos2);
      v2Patch := StrToIntDef(TempStr, 0);
    end
    else
    begin
      v2Minor := StrToIntDef(TempStr, 0);
      v2Patch := 0;
    end;
  end
  else
  begin
    v2Major := StrToIntDef(TempStr, 0);
    v2Minor := 0;
    v2Patch := 0;
  end;
  
  // 比较版本号
  if v1Major < v2Major then
    Result := -1
  else if v1Major > v2Major then
    Result := 1
  else if v1Minor < v2Minor then
    Result := -1
  else if v1Minor > v2Minor then
    Result := 1
  else if v1Patch < v2Patch then
    Result := -1
  else if v1Patch > v2Patch then
    Result := 1;
end;

// 检测并卸载旧版本（只卸载小于等于当前版本的版本）
function UninstallOldVersion(): Boolean;
var
  UninstallKey: String;
  UninstallString: String;
  InstalledVersion: String;
  CurrentVersion: String;
  ResultCode: Integer;
  PosIndex: Integer;
  VersionCompare: Integer;
  SearchDirs: array[0..3] of String;
  DirToCheck: String;
  FindRec: TFindRec;
  FoundUninstaller: Boolean;
  i: Integer;
begin
  Result := False;
  CurrentVersion := '{#MyAppVersion}'; // 当前安装的版本
  
  // 检查注册表中的卸载信息
  // HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Bazaar Lens
  UninstallKey := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Bazaar Lens';
  
  // 尝试从注册表读取已安装的版本号
  if RegQueryStringValue(HKLM, UninstallKey, 'DisplayVersion', InstalledVersion) then
  begin
    Log('检测到已安装版本: ' + InstalledVersion + ', 当前安装版本: ' + CurrentVersion);
    
    // 比较版本号
    VersionCompare := CompareVersions(InstalledVersion, CurrentVersion);
    
    if VersionCompare > 0 then
    begin
      // 已安装的版本大于当前版本，提示用户
      if MsgBox('检测到已安装的版本 ' + InstalledVersion + ' 高于当前安装版本 ' + CurrentVersion + '。' + #13#10 + 
                '是否继续安装旧版本？', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end
    else if VersionCompare <= 0 then
    begin
      // 已安装的版本小于等于当前版本，需要卸载
      Log('已安装版本 ' + InstalledVersion + ' 小于等于当前版本 ' + CurrentVersion + '，将卸载旧版本');
    end;
  end;
  
  // 尝试从注册表读取卸载命令
  if RegQueryStringValue(HKLM, UninstallKey, 'UninstallString', UninstallString) then
  begin
    // 找到卸载程序路径
    // 卸载字符串格式通常是: "C:\Program Files\Inno Setup\unins000.exe" /SILENT
    // 我们需要提取路径部分
    PosIndex := Pos('"', UninstallString);
    if PosIndex > 0 then
    begin
      // 提取引号内的路径
      Delete(UninstallString, 1, PosIndex);
      PosIndex := Pos('"', UninstallString);
      if PosIndex > 0 then
        Delete(UninstallString, PosIndex, Length(UninstallString));
    end
    else
    begin
      // 如果没有引号，尝试提取到第一个空格
      PosIndex := Pos(' ', UninstallString);
      if PosIndex > 0 then
        UninstallString := Copy(UninstallString, 1, PosIndex - 1);
    end;
    
    // 检查卸载程序是否存在
    if FileExists(UninstallString) then
    begin
      // 再次检查版本（如果之前没有读取到版本号，这里默认卸载）
      if InstalledVersion = '' then
      begin
        Log('检测到已安装版本，但无法读取版本号，将尝试卸载');
      end;
      
      Log('开始卸载旧版本: ' + UninstallString);
      
      // 先关闭运行中的程序
      Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Exec('timeout', '/t 1 /nobreak', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
      // 运行卸载程序（静默模式）
      // /SILENT 表示静默卸载，不显示界面
      // /VERYSILENT 表示完全静默，不显示任何界面
      if Exec(UninstallString, '/VERYSILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        // 等待卸载完成
        Sleep(2000);
        Log('旧版本卸载完成');
        Result := True;
      end
      else
      begin
        Log('卸载旧版本失败，错误代码: ' + IntToStr(ResultCode));
      end;
    end
    else
    begin
      Log('卸载程序不存在: ' + UninstallString);
    end;
  end
  else
  begin
  // 如果注册表中没有找到，跳过目录搜索（避免在不同 Windows 环境中出现兼容性问题）
  begin
    Log('未在注册表中找到卸载信息；跳过目录遍历，继续安装。');
  end;
  end;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // 先尝试卸载旧版本
  UninstallOldVersion();
  
  // 再次确保关闭运行中的程序
  Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('timeout', '/t 1 /nobreak', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  Result := True;
end;

procedure InitializeWizard;
begin
  // 创建帮助说明页面
  CreateHelpPage;
end;

// 在安装完成后设置快捷方式为"以管理员身份运行"
procedure CurStepChanged(CurStep: TSetupStep);
var
  ShortcutPath: String;
  PowerShellScript: String;
  ResultCode: Integer;
  TempFile: String;
  VbsPath: String;
  VbsContent: String;
  PsPath: String;
  PsContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 等待一下，确保快捷方式已经创建
    Sleep(500);
    
    // 生成一个简单的 VBScript 启动器，用于以管理员权限启动主程序
    VbsPath := ExpandConstant('{app}\run_elevated.vbs');
    VbsContent := 'Set sh = CreateObject("Shell.Application")' + #13#10 +
                  'sh.ShellExecute "' + ExpandConstant('{app}\Bazaar_Lens.exe') + '", "", "' + ExpandConstant('{app}') + '", "runas", 1' + #13#10;
    if SaveStringToFile(VbsPath, VbsContent, False) then
    begin
      Log('已生成以管理员启动的 VBScript 启动器: ' + VbsPath);
    end
    else
    begin
      Log('生成 VBScript 启动器失败: ' + VbsPath);
    end;

    // 创建开始菜单与桌面快捷方式已交由 [Icons] 节创建（指向 run_elevated.vbs）
    Log('开始菜单/桌面快捷方式将由 [Icons] 节创建，目标: ' + VbsPath);
  end;
    
    // 生成并运行 PowerShell 脚本，使用 Windows DPAPI (ProtectedData) 保护 data_key.bin
    if FileExists(ExpandConstant('{app}\data_key.bin')) then
    begin
      Log('尝试使用 PowerShell + DPAPI 保护 data_key.bin');
      PsPath := ExpandConstant('{app}\protect_key.ps1');
      PsContent := 
        '$in = "' + ExpandConstant('{app}\data_key.bin') + '"' + #13#10 +
        '$out = "' + ExpandConstant('{app}\data_key_prot.bin') + '"' + #13#10 +
        '$b = [System.IO.File]::ReadAllBytes($in)' + #13#10 +
        '$prot = [System.Security.Cryptography.ProtectedData]::Protect($b, $null, [System.Security.Cryptography.DataProtectionScope]::LocalMachine)' + #13#10 +
        '[System.IO.File]::WriteAllBytes($out, $prot)' + #13#10;

      if SaveStringToFile(PsPath, PsContent, False) then
      begin
        Log('已生成 PowerShell 脚本: ' + PsPath);
        if Exec('powershell', '-NoProfile -ExecutionPolicy Bypass -File "' + PsPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
        begin
          Log('PowerShell 执行成功，已生成受保护 key: ' + ExpandConstant('{app}\data_key_prot.bin'));
          // 设置受保护 key 文件为隐藏且只读
          Exec('attrib', '+h +r "' + ExpandConstant('{app}\data_key_prot.bin') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
          // 删除未保护的 key
          if DeleteFile(ExpandConstant('{app}\data_key.bin')) then
            Log('已删除未保护的 key (data_key.bin)')
          else
            Log('删除未保护 key 失败，可能需要手动删除: ' + ExpandConstant('{app}\data_key.bin'));
        end
        else
        begin
          Log('PowerShell 执行失败，未能生成受保护 key，请检查系统是否允许执行 PowerShell 脚本');
        end;
      end
      else
      begin
        Log('生成 PowerShell 脚本失败: ' + PsPath);
      end;
    end
    else
    begin
      Log('未找到 data_key.bin，跳过保护步骤');
    end;
end;

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"

[Files]
; 主程序（从根目录，因为 build.py 输出到根目录）
Source: "Bazaar_Lens.exe"; DestDir: "{app}"; Flags: ignoreversion
; 图标文件
Source: "Bazaar_Lens.ico"; DestDir: "{app}"; Flags: ignoreversion
; 帮助文档
Source: "Help.txt"; DestDir: "{app}"; Flags: ignoreversion
; 加密后的 JSON 数据包（将替代明文 JSON）
Source: "data_json.enc"; DestDir: "{app}"; Flags: ignoreversion
; 打包时产生的未保护 key（安装器应在安装过程中保护或替换）
Source: "data_key.bin"; DestDir: "{app}"; Flags: ignoreversion
; 图标文件（包括所有子目录）
Source: "data\icon\*"; DestDir: "{app}\data\icon"; Flags: ignoreversion recursesubdirs createallsubdirs
; Tesseract-OCR（整个目录，不包含在 exe 中）
Source: "Tesseract-OCR\*"; DestDir: "{app}\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 快捷方式改为指向 run_elevated.vbs（以管理员权限启动主程序）
Name: "{group}\Bazaar Lens"; Filename: "{app}\run_elevated.vbs"; IconFilename: "{app}\Bazaar_Lens.ico"
Name: "{commondesktop}\Bazaar Lens"; Filename: "{app}\run_elevated.vbs"; IconFilename: "{app}\Bazaar_Lens.ico"; Tasks: desktopicon

[Run]
; 安装完成后选项
Filename: "{app}\Bazaar_Lens.exe"; Description: "启动 Bazaar Lens"; Flags: postinstall nowait skipifsilent
Filename: "{app}\Help.txt"; Description: "查看帮助文档"; Flags: postinstall shellexec skipifsilent unchecked

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM Bazaar_Lens.exe /T"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\data_json.enc"
Type: files; Name: "{app}\data_key.bin"
Type: files; Name: "{app}\data_key_prot.bin"
Type: files; Name: "{app}\*.png"
Type: dirifempty; Name: "{app}"

[Messages]
WelcomeLabel1=欢迎使用 Bazaar Lens 安装向导
WelcomeLabel2=此向导将引导您完成 Bazaar Lens 的安装过程。%n%n建议：%n- 以管理员身份运行安装程序%n- 安装完成后，程序会出现在系统托盘中%n- 右键点击托盘图标可以访问程序功能
