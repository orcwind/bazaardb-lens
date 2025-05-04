import os
import shutil
import subprocess

def build_exe():
    # 清理旧的构建文件
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # 创建spec文件内容
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['bazaar_helper.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Tesseract-OCR', 'Tesseract-OCR'),  # 包含Tesseract-OCR
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
    name='TheBazaarHelper',
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
    icon='icon.ico',  # 添加图标
    uac_admin=True,  # 请求管理员权限
)
'''
    
    # 写入spec文件
    with open('bazaar_helper.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # 运行PyInstaller
    subprocess.run(['pyinstaller', 'bazaar_helper.spec', '--clean'])
    
    print("构建完成！")
    print("可执行文件位于: dist/TheBazaarHelper.exe")

if __name__ == "__main__":
    build_exe() 