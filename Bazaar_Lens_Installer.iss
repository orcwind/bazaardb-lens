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
RestartApplications=no

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
; OCR依赖
Source: "tesseract-ocr-w64-setup-5.5.0.20241111.exe"; DestDir: "{tmp}"; Flags: ignoreversion
Source: "eng.traineddata"; DestDir: "{tmp}"; Flags: ignoreversion
Source: "osd.traineddata"; DestDir: "{tmp}"; Flags: ignoreversion
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

; 安装Tesseract-OCR
Filename: "{tmp}\tesseract-ocr-w64-setup-5.5.0.20241111.exe"; Parameters: "/SILENT /DIR=""C:\Program Files\Tesseract-OCR"""; StatusMsg: "正在安装Tesseract-OCR..."; Flags: waituntilterminated

; 确保tessdata目录存在
Filename: "{cmd}"; Parameters: "/C IF NOT EXIST ""C:\Program Files\Tesseract-OCR\tessdata"" mkdir ""C:\Program Files\Tesseract-OCR\tessdata"""; StatusMsg: "正在创建OCR数据目录..."; Flags: runhidden

; 复制英文语言文件到正确位置
Filename: "{cmd}"; Parameters: "/C copy ""{tmp}\eng.traineddata"" ""C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata"" /Y"; StatusMsg: "正在安装OCR英文语言文件..."; Flags: runhidden

; 复制osd语言文件到正确位置
Filename: "{cmd}"; Parameters: "/C copy ""{tmp}\osd.traineddata"" ""C:\Program Files\Tesseract-OCR\tessdata\osd.traineddata"" /Y"; StatusMsg: "正在安装OCR方向检测语言文件..."; Flags: runhidden

; 安装完成后选项
Filename: "{app}\Help.txt"; Description: "查看帮助文档 (View Help Document)"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\Bazaar_Lens.exe"; Description: "启动 Bazaar_Lens (Launch Bazaar_Lens)"; Flags: postinstall skipifsilent nowait

[Messages]
WelcomeLabel2=此过程会安装两个程序，首先是Bazaar_Lens, 主程序用于显示信息，可安装在任何位置。 接下来会安装tesseract-ocr程序，用于识别文字，建议安装在默认目录。如果非默认目录，需要您后续在选项中重新选择安装目录。%n%nThis process will install two programs. First, Bazaar_Lens, the main program for displaying information, which can be installed in any location. Next, the tesseract-ocr program will be installed, which is used for text recognition. It is recommended to install it in the default directory. If you choose a non-default directory, you will need to select the installation directory again in the options later.

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
  InstructionsMemo.Lines.Add('1. 安装过程中会首先安装Bazaar_Lens主程序');
  InstructionsMemo.Lines.Add('   The main Bazaar_Lens program will be installed first.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('2. 然后会自动安装Tesseract-OCR文字识别程序');
  InstructionsMemo.Lines.Add('   The Tesseract-OCR text recognition program will then be installed automatically.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('3. 强烈建议将Tesseract-OCR安装在默认位置: C:\Program Files\Tesseract-OCR');
  InstructionsMemo.Lines.Add('   It is strongly recommended to install Tesseract-OCR in the default location: C:\Program Files\Tesseract-OCR');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('4. 如果您选择其他安装位置，请记住安装路径，之后需要在程序设置中手动指定OCR路径');
  InstructionsMemo.Lines.Add('   If you choose a different installation location, please remember the path as you will need to manually specify the OCR path in the program settings later.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('5. 安装过程中若出现"Downloading eng language file"或"Downloading osd language file"或"Connecting..."提示，如果很慢，可以点击"Cancel"取消下载，不影响使用');
  InstructionsMemo.Lines.Add('   During installation, if you see "Downloading eng language file" or "Downloading osd language file" or "Connecting..." and it is slow, you can click "Cancel" to skip the download. This will not affect functionality.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('6. 不用担心取消下载，我们已经准备了离线语言包，会在后续步骤中自动安装');
  InstructionsMemo.Lines.Add('   Don''t worry about canceling the download. We have prepared an offline language pack that will be automatically installed in later steps.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('7. 安装完成后，可以通过系统托盘图标访问程序功能');
  InstructionsMemo.Lines.Add('   After installation, you can access program functions through the system tray icon.');
  InstructionsMemo.Lines.Add('');
  InstructionsMemo.Lines.Add('8. 如果OCR功能无法正常工作，请通过系统托盘图标菜单中的"Set tesseract-ocr.exe Path"选项重新设置OCR路径');
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
