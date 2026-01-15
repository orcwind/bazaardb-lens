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

# 导入模块化组件（延迟导入 heavy 部分，确保管理员检查先执行）
from system.admin import is_admin, run_as_admin
# 后续：在确认管理员权限后再导入 setup_logging、MainController 等以避免在非管理员模式初始化资源


def main():
    """主程序入口"""
    # 先检查管理员权限（功能需要管理员权限才能正常工作）
    if not is_admin():
        logging.warning("未检测到管理员权限，程序需要管理员权限才能正常工作")
        logging.info("尝试以管理员身份重新运行...")
        if run_as_admin():
            # 如果成功启动管理员进程，当前进程退出
            logging.info("已启动管理员进程，当前进程退出")
            sys.exit(0)
        else:
            # 如果用户拒绝了UAC提示或启动失败，立即退出，不创建任何资源
            logging.error("无法获取管理员权限，程序将立即退出")
            # 使用GUI消息框提示（如果可能），但使用非阻塞方式
            try:
                import tkinter.messagebox as messagebox
                # 使用 after 方法确保消息框显示后程序退出
                root = tk.Tk()
                root.withdraw()  # 隐藏主窗口
                messagebox.showerror("权限不足", "程序需要管理员权限才能正常工作。\n请手动以管理员身份运行程序。")
                root.destroy()
            except Exception as e:
                # 如果无法显示GUI，至少打印到控制台
                logging.error(f"显示错误消息失败: {e}")
                print("错误：程序需要管理员权限才能正常工作。")
                print("请右键点击程序，选择'以管理员身份运行'。")
            # 立即退出，不创建任何资源（包括托盘图标）
            # 使用 os._exit 强制退出，不执行任何清理操作
            import os
            os._exit(1)

    # 到这里说明是管理员，接着初始化日志和其他模块
    # 设置日志
    from logger import setup_logging, get_log_file_path, hide_console
    from core.main_controller import MainController
    setup_logging()
    log_path = get_log_file_path()
    logging.info(f"Bazaar Lens v{VERSION} 启动")
    logging.info(f"日志文件位置: {log_path}")
    
    # 在开发环境或配置允许时显示日志路径
    from config import ConfigManager
    temp_config = ConfigManager()
    if temp_config.get("show_console", False) or not getattr(sys, 'frozen', False):
        print(f"日志文件位置: {log_path}")
        print("如果遇到问题，请查看日志文件获取详细信息")

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
