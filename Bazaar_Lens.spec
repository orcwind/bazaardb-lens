
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Bazaar_Lens.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('tesseract-ocr-w64-setup-5.5.0.20241111.exe', '.'),  # Tesseract-OCR安装程序
        ('icons', 'icons'),  # icons文件夹
        ('data', 'data'),    # 数据文件夹
        ('Info.txt', '.'),   # 说明文件
        ('Bazaar_Lens.ico', '.'),  # 程序图标
    ],
    hiddenimports=['win32api', 'win32gui', 'win32con', 'keyboard'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Bazaar_Lens',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Bazaar_Lens.ico',
    uac_admin=True,
)
