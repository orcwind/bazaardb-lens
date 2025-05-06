[Setup]
AppName=Bazaar_Lens
AppVersion=1.0
DefaultDirName={pf}\\Bazaar_Lens
DefaultGroupName=Bazaar_Lens
OutputBaseFilename=Bazaar_Lens_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\Bazaar_Lens.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icons\\*"; DestDir: "{app}\\icons"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "data\\*"; DestDir: "{app}\\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "tesseract-ocr-w64-setup-5.5.0.20241111.exe"; DestDir: "{tmp}"; Flags: ignoreversion

[Icons]
Name: "{group}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"
Name: "{commondesktop}\\Bazaar_Lens"; Filename: "{app}\\Bazaar_Lens.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\\tesseract-ocr-w64-setup-5.5.0.20241111.exe"; Parameters: "/SILENT"; StatusMsg: "正在安装Tesseract-OCR..."; Flags: waituntilterminated
Filename: "{app}\\Bazaar_Lens.exe"; Description: "运行 Bazaar_Lens"; Flags: nowait postinstall skipifsilent
