[Setup]
AppName=Bazaar_Lens
AppVersion=1.0
DefaultDirName={pf}\\Bazaar_Lens
DefaultGroupName=Bazaar_Lens
OutputBaseFilename=Bazaar_Lens_Installer
Compression=lzma
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "创建桌面图标"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "dist\\Bazaar_Lens.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icons\\*"; DestDir: "{app}\\icons"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "data\\*"; DestDir: "{app}\\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "tesseract-ocr-w64-setup-5.5.0.20241111.exe"; DestDir: "{tmp}"; Flags: ignoreversion
Source: "Bazaar_Lens.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"
Name: "{commondesktop}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\\tesseract-ocr-w64-setup-5.5.0.20241111.exe"; Parameters: "/SILENT"; StatusMsg: "正在安装Tesseract-OCR..."; Flags: waituntilterminated

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM Bazaar_Lens.exe /T"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\\bazaar_helper.log"
Type: files; Name: "{app}\\debug_binary.png"
Type: files; Name: "{app}\\debug_capture.png"
Type: files; Name: "{app}\\*.log"
Type: files; Name: "{app}\\*.png"
Type: filesandordirs; Name: "{app}\\icons"
Type: filesandordirs; Name: "{app}\\data"
Type: dirifempty; Name: "{app}"
