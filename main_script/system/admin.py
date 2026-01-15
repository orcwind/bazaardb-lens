"""
管理员权限相关功能
"""
import sys
import ctypes
import logging
import time


def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"检查管理员权限时出错: {e}")
        return False


def run_as_admin():
    """以管理员权限重新运行程序
    
    Returns:
        bool: 如果成功启动管理员进程返回True，否则返回False
    """
    if not is_admin():
        try:
            logging.info("尝试以管理员权限重新运行程序...")
            # ShellExecuteW 返回一个 HINSTANCE 值
            # 如果返回值 > 32，表示成功；如果 <= 32，表示失败
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1
            )
            # 检查返回值，如果成功（> 32），返回 True
            if result > 32:
                logging.info("已成功请求管理员权限，新进程将启动")
                return True
            else:
                logging.warning(f"请求管理员权限失败，返回值: {result}")
                return False
        except Exception as e:
            logging.error(f"获取管理员权限失败: {e}")
            return False
    return True  # 如果已经是管理员，返回 True
