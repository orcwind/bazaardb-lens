import PyInstaller.__main__
import os
import sys
import subprocess

print("="*60)
print("开始打包 Bazaar_Lens...")
print("="*60)

# 检查必须文件是否存在（使用正确的路径）
required_files = [
    'main_script/Bazaar_Lens.py',  # 主脚本在 main_script 目录
    'Bazaar_Lens.ico',  # 图标在根目录
    'data/Json/monsters_detail.json',  # 怪物数据
    'data/Json/items.json',  # 物品数据
    'data/Json/items_db.json',  # 物品UUID映射
    'data/Json/skills.json',  # 技能数据
    'data/Json/events_from_html.json',  # 事件数据
    'Help.txt',  # 帮助文档
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

# 检查图标目录（使用正确的路径）
print("\n检查图标目录...")
icon_dirs = [
    'data/icon/monster',
    'data/icon/event',
    'data/icon/item',
    'data/icon/skill'
]

total_icons = 0
for icon_dir in icon_dirs:
    if os.path.exists(icon_dir):
        # 统计文件数量（包括子目录）
        count = 0
        for root, dirs, files in os.walk(icon_dir):
            count += len([f for f in files if f.endswith('.webp')])
        total_icons += count
        print(f"  ✓ {icon_dir} - {count} 个图标文件")
    else:
        print(f"  ✗ {icon_dir} - 目录不存在！")
        sys.exit(1)

print(f"\n  总计: {total_icons} 个图标文件")

# 清理之前的构建文件
print("\n清理之前的构建文件...")
import shutil

# 删除 build 目录和根目录下的旧 exe 文件
if os.path.exists('build'):
    try:
        shutil.rmtree('build')
        print(f"  ✓ 已删除 build 目录")
    except Exception as e:
        print(f"  ⚠ 删除 build 目录失败: {e}")

# 删除根目录下的旧 exe 文件（强制覆盖）
exe_name = 'Bazaar_Lens.exe'
if os.path.exists(exe_name):
    try:
        # 尝试删除旧文件
        os.remove(exe_name)
        print(f"  ✓ 已删除旧的 {exe_name}")
    except PermissionError:
        print(f"  ✗ 无法删除旧的 {exe_name}：文件正在被使用")
        print(f"     请先关闭正在运行的 Bazaar_Lens.exe，然后重新运行打包脚本")
        sys.exit(1)
    except Exception as e:
        print(f"  ⚠ 删除旧的 {exe_name} 失败: {e}")
        print(f"     如果文件正在运行，请先关闭程序")
        # 不退出，让 PyInstaller 尝试覆盖（如果可能）

print("\n开始PyInstaller打包...")
print("-"*60)

# 在打包前生成加密包（data_json.enc），用于将 JSON 数据打包为单个加密文件
print("\n准备生成加密数据包 data_json.enc ...")
encrypt_script = os.path.join(os.getcwd(), 'tools', 'encrypt_data.py')
if os.path.exists(encrypt_script):
    try:
        res = subprocess.run([sys.executable, encrypt_script], check=True)
        print("✓ data_json.enc 生成完成")
    except subprocess.CalledProcessError as e:
        print(f"✗ 生成 data_json.enc 失败: {e}")
        print("打包终止")
        sys.exit(1)
else:
    print("⚠ 未找到 encrypt_data 脚本，跳过加密打包步骤（确保你已手动准备 data_json.enc）")

# PyInstaller参数
args = [
    'main_script/Bazaar_Lens.py',  # 使用正确的主脚本路径
    '--icon=Bazaar_Lens.ico',
    '--name=Bazaar_Lens',
    '--distpath=.',  # 输出到项目根目录
    '--workpath=build',  # 临时文件放在 build 目录
    # 添加数据文件到打包（Windows使用分号分隔）
    '--add-data=Bazaar_Lens.ico;.',  # 托盘图标文件，放在打包后根目录
    '--add-data=data_json.enc;.',  # 将加密后的 JSON 数据包打包到根目录
    '--add-data=data_key.bin;.',   # 未保护的 key（安装器应在安装时替换为受保护的 key）
    '--add-data=data/icon;data/icon',  # 图标文件（包括所有子目录）
    '--add-data=Help.txt;.',  # 帮助文档
    # 隐藏导入（避免打包时遗漏）
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=PIL.Image',
    '--hidden-import=PIL.ImageDraw',
    '--hidden-import=pytesseract',
    '--hidden-import=pystray',
    '--hidden-import=pystray._win32',  # Windows 平台必需的 pystray 后端
    '--hidden-import=pystray.backends._win32',  # Windows 后端实现
    '--hidden-import=psutil',
    # 排除不必要的库（减小体积）
    '--exclude-module=matplotlib',
    '--exclude-module=scipy', 
    '--exclude-module=pandas',
    '--exclude-module=sklearn',
    '--exclude-module=tensorflow',
    '--exclude-module=torch',
    '--exclude-module=IPython',
    '--exclude-module=jupyter',
    '--exclude-module=notebook',
    '--exclude-module=seaborn',
    '--exclude-module=plotly',
    '--exclude-module=bokeh',
    '--exclude-module=dash',
    '--exclude-module=flask',
    '--exclude-module=django',
    '--exclude-module=sqlalchemy',
    '--exclude-module=sqlite3',
    '--exclude-module=test',
    '--exclude-module=unittest',
    '--exclude-module=pytest',
    # 优化选项
    '--strip',  # 去除调试信息
    '--onefile',  # 单文件模式
    '--windowed',  # 无控制台窗口
    # 清理之前的构建
    '--clean',
]

print("PyInstaller 参数:")
for arg in args:
    print(f"  {arg}")
print()

def use_pyarmor_pack(pyarmor_cmd, extra_options):
    """尝试使用 pyarmor pack 调用（会同时做 obfuscate + pyinstaller）"""
    cmd = [pyarmor_cmd, 'pack', '-e', extra_options, 'main_script/Bazaar_Lens.py']
    print("调用 pyarmor 打包（obfuscate + PyInstaller）：")
    print(" ".join(cmd))
    res = subprocess.run(cmd)
    return res.returncode == 0

try:
    # 优先尝试使用 pyarmor（如果在 PATH 中可用）进行一键加密并打包
    pyarmor_exe = shutil.which('pyarmor')
    if pyarmor_exe:
        print("检测到 pyarmor，可使用 pyarmor 对脚本加密后打包。")
        # 准备传递给 pyarmor pack 的 PyInstaller 选项（除脚本本身）
        extra_opts = " ".join([a for a in args[1:]])
        success = use_pyarmor_pack(pyarmor_exe, extra_opts)
        if success:
            print("\n" + "="*60)
            print("pyarmor 打包完成！输出文件应在项目根目录")
            print("="*60)
            sys.exit(0)
        else:
            print("pyarmor 打包失败，回退到直接使用 PyInstaller。")

    # 如果没有 pyarmor 或 pyarmor pack 失败，直接使用 PyInstaller
    PyInstaller.__main__.run(args)
    print("\n" + "="*60)
    print("打包完成！")
    print("="*60)
    print("\n输出文件位置:")
    print("  Bazaar_Lens.exe (项目根目录)")
    print("\n提示:")
    print("  1. exe 文件已直接生成在项目根目录")
    print("  2. 使用 Inno Setup 创建安装程序")
    print("  3. 测试安装程序是否正常工作")
    print()
except Exception as e:
    print("\n" + "="*60)
    print("打包失败！")
    print("="*60)
    print(f"\n错误信息: {e}")
    sys.exit(1)
