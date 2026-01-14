"""
核心功能模块
"""
from .gui_manager import GUIManager
from .ocr_processor import OCRProcessor
from .window_detector import WindowDetector
from .main_controller import MainController

__all__ = ['GUIManager', 'OCRProcessor', 'WindowDetector', 'MainController']
