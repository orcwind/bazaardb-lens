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
'''
    
    # 写入spec文件
    with open('Bazaar_Lens.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("\n打包内容清单：")
    print("1. 主程序文件：")
    print("   - Bazaar_Lens.py")
    print("\n2. 资源文件：")
    print("   - icons/（所有游戏图标）")
    print("   - data/（怪物和事件数据）")
    print("   - Info.txt（使用说明）")
    print("   - Bazaar_Lens.ico（程序图标）")
    print("\n3. 依赖程序：")
    print("   - tesseract-ocr-w64-setup-5.5.0.20241111.exe")
    print("\n4. Python依赖库：")
    print("   - win32api, win32gui, win32con")
    print("   - keyboard")
    print("   - PIL (Pillow)")
    print("   - opencv-python (cv2)")
    print("   - numpy")
    print("   - pytesseract")
    print("   - requests")
    print("   - pystray")
    print("   - psutil")
    
    # 运行PyInstaller
    subprocess.run(['pyinstaller', 'Bazaar_Lens.spec', '--clean'])
    
    print("\n构建完成！")
    print("可执行文件位于: dist/Bazaar_Lens.exe")

if __name__ == "__main__":
    build_exe() 