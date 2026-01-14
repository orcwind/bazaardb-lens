"""
日志管理模块
"""
import os
import sys
import tempfile
import logging
import ctypes
from logging.handlers import RotatingFileHandler


def is_packaged_environment():
    """检测当前是否在打包后的环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_log_file_path():
    """获取日志文件路径，优先使用用户可写目录"""
    try:
        # 检测是否在打包环境中运行
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 打包环境：使用临时目录或用户文档目录
            try:
                # 尝试使用用户文档目录
                user_docs = os.path.join(os.path.expanduser('~'), 'Documents')
                if os.path.exists(user_docs) and os.access(user_docs, os.W_OK):
                    log_dir = os.path.join(user_docs, 'Bazaar_Lens')
                    os.makedirs(log_dir, exist_ok=True)
                    return os.path.join(log_dir, 'bazaar_helper.log')
            except BaseException:
                pass

            # 如果用户目录不可用，使用临时目录
            temp_dir = tempfile.gettempdir()
            log_dir = os.path.join(temp_dir, 'Bazaar_Lens')
            os.makedirs(log_dir, exist_ok=True)
            return os.path.join(log_dir, 'bazaar_helper.log')
        else:
            # 开发环境：使用当前目录
            return 'bazaar_helper.log'
    except Exception as e:
        # 最后的备用方案：使用临时目录
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, 'bazaar_helper.log')


def setup_logging():
    """设置日志系统"""
    # 获取日志文件路径
    log_file_path = get_log_file_path()

    # 创建日志格式
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 创建旋转文件处理器
    # maxBytes: 最大10MB，超过后自动创建新文件
    # backupCount: 保留最近3个备份文件
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)

    # 控制台处理器（只在开发环境显示）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def hide_console():
    """隐藏控制台窗口"""
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)  # 0表示隐藏窗口
    except Exception as e:
        logging.error(f"隐藏控制台失败: {e}")


def show_console():
    """显示控制台窗口"""
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 1)  # 1表示显示窗口
    except Exception as e:
        logging.error(f"显示控制台失败: {e}")
