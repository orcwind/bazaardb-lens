"""
简单的托盘图标测试脚本
用于测试打包后的托盘图标是否能正常显示
"""
import sys
import os
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_tray.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

print("="*60)
print("托盘图标测试脚本")
print("="*60)
print(f"Python 版本: {sys.version}")
print(f"是否打包环境: {getattr(sys, 'frozen', False)}")
if hasattr(sys, '_MEIPASS'):
    print(f"临时目录: {sys._MEIPASS}")
print()

try:
    import pystray
    print("✓ pystray 导入成功")
    print(f"  pystray 版本: {getattr(pystray, '__version__', '未知')}")
except ImportError as e:
    print(f"✗ pystray 导入失败: {e}")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw
    print("✓ PIL/Pillow 导入成功")
except ImportError as e:
    print(f"✗ PIL/Pillow 导入失败: {e}")
    sys.exit(1)

# 测试图标路径解析
print("\n测试图标路径解析...")
def get_resource_path(relative_path):
    """获取资源的绝对路径，兼容开发和 PyInstaller 打包环境"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        print(f"  打包环境，使用 _MEIPASS: {base_path}")
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"  开发环境，使用当前目录: {base_path}")
    
    result_path = os.path.join(base_path, relative_path)
    exists = os.path.exists(result_path)
    print(f"  路径: {result_path}")
    print(f"  存在: {exists}")
    return result_path

icon_path = get_resource_path("Bazaar_Lens.ico")
print()

# 创建图标
print("创建图标...")
icon_image = None

# 尝试加载图标文件
if os.path.exists(icon_path):
    try:
        icon_image = Image.open(icon_path)
        icon_image.load()
        print(f"✓ 成功加载图标文件: {icon_path}, 尺寸: {icon_image.size}")
    except Exception as e:
        print(f"✗ 加载图标文件失败: {e}")
        icon_image = None
else:
    print(f"✗ 图标文件不存在: {icon_path}")

# 如果加载失败，创建兜底图标
if not icon_image or icon_image.size == (0, 0):
    print("  创建兜底图标...")
    icon_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon_image)
    draw.ellipse((4, 4, 60, 60), fill='#0078D7', outline='white', width=4)
    print("✓ 兜底图标创建成功")

# 创建菜单
print("\n创建菜单...")
try:
    def on_quit(icon, item):
        print("退出按钮被点击")
        icon.stop()
    
    menu = pystray.Menu(
        pystray.MenuItem("测试", lambda: print("测试菜单被点击")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit)
    )
    print("✓ 菜单创建成功")
except Exception as e:
    print(f"✗ 菜单创建失败: {e}")
    menu = None

# 创建托盘图标
print("\n创建托盘图标...")
try:
    icon = pystray.Icon(
        name="Bazaar Lens Test",
        icon=icon_image,
        title="Bazaar Lens Test",
        menu=menu
    )
    print(f"✓ 托盘图标对象创建成功: {icon}")
    print(f"  类型: {type(icon)}")
    print(f"  is None: {icon is None}")
except Exception as e:
    print(f"✗ 托盘图标创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 运行托盘
print("\n" + "="*60)
print("托盘图标应该已经显示在系统托盘区域")
print("请检查 Windows 系统托盘（包括隐藏图标区域）")
print("="*60)
print("\n按 Ctrl+C 退出...")

try:
    icon.run()
except KeyboardInterrupt:
    print("\n接收到中断信号，退出...")
    icon.stop()
except Exception as e:
    print(f"\n运行出错: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")
