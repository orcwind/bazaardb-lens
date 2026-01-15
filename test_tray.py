import sys
import os
sys.path.insert(0, 'main_script')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

class TestController:
    pass

try:
    print("开始测试SystemTray...")
    from system.tray import SystemTray
    
    print("创建SystemTray对象...")
    tray = SystemTray(TestController())
    
    print(f"icon对象: {tray.icon}")
    print(f"icon对象类型: {type(tray.icon)}")
    
    if tray.icon:
        print("系统托盘图标创建成功！")
    else:
        print("系统托盘图标创建失败，icon为None")
        
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
