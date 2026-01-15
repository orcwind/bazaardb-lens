# 保存为 test_env.py 并运行
import pystray
from PIL import Image, ImageDraw

def create_image():
    image = Image.new('RGB', (64, 64), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(255, 0, 0))
    return image

print("开始测试 pystray 环境...")
print(f"pystray 版本: {pystray.__version__ if hasattr(pystray, '__version__') else '未知'}")

# 检查后端
try:
    from pystray import BACKENDS
    print(f"可用的 pystray 后端: {BACKENDS}")
except Exception as e:
    print(f"无法获取后端信息: {e}")

icon = pystray.Icon("test_icon", create_image(), "Test")
print(f"Icon Object: {icon}")
print(f"Icon 类型: {type(icon)}")
print(f"Icon is None: {icon is None}")

if icon is not None:
    print("环境正常，尝试启动（请手动关闭窗口）...")
    try:
        icon.run()
    except KeyboardInterrupt:
        print("用户中断")
        icon.stop()
else:
    print("环境异常：pystray 无法生成对象")
