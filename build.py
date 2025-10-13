import PyInstaller.__main__
import os
import sys

print("="*60)
print("开始打包 Bazaar_Lens...")
print("="*60)

# 检查必须文件是否存在
required_files = [
    'Bazaar_Lens.py',
    'Bazaar_Lens.ico',
    '6.0/crawlers/monster_details_v3/monsters_v3.json',
    '6.0/crawlers/event_details_final/events_final.json'
]

print("\n检查必须文件...")
missing_files = []
for file in required_files:
    if os.path.exists(file):
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - 文件不存在！")
        missing_files.append(file)

if missing_files:
    print("\n错误：以下文件缺失，无法打包：")
    for file in missing_files:
        print(f"  - {file}")
    sys.exit(1)

# 检查图标目录
print("\n检查图标目录...")
icon_dirs = [
    '6.0/crawlers/monster_details_v3/icons',
    '6.0/crawlers/event_details_final/icons'
]

for icon_dir in icon_dirs:
    if os.path.exists(icon_dir):
        # 统计文件数量
        count = 0
        for root, dirs, files in os.walk(icon_dir):
            count += len([f for f in files if f.endswith('.webp')])
        print(f"  ✓ {icon_dir} - {count} 个图标文件")
    else:
        print(f"  ✗ {icon_dir} - 目录不存在！")
        sys.exit(1)

print("\n开始PyInstaller打包...")
print("-"*60)

# PyInstaller参数
args = [
    'Bazaar_Lens.py',
    '--onefile',
    '--windowed',
    '--icon=Bazaar_Lens.ico',
    '--name=Bazaar_Lens',
    # 添加怪物数据文件
    '--add-data=6.0/crawlers/monster_details_v3/monsters_v3.json;6.0/crawlers/monster_details_v3',
    # 添加怪物图标目录
    '--add-data=6.0/crawlers/monster_details_v3/icons;6.0/crawlers/monster_details_v3/icons',
    # 添加事件数据文件
    '--add-data=6.0/crawlers/event_details_final/events_final.json;6.0/crawlers/event_details_final',
    # 添加事件图标目录（包含子目录）
    '--add-data=6.0/crawlers/event_details_final/icons;6.0/crawlers/event_details_final/icons',
    # 隐藏导入（避免打包时遗漏）
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=pytesseract',
    '--hidden-import=pystray',
    '--hidden-import=psutil',
    # 清理之前的构建
    '--clean',
]

print("PyInstaller 参数:")
for arg in args:
    print(f"  {arg}")
print()

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*60)
    print("打包完成！")
    print("="*60)
    print("\n输出文件位置:")
    print(f"  dist/Bazaar_Lens.exe")
    print("\n提示:")
    print("  1. 请检查 dist 目录中的 Bazaar_Lens.exe")
    print("  2. 使用 Inno Setup 创建安装程序")
    print("  3. 测试安装程序是否正常工作")
    print()
except Exception as e:
    print("\n" + "="*60)
    print("打包失败！")
    print("="*60)
    print(f"\n错误信息: {e}")
    sys.exit(1)
