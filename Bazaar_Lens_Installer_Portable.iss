[Setup]
AppName=Bazaar_Lens
#define MyAppVersion "1.0.1"
AppVersion={#MyAppVersion}
DefaultDirName={pf}\Bazaar_Lens
DefaultGroupName=Bazaar_Lens
OutputBaseFilename=Bazaar_Lens_Installer_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
; 安装前检查并关闭运行中的程序
RestartIfNeededByRun=no
; 允许覆盖安装
AllowNoIcons=yes
; 强制关闭正在使用的文件，不询问用户
CloseApplications=yes

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // 安装前强制关闭 Bazaar_Lens.exe
  Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('timeout', '/t 1 /nobreak', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM Bazaar_Lens.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

[Tasks]
Name: "desktopicon"; Description: "创建桌面图标"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "dist\\Bazaar_Lens.exe"; DestDir: "{app}"; Flags: ignoreversion
; 不再需要单独的 icons 和 data 目录，所有数据都在 6.0 目录中
; 怪物数据和图标
Source: "6.0\\crawlers\\monster_details_v3\\monsters_v3.json"; DestDir: "{app}\\6.0\\crawlers\\monster_details_v3"; Flags: ignoreversion
Source: "6.0\\crawlers\\monster_details_v3\\icons\\*.webp"; DestDir: "{app}\\6.0\\crawlers\\monster_details_v3\\icons"; Flags: ignoreversion
; 事件数据和图标（包含子目录）
Source: "6.0\\crawlers\\event_details_final\\events_final.json"; DestDir: "{app}\\6.0\\crawlers\\event_details_final"; Flags: ignoreversion
Source: "6.0\\crawlers\\event_details_final\\icons\\*"; DestDir: "{app}\\6.0\\crawlers\\event_details_final\\icons"; Flags: ignoreversion recursesubdirs createallsubdirs
; Tesseract-OCR 便携版（直接打包到应用目录，无需单独安装）
; 注意：需要先将 Tesseract 安装目录（如 C:\Program Files\Tesseract-OCR）复制到项目根目录下的 Tesseract-OCR 文件夹
; 当前使用版本：Tesseract 5.5.0（包含 chi_sim, eng, osd 语言包）
Source: "Tesseract-OCR\\*"; DestDir: "{app}\\Tesseract-OCR"; Flags: ignoreversion recursesubdirs createallsubdirs
; 程序图标和帮助文档
Source: "Bazaar_Lens.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "Help.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "Help.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "How to Install.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "How to Install.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"
Name: "{commondesktop}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"; Tasks: desktopicon

[Run]
; 安装前强制关闭运行中的程序（不询问，直接终止）
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM Bazaar_Lens.exe /T 2>nul & timeout /t 1 /nobreak >nul & taskkill /F /IM Bazaar_Lens.exe /T 2>nul"; StatusMsg: "正在强制关闭运行中的程序..."; Flags: runhidden waituntilterminated

; 安装完成后选项
Filename: "{app}\Help.txt"; Description: "查看帮助文档 (View Help Document)"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\Bazaar_Lens.exe"; Description: "启动 Bazaar_Lens (Launch Bazaar_Lens)"; Flags: postinstall skipifsilent nowait

[Messages]
WelcomeLabel2=此安装程序会将 Bazaar_Lens 和 Tesseract OCR 一起安装到您选择的目录。所有文件都在一个目录下，无需单独安装 Tesseract。%n%nThis installer will install both Bazaar_Lens and Tesseract OCR together in the directory you choose. All files are in one directory, no need to install Tesseract separately.

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM Bazaar_Lens.exe /T"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\\bazaar_lens.log"
Type: files; Name: "{app}\\bazaar_lens_config.json"
Type: files; Name: "{app}\\debug_binary.png"
Type: files; Name: "{app}\\debug_capture.png"
Type: files; Name: "{app}\\debug_capture_fixed.png"
Type: files; Name: "{app}\\*.log"
Type: files; Name: "{app}\\*.png"
Type: filesandordirs; Name: "{app}\\6.0"
Type: filesandordirs; Name: "{app}\\Tesseract-OCR"
Type: dirifempty; Name: "{app}"

[Code]
var
  InstructionsPage: TWizardPage;
  InstructionsMemo: TMemo;  // 使用简单的Memo控件代替RichEdit

// 创建安装说明页面
procedure CreateInstructionsPage;
begin
  // 创建说明页面
  InstructionsPage := CreateCustomPage(wpWelcome, 
    '安装说明 (Installation Instructions)', 
    '请仔细阅读以下安装说明 (Please read the installation instructions carefully)');
    
  // 使用Memo控件，支持滚动
  InstructionsMemo := TMemo.Create(InstructionsPage);
  InstructionsMemo.Parent := InstructionsPage.Surface;
  InstructionsMemo.Left := 0;
  InstructionsMemo.Top := 0;
  InstructionsMemo.Width := InstructionsPage.SurfaceWidth;
  InstructionsMemo.Height := ScaleY(300);  // 增加高度
  InstructionsMemo.ReadOnly := True;
  InstructionsMemo.ScrollBars := ssVertical;
  InstructionsMemo.Font.Size := 9;  // 设置字体大小
  
  // 设置纯文本内容
  InstructionsMemo.Lines.Add('重要安装说明 (Important Installation Instructions):');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('1. 此安装程序包含 Bazaar_Lens 和 Tesseract OCR，所有文件将安装到同一目录');
  InstructionsMemo.Lines.Add('   This installer includes both Bazaar_Lens and Tesseract OCR, all files will be installed to the same directory.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('2. 无需单独安装 Tesseract OCR，所有依赖已包含在安装包中');
  InstructionsMemo.Lines.Add('   No need to install Tesseract OCR separately, all dependencies are included in the installer.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('3. 安装完成后，可以通过系统托盘图标访问程序功能');
  InstructionsMemo.Lines.Add('   After installation, you can access program functions through the system tray icon.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('4. 如果OCR功能无法正常工作，请通过系统托盘图标菜单中的"Set tesseract-ocr.exe Path"选项重新设置OCR路径');
  InstructionsMemo.Lines.Add('   If the OCR function does not work properly, please reset the OCR path through the "Set tesseract-ocr.exe Path" option in the system tray icon menu.');
end;

procedure InitializeWizard;
begin
  // 创建指示页面
  CreateInstructionsPage;
  
  // 调整安装向导的大小
  WizardForm.Width := ScaleX(600);  // 增加宽度
  WizardForm.Height := ScaleY(500); // 增加高度
end;

