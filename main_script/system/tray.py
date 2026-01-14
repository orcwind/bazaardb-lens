"""
系统托盘模块
"""
import pystray
import logging
import os
from PIL import Image


class SystemTray:
    def __init__(self, controller_instance):
        self.controller = controller_instance
        self.create_tray_icon()
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建托盘图标菜单
        menu = (
            pystray.MenuItem("显示", self._show_window),
            pystray.MenuItem("退出", self._quit_application)
        )
        
        # 加载图标
        try:
            # 尝试从项目根目录加载
            current_file = os.path.abspath(__file__)  # system/tray.py
            system_dir = os.path.dirname(current_file)  # system目录
            main_script_dir = os.path.dirname(system_dir)  # main_script目录
            project_root = os.path.dirname(main_script_dir)  # 项目根目录
            icon_path = os.path.join(project_root, "Bazaar_Lens.ico")
            
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
            else:
                raise FileNotFoundError(f"图标文件不存在: {icon_path}")
        except Exception as e:
            logging.error(f"加载图标失败: {e}")
            # 创建一个默认的图标
            icon_image = Image.new('RGB', (64, 64), color='#496D89')
            
        # 创建系统托盘图标
        self.icon = pystray.Icon(
            "BazaarHelper",
            icon_image,
            "Bazaar Helper",
            menu
        )
        
    def run(self):
        """运行系统托盘"""
        if self.icon:
            self.icon.run()
    
    def stop(self):
        """停止系统托盘"""
        if self.icon:
            self.icon.stop()
    
    def _show_window(self, icon, item):
        """显示窗口"""
        try:
            if self.controller and self.controller.gui_manager:
                if self.controller.gui_manager.info_window:
                    self.controller.gui_manager.info_window.deiconify()
        except Exception as e:
            logging.error(f"显示窗口失败: {e}")
    
    def _quit_application(self, icon, item):
        """退出应用程序"""
        try:
            logging.info("收到退出请求，正在关闭程序...")
            if self.controller:
                self.controller.stop()
            if self.icon:
                self.icon.stop()
            import sys
            sys.exit(0)
        except Exception as e:
            logging.error(f"退出应用程序失败: {e}")
            import sys
            sys.exit(1)