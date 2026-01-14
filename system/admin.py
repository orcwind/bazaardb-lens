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
    """以管理员权限重新运行程序"""
    if not is_admin():
        try:
            logging.info("尝试以管理员权限重新运行程序...")
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{__file__}"', None, 1
            )
        except Exception as e:
            logging.error(f"获取管理员权限失败: {e}")
            print("请手动以管理员身份运行程序")
            # 等待3秒后自动退出，避免假死
            time.sleep(3)
            sys.exit()
