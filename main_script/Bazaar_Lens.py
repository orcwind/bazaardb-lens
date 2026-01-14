"""
Bazaar Lens 主程序
使用模块化架构重构后的版本
"""
import os
import sys
import threading
import traceback
import logging

# Windows相关导入
import win32api
import win32event
import winerror
import tkinter as tk

# 版本信息
try:
    # 尝试从项目根目录导入
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from version import VERSION
except ImportError:
    VERSION = "1.0.0"

# 导入模块化组件
from logger import setup_logging, hide_console
from system.admin import is_admin, run_as_admin
from core.main_controller import MainController


def main():
    """主程序入口"""
    # 设置日志
    setup_logging()
    logging.info(f"Bazaar Lens v{VERSION} 启动")

    # 检查管理员权限
    if not is_admin():
        logging.info("未检测到管理员权限，尝试以管理员身份重新运行...")
        if run_as_admin():
            sys.exit(0)
        else:
            logging.warning("无法获取管理员权限，程序可能无法正常工作")
            print("请手动以管理员身份运行程序")
            input("按Enter键退出...")
            sys.exit(1)

    # 创建互斥锁，防止多实例运行
    mutex = None
    try:
        mutex_name = "BazaarLensMutex"
        mutex = win32event.CreateMutex(None, False, mutex_name)
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logging.warning("程序已在运行，退出")
            print("程序已在运行中，请勿重复启动")
            sys.exit(0)
    except Exception as e:
        logging.warning(f"创建互斥锁失败，继续运行: {e}")
        mutex = None

    # 创建主控制器
    controller = None
    try:
        # 根据配置决定是否显示控制台（在创建controller之前）
        # 先创建临时config来检查设置
        from config import ConfigManager
        temp_config = ConfigManager()
        if not temp_config.get("show_console", False):
            hide_console()
        
        # 创建主控制器
        controller = MainController()
        
        # 初始化所有模块（这会创建GUI窗口）
        controller.initialize()
        
        # 运行主程序（这会阻塞直到程序退出）
        # GUIManager 已经创建了 tkinter 根窗口，这里直接运行主循环
        controller.run()

    except KeyboardInterrupt:
        logging.info("接收到键盘中断信号")
    except Exception as e:
        logging.error(f"主程序异常: {e}")
        logging.error(traceback.format_exc())
        # 显示错误信息
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("错误", f"程序运行出错:\n{e}\n\n详细信息请查看日志文件")
        except:
            print(f"程序运行出错: {e}")
    finally:
        # 清理资源
        if controller:
            try:
                controller.stop()
            except Exception as e:
                logging.error(f"停止controller时出错: {e}")

        # 释放互斥锁
        if mutex:
            try:
                win32api.CloseHandle(mutex)
            except Exception as e:
                logging.error(f"关闭互斥锁时出错: {e}")

        # 退出程序
        sys.exit(0)


if __name__ == "__main__":
    main()
