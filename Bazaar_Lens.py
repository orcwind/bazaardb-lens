# 标准库导入
import os
import sys
import json
import logging
import traceback
import re
import difflib
from urllib.parse import urlparse
import datetime
import shutil

# 版本信息
from version import VERSION

# 检测是否在打包环境中运行
def is_packaged_environment():
    """检测当前是否在打包后的环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# 第三方库导入
import keyboard
import win32gui
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pyautogui
import win32con
import win32api
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageDraw, ImageFont

# Python 3.13 兼容性补丁：cgi 模块已被移除（已移除PaddleOCR，不再需要）

# PaddleOCR已移除，仅使用Tesseract
import pytesseract
import time
import ctypes
from ctypes import wintypes
import win32com.client
import threading
import concurrent.futures
import io
import tempfile
import subprocess
import pystray
import psutil
import webbrowser
import win32event
import winerror
import win32process

# 设置日志 - 使用旋转日志文件，自动管理大小和备份
from logging.handlers import RotatingFileHandler
import tempfile

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
            except:
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

# 获取日志文件路径
log_file_path = get_log_file_path()

# 创建日志格式
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 创建旋转文件处理器
# maxBytes: 最大10MB，超过后自动创建新文件
# backupCount: 保留最近3个备份文件
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=10*1024*1024,  # 10MB
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

# 顶层定义ocr_task，确保无缩进
def ocr_task(img_bytes):
    from PIL import Image
    import pytesseract
    import io
    try:
        # 使用全局设置的tesseract_cmd路径
        img = Image.open(io.BytesIO(img_bytes))
        # 使用标准版本（tessdata_fast中没有chi_sim_fast）
        # 使用PSM 6（统一文本块）和OEM 3（LSTM引擎）以获得最佳速度和准确率平衡
        return pytesseract.image_to_string(
            img,
            config='--psm 6 --oem 3 -l chi_sim'
        ).strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

# 添加不使用进程池的OCR函数
def direct_ocr(img_bytes, psm=6, paddle_ocr=None):
    """直接在当前线程执行OCR，使用Tesseract"""
    from PIL import Image
    import io
    
    try:
        img = Image.open(io.BytesIO(img_bytes))
        
        # 使用Tesseract OCR
        # 使用PSM 6（统一文本块）和OEM 3（LSTM引擎）以获得最佳速度和准确率平衡
        ocr_text = pytesseract.image_to_string(
            img,
            config=f'--psm {psm} --oem 3 -l chi_sim'
        ).strip()
        
        if ocr_text:
            logging.debug(f"[Tesseract] 识别成功: {repr(ocr_text[:100])}")
        return ocr_text if ocr_text else None
            
    except Exception as e:
        logging.error(f"direct_ocr错误: {e}")
        logging.error(traceback.format_exc())
        return None

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

class IconFrame(tk.Frame):
    """用于显示图标和文本的框架"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # 获取父容器的背景色，如果没有指定则使用深色主题
        parent_bg = parent.cget('bg') if parent else '#1C1810'
        self.configure(bg=parent_bg)
        
        # 创建左侧图标容器，固定宽度
        self.icon_container = tk.Frame(self, bg=parent_bg, width=144, height=96)
        self.icon_container.pack_propagate(False)
        self.icon_container.pack(side='left', padx=0, pady=0)
        
        # 创建图标标签
        self.icon_label = tk.Label(self.icon_container, bg=parent_bg)
        self.icon_label.pack(expand=True)
        
        # 创建右侧文本容器
        self.text_frame = tk.Frame(self, bg=parent_bg)
        self.text_frame.pack(side='left', fill='both', expand=True, padx=0, pady=0)
        
        # 创建名称和数量的容器
        self.name_container = tk.Frame(self.text_frame, bg=parent_bg)
        self.name_container.pack(fill='x', anchor='w', pady=0)
        
        # 创建名称标签
        self.name_label = tk.Label(
            self.name_container,
            font=('Segoe UI', 14, 'bold'),
            fg='#E8D4B9',  # 浅色文字
            bg=parent_bg,
            anchor='w',
            justify='left'
        )
        self.name_label.pack(side='left', anchor='w')
        
        # 创建数量标签
        self.quantity_label = tk.Label(
            self.name_container,
            font=('Segoe UI', 16, 'bold'),  # 更大的字体
            fg='#FFD700',  # 金色文字
            bg=parent_bg,
            anchor='w',
            justify='left'
        )
        self.quantity_label.pack(side='left', padx=(5, 0))
        
        # 创建描述标签
        self.desc_label = tk.Label(
            self.text_frame,
            font=('Segoe UI', 13),
            fg='#BFA98F',  # 稍暗的浅色文字用于描述
            bg=parent_bg,
            anchor='w',
            wraplength=400,
            justify='left'
        )
        self.desc_label.pack(fill='both', expand=True, anchor='w')
        
        # 保存当前图像
        self.current_photo = None
        self._photo_refs = []  # 用于保存所有PhotoImage对象的引用

    def format_description(self, description):
        """格式化描述文本，处理换行和空格
        
        规则：
        1. 数字\n秒\n → 数字 秒 （空格）
        2. 其他 \n 转换为逗号，但如果遇到新句子（以"使用"、"当"等开头）则换行
        3. 如果一行太长（超过一定长度），自动换行
        """
        if not description:
            return ''
        
        # 处理冷却时间格式：数字\n秒\n → 数字 秒 
        # 匹配模式：数字（可能带小数）\n秒\n
        description = re.sub(r'(\d+\.?\d*)\n秒\n', r'\1 秒 ', description)
        
        # 将剩余的 \n 转换为逗号，但保留某些特定的换行
        # 先按 \n 分割
        lines = [line.strip() for line in description.split('\n') if line.strip()]
        
        if not lines:
            return ''
        
        formatted_lines = []
        current_line = ''
        
        for i, line in enumerate(lines):
            # 如果当前行为空，直接添加
            if not current_line:
                current_line = line
            else:
                # 判断是否应该换行
                # 检查是否是新的句子开始（以某些关键词开头）
                is_new_sentence = (
                    line.startswith('使用') or
                    line.startswith('当') or
                    line.startswith('如果') or
                    line.startswith('此物品') or
                    (line.startswith('此') and len(current_line) > 30)
                )
                
                # 如果当前行已经很长（超过60个字符），考虑换行
                is_too_long = len(current_line) > 60
                
                if is_new_sentence or (is_too_long and is_new_sentence):
                    # 新句子开始，换行
                    formatted_lines.append(current_line)
                    current_line = line
                elif is_too_long:
                    # 虽然很长，但不是新句子，用逗号连接（tkinter会自动换行）
                    current_line += '，' + line
                else:
                    # 用逗号连接
                    current_line += '，' + line
        
        # 添加最后一行
        if current_line:
            formatted_lines.append(current_line)
        
        # 用换行符连接多行
        result = '\n'.join(formatted_lines)
        
        return result

    def update_content(self, name, description, icon_path=None, aspect_ratio=1.0):
        try:
            # 获取当前背景色
            bg_color = self.cget('bg')
            
            # 处理名称和数量
            if name:
                # 分离名称和数量
                quantity_match = re.search(r'^(.*?)\s*x(\d+)\s*$', name)
                if quantity_match:
                    base_name = quantity_match.group(1)
                    quantity = quantity_match.group(2)
                    self.name_label.config(text=base_name, anchor='w', justify='left', bg=bg_color)
                    self.quantity_label.config(text=f"×{quantity}", bg=bg_color)  # 使用中文乘号
                    self.quantity_label.pack(side='left', padx=(5, 0))
                else:
                    self.name_label.config(text=name, anchor='w', justify='left', bg=bg_color)
                    self.quantity_label.pack_forget()
                self.name_container.pack(fill='x', anchor='w', pady=0)
            else:
                self.name_container.pack_forget()
            
            # 描述左对齐（格式化描述）
            if description:
                formatted_description = self.format_description(description)
                self.desc_label.config(text=formatted_description, anchor='w', justify='left', bg=bg_color)
                self.desc_label.pack(fill='both', expand=True)
            else:
                self.desc_label.pack_forget()
            
            # 图标处理
            icon_container_width = 144
            icon_container_height = 96
            self.icon_container.config(width=icon_container_width, height=icon_container_height, bg=bg_color)
            
            if icon_path and os.path.exists(icon_path):
                try:
                    # 处理图标路径中的@符号
                    real_icon_path = icon_path
                    if '@' in icon_path:
                        # 保持@符号，不进行替换
                        real_icon_path = icon_path
                    
                    img = Image.open(real_icon_path).convert('RGBA')
                    icon_height = icon_container_height
                    icon_width = int(icon_height * aspect_ratio)
                    icon_width = min(icon_width, icon_container_width)
                    img = img.resize((icon_width, icon_height), Image.Resampling.LANCZOS)
                    
                    # 创建透明底图，保证居中
                    bg = Image.new('RGBA', (icon_container_width, icon_container_height), (0, 0, 0, 0))
                    offset_x = (icon_container_width - icon_width) // 2
                    bg.paste(img, (offset_x, 0), img)
                    
                    # 关键：转为PNG内存流再交给PhotoImage
                    with io.BytesIO() as output:
                        bg.save(output, format='PNG')
                        photo = ImageTk.PhotoImage(data=output.getvalue())
                    
                    self.icon_label.configure(image=photo, bg=bg_color)
                    self._photo_refs.append(photo)
                    
                except Exception as e:
                    logging.error(f"加载图标失败: {e}")
                    self.clear_icon()
            else:
                self.clear_icon()
            
            self.icon_container.pack(side='left', padx=0, pady=0)
            self.update()
            
        except Exception as e:
            logging.error(f"更新内容失败: {e}")
            self.clear_icon()

    def clear_icon(self):
        """清理图标"""
        try:
            bg_color = self.cget('bg')
            self.icon_label.configure(image='', bg=bg_color)
            self._photo_refs.clear()
        except Exception as e:
            logging.error(f"清理图标失败: {e}")

    def destroy(self):
        """重写destroy方法，确保清理所有资源"""
        try:
            self.clear_icon()
            super().destroy()
        except Exception as e:
            logging.error(f"销毁IconFrame失败: {e}")

class ScrollableFrame(tk.Frame):
    """可滚动的框架类"""
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg', '#1C1810')
        super().__init__(parent, **kwargs)
        self.configure(bg=bg_color)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 创建Canvas
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # 创建滚动条
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 创建内部框架
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        # 绑定事件
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 初始隐藏滚动条
        self.scrollbar.grid_remove()
        
    def _on_canvas_configure(self, event):
        """当Canvas大小改变时，调整内部窗口宽度"""
        self.canvas.itemconfig(self.inner_frame_id, width=event.width)
        
    def _on_frame_configure(self, event):
        """当内部框架大小改变时，更新滚动区域"""
        # 更新Canvas的滚动区域
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 检查是否需要显示滚动条
        inner_height = self.inner_frame.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()
        
        if inner_height > canvas_height:
            # 内容高度超过Canvas高度，显示滚动条
            self.scrollbar.grid()
        else:
            # 内容高度不超过Canvas高度，隐藏滚动条
            self.scrollbar.grid_remove()
        
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        # 只有当滚动条显示时才处理滚轮事件
        if self.scrollbar.winfo_ismapped():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
    def update_scrollregion(self):
        """手动更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 检查是否需要显示滚动条
        inner_height = self.inner_frame.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()
        
        if inner_height > canvas_height:
            # 内容高度超过Canvas高度，显示滚动条
            self.scrollbar.grid()
        else:
            # 内容高度不超过Canvas高度，隐藏滚动条
            self.scrollbar.grid_remove()
            
    def get_inner_frame(self):
        """获取内部框架"""
        return self.inner_frame

class ConfigManager:
    """配置管理类，用于保存和加载配置"""
    def __init__(self):
        self.config_file = "bazaar_lens_config.json"
        # 默认 Tesseract 路径：必须使用项目目录下的便携版
        app_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        portable_tesseract = os.path.join(app_dir, "Tesseract-OCR", "tesseract.exe")
        
        self.default_config = {
            "tesseract_path": portable_tesseract,
            "last_update_check": "",
            "auto_update": True,
            "show_console": False
        }
        self.config = self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 确保所有默认配置项都存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                
                # 强制使用便携版路径（如果存在），覆盖配置文件中的旧路径
                portable_tesseract = self.default_config.get("tesseract_path")
                if portable_tesseract and os.path.exists(portable_tesseract):
                    config["tesseract_path"] = portable_tesseract
                    logging.info(f"强制使用便携版Tesseract: {portable_tesseract}")
                
                return config
            else:
                return self.default_config.copy()
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return self.default_config.copy()
            
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False
            
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
        
    def set(self, key, value):
        """设置配置项并保存"""
        self.config[key] = value
        return self.save_config()
        
    def get_tesseract_path(self):
        """获取Tesseract OCR路径"""
        return self.get("tesseract_path", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        
    def set_tesseract_path(self, path):
        """设置Tesseract OCR路径"""
        if path and os.path.exists(path) and os.path.isfile(path):
            return self.set("tesseract_path", path)
        return False

class BazaarHelper:
    def __init__(self):
        """初始化BazaarHelper"""
        # 加载位置配置
        self.position_config = self.load_position_config()
        # 计算相对位置关系（用于动态计算名称区域）
        self.monster_icon_name_offset = self.calculate_relative_offset('monster')
        self.item_icon_name_offset = self.calculate_relative_offset('item')
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.shift_pressed = False
        self.last_check_time = time.time()
        self.check_interval = 0.1  # 缩短检查间隔到0.1秒
        self.is_running = True
        self.info_window = None
        self.current_text = None
        self.monster_data = {}
        self.event_data = {}
        self.event_name_map = {}  # 中文名称 -> 英文名称的映射
        self.items_data = {}  # 物品数据字典，key为英文名称
        self.skills_data = {}  # 技能数据字典，key为英文名称
        
        # 添加配置管理器
        self.config = ConfigManager()
        
        # 添加OCR线程锁
        self.ocr_lock = threading.Lock()
        
        # 添加GUI更新队列（线程安全）
        self.gui_update_queue = []
        self.gui_update_lock = threading.Lock()
        
        # 添加图标缓存
        self.icon_cache = {}
        
        # 添加OCR结果缓存（基于文本内容的匹配结果缓存）
        self.ocr_cache = {}  # 图像hash -> OCR文本
        self.match_cache = {}  # OCR文本 -> 匹配结果
        self.ocr_cache_max_size = 20
        self.match_cache_max_size = 50
        
        # 游戏日志监控相关
        self.log_monitor_thread = None
        self.log_monitor_running = False
        self.log_data_lock = threading.Lock()
        self.instance_to_template = {}  # InstanceId -> TemplateId 映射
        self.template_to_name_zh = {}  # TemplateId -> 中文名称 映射
        self.uuid_to_item_data = {}  # UUID (TemplateId) -> 物品数据 映射（从items_db.json加载）
        self.hand_items = set()  # 手牌物品InstanceId集合
        self.stash_items = set()  # 仓库物品InstanceId集合
        self.equipped_items = set()  # 当前装备的物品InstanceId集合（手牌+仓库，保留用于兼容）
        
        # 检测运行环境
        self.is_packaged = is_packaged_environment()
        if self.is_packaged:
            logging.info("检测到打包环境，使用简化OCR策略")
        else:
            logging.info("检测到开发环境，使用标准OCR策略")
            
        # 检查Tesseract是否可用
        self.check_tesseract()
        
        # 加载数据
        self.load_monster_data()
        self.load_event_data()
        self.load_items_data()  # 加载物品数据（用于附魔显示）
        
        # 创建信息窗口（但保持隐藏状态）
        self.create_info_window()
        
        # 启动保活线程
        self.keep_alive_thread = threading.Thread(target=self.keep_alive, daemon=True)
        self.keep_alive_thread.start()
        
        # 启动游戏日志监控线程（用于辅助OCR识别）
        self.start_log_monitor()

        # 创建系统托盘
        self.system_tray = SystemTray(self)

        # 启动自动更新检查
        if self.config.get("auto_update", True):
            self.check_for_updates()

        # 根据配置决定是否显示控制台（默认隐藏，但生成日志文件）
        if not self.config.get("show_console", False):
            hide_console()
        
        # 启动GUI更新定时器
        self.start_gui_update_timer()

    def start_gui_update_timer(self):
        """启动GUI更新定时器（在主线程中）"""
        def process_gui_updates():
            try:
                # 处理GUI更新队列
                with self.gui_update_lock:
                    if self.gui_update_queue:
                        # 只处理最新的更新，忽略旧的
                        task = self.gui_update_queue[-1]
                        self.gui_update_queue.clear()
                        
                        task_type = task.get('type')
                        if task_type == 'show':
                            self._do_show_info(task['text'], task['x'], task['y'])
                        elif task_type == 'show_enchantments':
                            self._do_show_enchantments(task['text'], task['x'], task['y'])
                        elif task_type == 'hide':
                            self._do_hide_info()
                        elif task_type == 'adjust':
                            self._do_adjust_window(task['x'], task['y'])
                        elif task_type == 'move':
                            self._do_move_window(task['x'], task['y'])
            except Exception as e:
                logging.error(f"处理GUI更新队列异常: {e}")
            finally:
                # 每50ms检查一次更新队列
                if self.is_running and self.info_window:
                    self.info_window.after(50, process_gui_updates)
        
        # 启动定时器
        if self.info_window:
            self.info_window.after(50, process_gui_updates)
    
    def keep_alive(self):
        """保活机制，检查Ctrl键、Alt键和Shift键状态和程序响应（不直接操作GUI）"""
        VK_CONTROL = 0x11  # Ctrl键的虚拟键码
        VK_MENU = 0x12  # Alt键的虚拟键码（VK_MENU是Alt键）
        VK_SHIFT = 0x10  # Shift键的虚拟键码
        last_action_time = 0  # 上次执行动作的时间
        debounce_delay = 0.5  # 防抖动延迟(秒)
        last_position = (0, 0)  # 上次鼠标位置
        position_update_interval = 0.1  # 位置更新间隔
        last_position_update = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                # 使用win32api检查Ctrl键、Shift键状态（Alt键功能已禁用）
                ctrl_state = win32api.GetAsyncKeyState(VK_CONTROL)
                shift_state = win32api.GetAsyncKeyState(VK_SHIFT)
                # alt_state = win32api.GetAsyncKeyState(VK_MENU)  # Alt键功能已禁用
                is_ctrl_pressed = (ctrl_state & 0x8000) != 0
                is_shift_pressed = (shift_state & 0x8000) != 0
                # is_alt_pressed = (alt_state & 0x8000) != 0  # Alt键功能已禁用
                
                # Ctrl键状态发生变化（怪物/事件）
                if is_ctrl_pressed != self.ctrl_pressed:
                    self.ctrl_pressed = is_ctrl_pressed
                    if is_ctrl_pressed:
                        time_since_last = current_time - last_action_time
                        logging.info(f"Ctrl键按下，距离上次动作: {time_since_last:.2f}秒，防抖动延迟: {debounce_delay}秒")
                        # 添加防抖动: 检查距离上次动作的时间是否足够
                        if current_time - last_action_time >= debounce_delay:
                            logging.info("防抖动检查通过，开始OCR识别")
                            # Ctrl键被按下，获取并显示信息（使用右上角区域）
                            text = self.get_text_at_cursor(region_type='monster')
                            if text:
                                x, y = pyautogui.position()
                                last_position = (x, y)
                                # 添加到GUI更新队列而不是直接操作
                                with self.gui_update_lock:
                                    self.gui_update_queue.append({
                                        'type': 'show',
                                        'text': text,
                                        'x': x,
                                        'y': y
                                    })
                                last_action_time = current_time
                    else:
                                logging.warning("OCR识别返回空文本")
                        else:
                            logging.info(f"防抖动阻止：距离上次动作仅 {time_since_last:.2f}秒，需要等待 {debounce_delay - time_since_last:.2f}秒")
                    else:
                        # Ctrl键释放
                        logging.info("Ctrl键释放")
                        # Ctrl键释放，添加隐藏任务到队列
                        with self.gui_update_lock:
                            self.gui_update_queue.append({'type': 'hide'})
                
                # Shift键状态发生变化（物品附魔显示）
                if is_shift_pressed != self.shift_pressed:
                    self.shift_pressed = is_shift_pressed
                    if is_shift_pressed:
                        time_since_last = current_time - last_action_time
                        logging.info(f"Shift键按下，距离上次动作: {time_since_last:.2f}秒，防抖动延迟: {debounce_delay}秒")
                        # 添加防抖动: 检查距离上次动作的时间是否足够
                        if current_time - last_action_time >= debounce_delay:
                            logging.info("Shift键防抖动检查通过，开始物品OCR识别")
                            # Shift键被按下，获取物品信息并显示附魔
                            text = self.get_text_at_cursor(region_type='item')
                            if text:
                                x, y = pyautogui.position()
                                last_position = (x, y)
                                # 添加到GUI更新队列而不是直接操作
                                with self.gui_update_lock:
                                    self.gui_update_queue.append({
                                        'type': 'show_enchantments',
                                        'text': text,
                                        'x': x,
                                        'y': y
                                    })
                                last_action_time = current_time
                            else:
                                logging.warning("Shift OCR识别返回空文本")
                        else:
                            logging.info(f"Shift键防抖动阻止：距离上次动作仅 {time_since_last:.2f}秒，需要等待 {debounce_delay - time_since_last:.2f}秒")
                    else:
                        # Shift键释放
                        logging.info("Shift键释放")
                        # Shift键释放，添加隐藏任务到队列
                        with self.gui_update_lock:
                            self.gui_update_queue.append({'type': 'hide'})
                
                # Alt键功能已禁用
                # # Alt键状态发生变化（物品，后续功能）
                # if is_alt_pressed != self.alt_pressed:
                #     self.alt_pressed = is_alt_pressed
                #     if is_alt_pressed:
                #         # 添加防抖动: 检查距离上次动作的时间是否足够
                #         if current_time - last_action_time >= debounce_delay:
                #             # Alt键被按下，获取并显示信息（使用上方区域）
                #             text = self.get_text_at_cursor(region_type='item')
                #             if text:
                #                 x, y = pyautogui.position()
                #                 last_position = (x, y)
                #                 # TODO: 后续添加物品识别逻辑
                #                 logging.debug("Alt键按下，物品识别功能待实现")
                #                 # 添加到GUI更新队列而不是直接操作
                #                 with self.gui_update_lock:
                #                     self.gui_update_queue.append({
                #                         'type': 'show',
                #                         'text': text,
                #                         'x': x,
                #                         'y': y
                #                     })
                #                 last_action_time = current_time
                #     else:
                #         # Alt键释放，如果当前显示的是物品信息，则隐藏
                #         # （这里暂时不处理，因为物品功能还未实现）
                #         pass
                
                # 更新窗口位置（如果窗口显示中且Ctrl键或Shift键仍然按下，Alt键功能已禁用）
                if self.ctrl_pressed or self.shift_pressed:  # or self.alt_pressed:  # Alt键功能已禁用
                    # 限制位置更新频率
                    if current_time - last_position_update >= position_update_interval:
                        x, y = pyautogui.position()
                        # 只在位置变化时更新
                        if (x, y) != last_position:
                            last_position = (x, y)
                            with self.gui_update_lock:
                                self.gui_update_queue.append({
                                    'type': 'move',  # 改为 move 类型，只移动位置不调整大小
                                    'x': x,
                                    'y': y
                                })
                            last_position_update = current_time
                
                # 短暂休眠以减少CPU使用
                time.sleep(0.02)
                
            except Exception as e:
                logging.error(f"保活线程异常: {e}")
                time.sleep(1)  # 发生异常时稍长的休眠
                continue
    
    def run(self):
        """运行主程序"""
        try:
            if self.info_window:
                self.info_window.mainloop()
        except Exception as e:
            logging.error(f"主程序运行异常: {e}")
            self.stop()
    
    def stop(self):
        """停止程序"""
        self.is_running = False
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            self.keep_alive_thread.join(timeout=1)
        self.destroy_info_window()
        
        # 清理系统托盘图标
        try:
            if hasattr(self, 'system_tray') and self.system_tray.icon:
                self.system_tray.icon.stop()
        except Exception as e:
            logging.error(f"停止系统托盘图标时出错: {e}")
        
        # 清理临时文件
        self.cleanup_temp_files()

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_files = ['debug_binary.png', 'debug_capture.png']
            for filename in temp_files:
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                        logging.info(f"已删除临时文件: {filename}")
                    except Exception as e:
                        logging.warning(f"删除临时文件失败: {filename}, 错误: {e}")
        except Exception as e:
            logging.error(f"清理临时文件时出错: {e}")
    
    def cleanup_system_tray_icons(self):
        """清理系统托盘中的遗留图标"""
        try:
            logging.info("开始清理系统托盘中的遗留图标...")
            
            # 方法1: 使用系统命令清理通知区域
            self._cleanup_notification_area()
            
            # 方法2: 清理注册表中的图标缓存
            self._cleanup_icon_cache()
            
            # 方法3: 刷新系统托盘（不重启 Explorer）
            self._refresh_system_tray()
            
            logging.info("系统托盘图标清理完成")
            
        except Exception as e:
            logging.error(f"清理系统托盘图标时出错: {e}")
            logging.error(traceback.format_exc())
    
    def _cleanup_notification_area(self):
        """清理通知区域图标"""
        try:
            # 使用 PowerShell 命令清理通知区域
            ps_script = '''
            # 清理通知区域的图标缓存
            Remove-ItemProperty -Path "HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify" -Name "IconStreams" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path "HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify" -Name "PastIconsStream" -ErrorAction SilentlyContinue
            Write-Host "Notification area icons cache cleared"
            '''
            
            # 执行 PowerShell 脚本
            result = subprocess.run([
                'powershell', '-Command', ps_script
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logging.info("通知区域图标缓存已清理")
            else:
                logging.warning(f"清理通知区域失败: {result.stderr}")
                
        except Exception as e:
            logging.error(f"清理通知区域时出错: {e}")
    
    def _refresh_system_tray(self):
        """刷新系统托盘（不重启 Explorer）"""
        try:
            logging.info("正在刷新系统托盘...")
            
            # 发送消息刷新系统托盘
            import win32gui
            import win32con
            
            # 获取系统托盘窗口句柄
            tray_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if tray_hwnd:
                # 发送刷新消息
                win32gui.PostMessage(tray_hwnd, win32con.WM_COMMAND, 419, 0)
                logging.info("已发送系统托盘刷新消息")
            
            # 尝试刷新通知区域
            notification_hwnd = win32gui.FindWindowEx(tray_hwnd, None, "TrayNotifyWnd", None)
            if notification_hwnd:
                win32gui.InvalidateRect(notification_hwnd, None, True)
                win32gui.UpdateWindow(notification_hwnd)
                logging.info("已刷新通知区域")
            
            # 等待刷新完成
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"刷新系统托盘时出错: {e}")
    
    def _restart_explorer(self):
        """重启 Windows Explorer 进程（备用方法）"""
        try:
            logging.info("正在重启 Windows Explorer...")
            
            # 终止 Explorer 进程
            subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'], 
                         capture_output=True, timeout=10)
            
            # 等待一秒
            time.sleep(1)
            
            # 重新启动 Explorer
            subprocess.Popen(['explorer.exe'])
            
            logging.info("Windows Explorer 已重启")
            
        except Exception as e:
            logging.error(f"重启 Explorer 时出错: {e}")
    
    def _cleanup_icon_cache(self):
        """清理图标缓存"""
        try:
            # 清理图标缓存目录
            cache_dirs = [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
                os.path.join(os.environ.get('TEMP', ''), 'Low')
            ]
            
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    # 查找并删除图标缓存文件
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            if file.lower() in ['iconcache.db', 'thumbcache_*.db', '*.tmp']:
                                try:
                                    file_path = os.path.join(root, file)
                                    os.remove(file_path)
                                    logging.info(f"已删除图标缓存文件: {file_path}")
                                except Exception as e:
                                    logging.warning(f"删除图标缓存文件失败: {file_path}, 错误: {e}")
            
            logging.info("图标缓存清理完成")
            
        except Exception as e:
            logging.error(f"清理图标缓存时出错: {e}")

    def load_position_config(self):
        """加载位置配置文件"""
        try:
            # 获取数据文件路径（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                base_dir = os.path.dirname(__file__)
            
            position_file = os.path.join(base_dir, 'data', 'Json', 'position.json')
            if os.path.exists(position_file):
                with open(position_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logging.info("成功加载位置配置文件")
                    self.position_config = config
                    # 计算相对位置关系
                    self.monster_icon_name_offset = self.calculate_relative_offset('monster')
                    self.item_icon_name_offset = self.calculate_relative_offset('item')
                    return config
            else:
                logging.warning(f"位置配置文件不存在: {position_file}")
                self.position_config = None
                return None
        except Exception as e:
            logging.error(f"加载位置配置文件失败: {e}")
            self.position_config = None
            return None
    
    def calculate_relative_offset(self, entity_type='monster'):
        """
        计算图标和名称的相对位置关系
        
        Args:
            entity_type: 'monster' 或 'item'
        
        Returns:
            dict: 包含相对偏移量的字典
        """
        if not self.position_config:
            return None
        
        try:
            icon_data = self.position_config.get(entity_type, {}).get('icon', {})
            name_data = self.position_config.get(entity_type, {}).get('name', {})
            
            if not icon_data or not name_data:
                logging.warning(f"位置配置中缺少 {entity_type} 的数据")
                return None
            
            # 计算相对偏移量
            offset = {
                'x_offset_tl': name_data['top_left']['x'] - icon_data['top_left']['x'],
                'y_offset_tl': name_data['top_left']['y'] - icon_data['top_left']['y'],
                'x_offset_tr': name_data['top_right']['x'] - icon_data['top_right']['x'],
                'y_offset_tr': name_data['top_right']['y'] - icon_data['top_right']['y'],
                'x_offset_bl': name_data['bottom_left']['x'] - icon_data['bottom_left']['x'],
                'y_offset_bl': name_data['bottom_left']['y'] - icon_data['bottom_left']['y'],
                'x_offset_br': name_data['bottom_right']['x'] - icon_data['bottom_right']['x'],
                'y_offset_br': name_data['bottom_right']['y'] - icon_data['bottom_right']['y'],
            }
            
            logging.debug(f"{entity_type} 相对偏移量: {offset}")
            return offset
        except Exception as e:
            logging.error(f"计算 {entity_type} 相对偏移量失败: {e}")
            return None
    
    def is_cursor_in_icon_area(self, cursor_x, cursor_y, entity_type='monster', window_rect=None):
        """
        检查鼠标是否在图标区域内
        
        Args:
            cursor_x, cursor_y: 鼠标坐标（屏幕绝对坐标）
            entity_type: 'monster' 或 'item'
            window_rect: 游戏窗口坐标 (left, top, right, bottom)，用于坐标转换
        
        Returns:
            tuple: (是否在区域内, 图标区域的实际坐标) 或 (False, None)
        """
        if not self.position_config:
            return False, None
        
        if not window_rect or len(window_rect) != 4:
            logging.warning("[区域检测] 窗口坐标无效，无法进行图标区域检测")
            return False, None
        
        try:
            icon_data = self.position_config.get(entity_type, {}).get('icon', {})
            if not icon_data:
                return False, None
            
            # 获取参考坐标（从配置文件，这些是记录时的屏幕绝对坐标）
            ref_tl = (icon_data['top_left']['x'], icon_data['top_left']['y'])
            ref_tr = (icon_data['top_right']['x'], icon_data['top_right']['y'])
            ref_bl = (icon_data['bottom_left']['x'], icon_data['bottom_left']['y'])
            ref_br = (icon_data['bottom_right']['x'], icon_data['bottom_right']['y'])
            
            # 计算参考图标的边界框（使用最小外接矩形）
            ref_min_x = min(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_max_x = max(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_min_y = min(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            ref_max_y = max(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            
            # 将参考坐标转换为相对于窗口的坐标（假设记录时窗口位置是已知的）
            # 由于我们不知道记录时的窗口位置，我们使用一个更灵活的方法：
            # 计算图标区域相对于其中心点的相对位置，然后根据当前鼠标位置和窗口位置进行匹配
            
            # 方法1：直接比较绝对坐标（适用于窗口位置不变的情况）
            # 使用宽裕的容差（扩大20%的范围）
            tolerance_x = (ref_max_x - ref_min_x) * 0.2
            tolerance_y = (ref_max_y - ref_min_y) * 0.2
            
            # 检查鼠标是否在图标区域内（使用容差）
            if (ref_min_x - tolerance_x <= cursor_x <= ref_max_x + tolerance_x and
                ref_min_y - tolerance_y <= cursor_y <= ref_max_y + tolerance_y):
                # 返回实际图标区域的坐标（使用容差后的范围）
                actual_icon_area = {
                    'min_x': ref_min_x - tolerance_x,
                    'max_x': ref_max_x + tolerance_x,
                    'min_y': ref_min_y - tolerance_y,
                    'max_y': ref_max_y + tolerance_y
                }
                logging.debug(f"[区域检测] 鼠标在图标区域内（绝对坐标匹配）")
                return True, actual_icon_area
            
            # 方法2：如果绝对坐标不匹配，尝试使用相对位置匹配
            # 计算鼠标相对于窗口的位置
            cursor_rel_x = cursor_x - window_rect[0]
            cursor_rel_y = cursor_y - window_rect[1]
            
            # 尝试推断记录时的窗口位置
            # 假设position.json中的坐标是屏幕绝对坐标，我们需要找到记录时的窗口位置
            # 由于我们不知道记录时的窗口位置，我们尝试几种方法：
            
            # 方法2a：假设记录时的窗口位置是(0,0)，将position.json中的坐标视为相对于窗口的坐标
            # 但这不太可能，因为坐标值很大（1144, 401）
            
            # 方法2b：尝试推断记录时的窗口位置
            # 如果position.json中的坐标是屏幕绝对坐标，我们可以尝试通过比较当前窗口位置来推断
            # 但这需要知道记录时的窗口位置，否则无法正确匹配
            
            # 方法2c：更实用的方法 - 使用更大的容差，并检查鼠标是否在窗口内的合理位置
            # 扩大容差范围，允许更大的位置变化（扩大到100%的范围，即允许图标区域大小的一倍偏移）
            expanded_tolerance_x = (ref_max_x - ref_min_x) * 1.0  # 扩大到100%
            expanded_tolerance_y = (ref_max_y - ref_min_y) * 1.0
            
            # 检查鼠标是否在扩大后的图标区域内
            if (ref_min_x - expanded_tolerance_x <= cursor_x <= ref_max_x + expanded_tolerance_x and
                ref_min_y - expanded_tolerance_y <= cursor_y <= ref_max_y + expanded_tolerance_y):
                # 检查鼠标是否在窗口内
                if (window_rect[0] <= cursor_x <= window_rect[2] and
                    window_rect[1] <= cursor_y <= window_rect[3]):
                    # 返回实际图标区域的坐标（使用扩大容差后的范围）
                    actual_icon_area = {
                        'min_x': ref_min_x - expanded_tolerance_x,
                        'max_x': ref_max_x + expanded_tolerance_x,
                        'min_y': ref_min_y - expanded_tolerance_y,
                        'max_y': ref_max_y + expanded_tolerance_y
                    }
                    logging.info(f"[区域检测] 鼠标在图标区域内（扩大容差匹配，容差: {expanded_tolerance_x:.1f}x{expanded_tolerance_y:.1f}）")
                    return True, actual_icon_area
            
            return False, None
        except Exception as e:
            logging.error(f"检查鼠标是否在 {entity_type} 图标区域内失败: {e}")
            logging.error(traceback.format_exc())
            return False, None
    
    def _build_icon_area_from_cursor(self, cursor_x, cursor_y, entity_type='monster'):
        """
        根据鼠标位置构建图标区域
        
        Args:
            cursor_x, cursor_y: 鼠标坐标（屏幕绝对坐标）
            entity_type: 'monster' 或 'item'
        
        Returns:
            dict: 图标区域的实际坐标（包含min_x, max_x, min_y, max_y），或 None
        """
        if not self.position_config:
            return None
        
        try:
            icon_data = self.position_config.get(entity_type, {}).get('icon', {})
            if not icon_data:
                return None
            
            # 获取参考坐标（从配置文件）
            ref_tl = (icon_data['top_left']['x'], icon_data['top_left']['y'])
            ref_tr = (icon_data['top_right']['x'], icon_data['top_right']['y'])
            ref_bl = (icon_data['bottom_left']['x'], icon_data['bottom_left']['y'])
            ref_br = (icon_data['bottom_right']['x'], icon_data['bottom_right']['y'])
            
            # 计算参考图标的尺寸（使用最小外接矩形）
            ref_min_x = min(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_max_x = max(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_min_y = min(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            ref_max_y = max(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            
            icon_width = ref_max_x - ref_min_x
            icon_height = ref_max_y - ref_min_y
            
            # 检查图标尺寸是否有效（如果position.json中坐标都是0，则尺寸为0）
            if icon_width <= 0 or icon_height <= 0:
                logging.warning(f"[区域检测] {entity_type} 图标尺寸无效: {icon_width}x{icon_height}，将使用固定小区域")
                return None
            
            # 假设鼠标位置接近图标的左上角（或者鼠标在图标的某个固定位置）
            # 从position.json看，图标的左上角是(1144, 401)
            # 我们可以假设鼠标位置就是图标的左上角，或者鼠标在图标左上角附近
            # 更准确的方法：假设鼠标位置在图标的左上角附近（偏移一些像素，比如图标尺寸的10-20%）
            # 或者，假设鼠标位置就是图标的左上角
            
            # 方法1：假设鼠标位置就是图标的左上角（最简单，但可能不够准确）
            # icon_tl_x = cursor_x
            # icon_tl_y = cursor_y
            
            # 方法2：假设鼠标位置在图标的中心（当前方法，但可能不够准确）
            # icon_center_x = cursor_x
            # icon_center_y = cursor_y
            # icon_area = {
            #     'min_x': icon_center_x - icon_width // 2,
            #     'max_x': icon_center_x + icon_width // 2,
            #     'min_y': icon_center_y - icon_height // 2,
            #     'max_y': icon_center_y + icon_height // 2
            # }
            
            # 方法3：假设鼠标位置在图标的左上角附近（偏移图标尺寸的10-20%）
            # 这样更灵活，可以适应鼠标在图标的任何位置
            offset_factor = 0.15  # 假设鼠标在图标左上角偏移15%的位置
            icon_tl_x = cursor_x - int(icon_width * offset_factor)
            icon_tl_y = cursor_y - int(icon_height * offset_factor)
            
            # 构建图标区域（以计算出的左上角为基准）
            icon_area = {
                'min_x': icon_tl_x,
                'max_x': icon_tl_x + icon_width,
                'min_y': icon_tl_y,
                'max_y': icon_tl_y + icon_height
            }
            
            logging.info(f"[区域检测] 构建的图标区域({entity_type}): 尺寸={icon_width}x{icon_height}, 中心=({icon_center_x}, {icon_center_y})")
            return icon_area
        except Exception as e:
            logging.error(f"根据鼠标位置构建图标区域失败: {e}")
            logging.error(traceback.format_exc())
            return None
    
    def calculate_name_area_from_icon(self, icon_area, entity_type='monster'):
        """
        根据图标区域计算名称区域
        
        Args:
            icon_area: 图标区域的实际坐标（dict，包含min_x, max_x, min_y, max_y）
            entity_type: 'monster' 或 'item'
        
        Returns:
            tuple: (x1, y1, x2, y2) 名称区域的截图坐标，或 None
        """
        offset = self.monster_icon_name_offset if entity_type == 'monster' else self.item_icon_name_offset
        if not offset:
            return None
        
        try:
            # 使用图标的左上角作为基准点
            icon_tl_x = icon_area['min_x']
            icon_tl_y = icon_area['min_y']
            
            # 计算名称区域的左上角和右下角（使用平均偏移量）
            avg_x_offset_tl = offset['x_offset_tl']
            avg_y_offset_tl = offset['y_offset_tl']
            avg_x_offset_br = offset['x_offset_br']
            avg_y_offset_br = offset['y_offset_br']
            
            # 计算名称区域
            name_tl_x = icon_tl_x + avg_x_offset_tl
            name_tl_y = icon_tl_y + avg_y_offset_tl
            name_br_x = icon_area['max_x'] + avg_x_offset_br
            name_br_y = icon_area['max_y'] + avg_y_offset_br
            
            # 扩大范围，增加容差（上下左右各增加20%）
            name_width = name_br_x - name_tl_x
            name_height = name_br_y - name_tl_y
            padding_x = name_width * 0.2
            padding_y = name_height * 0.2
            
            x1 = int(name_tl_x - padding_x)
            y1 = int(name_tl_y - padding_y)
            x2 = int(name_br_x + padding_x)
            y2 = int(name_br_y + padding_y)
            
            logging.debug(f"计算出的名称区域({entity_type}): ({x1}, {y1}) -> ({x2}, {y2})")
            return (x1, y1, x2, y2)
        except Exception as e:
            logging.error(f"根据图标区域计算名称区域失败: {e}")
            return None

    def load_monster_data(self):
        """加载怪物数据"""
        try:
            # 获取数据文件路径（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                base_dir = os.path.dirname(__file__)
            
            # 优先使用新的数据源
            monster_file = os.path.join(base_dir, 'data', 'Json', 'monsters_detail.json')
            if not os.path.exists(monster_file):
                # 如果新文件不存在，尝试旧路径
                monster_file = os.path.join(base_dir, 'data', 'Json - 副本', 'monsters_detail.json')
            if not os.path.exists(monster_file):
                # 如果还是不存在，使用旧的数据源
            monster_file = os.path.join(base_dir, '6.0', 'crawlers', 'monster_details_v3', 'monsters_v3.json')
            
            with open(monster_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 新数据格式是数组，key使用中文名称
                if isinstance(data, list):
                    self.monster_data = {monster['name_zh']: monster for monster in data}
                else:
                    # 旧数据格式是字典
                self.monster_data = {monster['name']: monster for monster in data}
            logging.info(f"成功加载怪物数据，共 {len(self.monster_data)} 个怪物")
            
            # 加载物品和技能数据以获取描述信息
            self.load_items_data()
            self.load_skills_data()
        except Exception as e:
            logging.error(f"加载怪物数据失败: {e}")
            self.monster_data = {}
    
    def load_items_data(self):
        """加载物品数据"""
        try:
            if is_packaged_environment():
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(__file__)
            
            # 加载items.json（原有格式，Key为英文名称）
            items_file = os.path.join(base_dir, 'data', 'Json', 'items.json')
            if not os.path.exists(items_file):
                items_file = os.path.join(base_dir, 'data', 'Json - 副本', 'items.json')
            
            if os.path.exists(items_file):
                with open(items_file, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    self.items_data = {item['name']: item for item in items}
                logging.info(f"成功加载物品数据，共 {len(self.items_data)} 个物品")
            
            # 加载items_db.json（UUID映射格式，用于日志匹配）
            items_db_file = os.path.join(base_dir, 'data', 'Json', 'items_db.json')
            if os.path.exists(items_db_file):
                with open(items_db_file, 'r', encoding='utf-8') as f:
                    self.uuid_to_item_data = json.load(f)
                logging.info(f"成功加载UUID映射数据，共 {len(self.uuid_to_item_data)} 个物品UUID")
            else:
                logging.warning(f"未找到items_db.json文件: {items_db_file}，日志匹配功能将不可用")
                self.uuid_to_item_data = {}
        except Exception as e:
            logging.error(f"加载物品数据失败: {e}")
            self.items_data = {}
            self.uuid_to_item_data = {}
    
    def load_skills_data(self):
        """加载技能数据"""
        try:
            if is_packaged_environment():
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(__file__)
            
            skills_file = os.path.join(base_dir, 'data', 'Json', 'skills.json')
            if not os.path.exists(skills_file):
                skills_file = os.path.join(base_dir, 'data', 'Json - 副本', 'skills.json')
            
            if os.path.exists(skills_file):
                with open(skills_file, 'r', encoding='utf-8') as f:
                    skills = json.load(f)
                    self.skills_data = {skill['name']: skill for skill in skills}
                logging.info(f"成功加载技能数据，共 {len(self.skills_data)} 个技能")
        except Exception as e:
            logging.error(f"加载技能数据失败: {e}")
            self.skills_data = {}

    def load_event_data(self):
        """加载事件数据"""
        try:
            # 获取数据文件路径（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                base_dir = os.path.dirname(__file__)
            
            # 优先使用新的JSON文件路径
            event_file = os.path.join(base_dir, 'data', 'Json', 'events_from_html.json')
            if not os.path.exists(event_file):
                # 如果新文件不存在，尝试旧路径
            event_file = os.path.join(base_dir, '6.0', 'crawlers', 'event_details_final', 'events_final.json')
            
            with open(event_file, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                logging.info(f"已加载 {len(self.events)} 个事件")
            
            # 从 events_from_html.json 提取所有事件选项
            # 支持中文名称和英文名称的映射
            self.event_data = {}
            self.event_name_map = {}  # 中文名称 -> 英文名称的映射
            for event in self.events:
                if 'name' in event and 'choices' in event:
                    chinese_name = event['name']
                    english_name = event.get('name_en', '')
                    self.event_data[chinese_name] = event['choices']
                    if english_name:
                        self.event_name_map[chinese_name] = english_name
                        # 同时支持英文名称查找
                        self.event_data[english_name] = event['choices']
                else:
                    logging.warning(f"事件 {event.get('name', '')} 缺少 choices 字段")
        except Exception as e:
            logging.error(f"加载事件数据时出错: {e}")
            logging.error(traceback.format_exc())
            self.events = []
            self.event_data = {}
            self.event_name_map = {}

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        try:
            # 方法1: 通过进程名查找游戏窗口
            hwnd = self._find_window_by_process()
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                logging.info(f"通过进程名找到游戏窗口，坐标: {rect}")
                return hwnd, rect
            
            # 方法2: 尝试多种可能的游戏窗口名称
            window_names = [
                "The Bazaar",
                "The Bazaar - DirectX 11", 
                "The Bazaar - DirectX 12",
                "The Bazaar - Vulkan",
                "The Bazaar - OpenGL"
            ]
            
            hwnd = None
            found_window_name = None
            for name in window_names:
                hwnd = win32gui.FindWindow(None, name)
                if hwnd:
                    found_window_name = name
                    logging.debug(f"找到游戏窗口: {name}")
                    break
            
            # 方法3: 通过类名查找
            if not hwnd:
                hwnd = win32gui.FindWindow("UnityWndClass", None)
                if hwnd:
                    found_window_name = "UnityWndClass"
                    logging.debug(f"通过类名找到游戏窗口: UnityWndClass")
            
            # 方法4: 枚举所有窗口，寻找最大的 Bazaar 相关窗口
            if not hwnd:
                def enum_windows_callback(hwnd_test, windows):
                    if win32gui.IsWindowVisible(hwnd_test):
                        window_text = win32gui.GetWindowText(hwnd_test)
                        if "bazaar" in window_text.lower():
                            rect = win32gui.GetWindowRect(hwnd_test)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            # 记录所有找到的窗口，不管尺寸
                            windows.append((hwnd_test, window_text, rect, width, height))
                            logging.debug(f"找到候选窗口: {window_text}, 尺寸: {width}x{height}, 坐标: {rect}")
                    return True
                
                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                # 记录所有找到的窗口用于调试
                logging.info(f"找到的所有 Bazaar 相关窗口:")
                for h, t, r, w, h_val in windows:
                    logging.info(f"  - {t}: {w}x{h_val} at {r}")
                
                # 过滤出尺寸合理的窗口
                valid_windows = [(h, t, r, w, h_val) for h, t, r, w, h_val in windows if w > 800 and h_val > 600]
                
                if valid_windows:
                    # 选择最大的窗口
                    valid_windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                    hwnd = valid_windows[0][0]
                    found_window_name = valid_windows[0][1]
                    logging.info(f"通过枚举找到游戏窗口: {found_window_name}, 尺寸: {valid_windows[0][3]}x{valid_windows[0][4]}")
                elif windows:
                    # 如果没有尺寸合理的窗口，选择最大的
                    windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                    hwnd = windows[0][0]
                    found_window_name = windows[0][1]
                    logging.warning(f"使用最大窗口作为备选: {found_window_name}, 尺寸: {windows[0][3]}x{windows[0][4]}")
                
            if hwnd:
                try:
                    # 使用AttachThreadInput方法处理SetForegroundWindow错误
                    foreground_hwnd = win32gui.GetForegroundWindow()
                    foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
                    current_thread_id = win32api.GetCurrentThreadId()
                    
                    # 将线程输入关联起来
                    if foreground_thread_id != current_thread_id:
                        win32process.AttachThreadInput(foreground_thread_id, current_thread_id, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32process.AttachThreadInput(foreground_thread_id, current_thread_id, False)
                    else:
                        win32gui.SetForegroundWindow(hwnd)
                except Exception as e:
                    # 如果设置前台窗口失败，记录错误但继续
                    logging.warning(f"设置游戏窗口为前台失败: {e}")
                    # 保持静默，不影响正常功能
                    pass
                
                rect = win32gui.GetWindowRect(hwnd)
                # 检查窗口状态
                is_minimized = win32gui.IsIconic(hwnd)
                is_visible = win32gui.IsWindowVisible(hwnd)
                logging.info(f"找到游戏窗口: {found_window_name}, 坐标: {rect}")
                logging.info(f"窗口状态 - 最小化: {is_minimized}, 可见: {is_visible}")
                
                # 如果窗口太小，尝试获取客户端区域
                if rect[2] - rect[0] < 200 or rect[3] - rect[1] < 100:
                    try:
                        client_rect = win32gui.GetClientRect(hwnd)
                        client_width = client_rect[2]
                        client_height = client_rect[3]
                        logging.info(f"客户端区域尺寸: {client_width}x{client_height}")
                        
                        if client_width > 800 and client_height > 600:
                            # 使用客户端坐标重新计算窗口坐标
                            point = win32gui.ClientToScreen(hwnd, (0, 0))
                            rect = (point[0], point[1], point[0] + client_width, point[1] + client_height)
                            logging.info(f"使用客户端坐标: {rect}")
                    except Exception as e:
                        logging.warning(f"获取客户端坐标失败: {e}")
                
                return hwnd, rect
                
            logging.warning("未找到游戏窗口")
            # 调试：列出所有窗口
            self.debug_list_windows()
            return None, None
        except Exception as e:
            logging.error(f"获取游戏窗口失败: {e}")
            return None, None
    
    def _find_window_by_process(self):
        """通过进程名查找游戏窗口"""
        try:
            # 查找 Bazaar_Lens.exe 或 The Bazaar.exe 进程
            process_names = ["Bazaar_Lens.exe", "The Bazaar.exe", "TheBazaar.exe"]
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.name()
                    if any(name.lower() in proc_name.lower() for name in process_names):
                        pid = proc.pid
                        logging.info(f"找到游戏进程: {proc_name} (PID: {pid})")
                        
                        # 通过进程ID查找对应的窗口
                        def enum_windows_callback(hwnd, windows):
                            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                            if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                                window_text = win32gui.GetWindowText(hwnd)
                                if window_text:  # 只选择有标题的窗口
                                    rect = win32gui.GetWindowRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]
                                    windows.append((hwnd, window_text, rect, width, height))
                            return True
                        
                        windows = []
                        win32gui.EnumWindows(enum_windows_callback, windows)
                        
                        if windows:
                            # 选择最大的窗口
                            windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                            best_window = windows[0]
                            logging.info(f"通过进程找到窗口: {best_window[1]}, 尺寸: {best_window[3]}x{best_window[4]}")
                            return best_window[0]
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return None
        except Exception as e:
            logging.error(f"通过进程查找窗口失败: {e}")
            return None
    
    def debug_list_windows(self):
        """调试：列出所有窗口"""
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if window_text:
                        rect = win32gui.GetWindowRect(hwnd)
                        width = rect[2] - rect[0]
                        height = rect[3] - rect[1]
                        # 获取窗口类名
                        class_name = win32gui.GetClassName(hwnd)
                        windows.append((hwnd, window_text, width, height, rect, class_name))
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # 过滤出可能的游戏窗口
            game_windows = []
            for hwnd, text, width, height, rect, class_name in windows:
                if ("bazaar" in text.lower() or "the" in text.lower() or class_name == "UnityWndClass") and width > 100 and height > 100:
                    game_windows.append((text, width, height, rect, class_name))
            
            logging.info(f"找到所有可能的游戏窗口:")
            for text, width, height, rect, class_name in game_windows:
                logging.info(f"  - 标题: '{text}', 类名: '{class_name}', 尺寸: {width}x{height}, 坐标: {rect}")
                
                # 尝试获取客户端区域
                try:
                    client_rect = win32gui.GetClientRect(hwnd)
                    client_width = client_rect[2]
                    client_height = client_rect[3]
                    logging.info(f"    客户端区域: {client_width}x{client_height}")
                except:
                    logging.info(f"    无法获取客户端区域")
            
            if not game_windows:
                logging.info("未找到合适的游戏窗口")
                
        except Exception as e:
            logging.error(f"调试列出窗口失败: {e}")

    def preprocess_image(self, img):
        """图像预处理优化，提高OCR识别质量"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # 简单预处理：CLAHE增强对比度 + OTSU二值化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 放大图像以提高OCR准确性
            height, width = binary.shape
            if width < 400 or height < 200:
                scale = max(400 / width, 200 / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                binary = cv2.resize(binary, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            return binary
            
        except Exception as e:
            logging.error(f"图像预处理失败: {e}")
            logging.error(traceback.format_exc())
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                return binary
            except:
            return img

    def get_game_tesseract_config(self, mode='balanced'):
        """
        游戏专用Tesseract配置 - 基于测试结果优化
        
        测试结果显示：PSM 11 + OEM 1 效果最好
        - 原始图像：匹配次数最多（42次），平均分数0.42
        - 去噪+增强：分数最高（0.44），但速度较慢
        
        mode: 'fast' - 最快速度（原始图像+PSM11+OEM1）
              'balanced' - 平衡模式（原始图像+PSM11+OEM1，推荐）
              'accurate' - 最高准确率（去噪+增强+PSM11+OEM1，稍慢）
        """
        configs = {
            'fast': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            },
            'balanced': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            },
            'accurate': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            }
        }
        return configs.get(mode, configs['balanced'])
    
    def _clean_ocr_text(self, text):
        """清理OCR结果，移除明显错误的字符"""
        if not text:
            return ""
        
        # 1. 移除游戏文本中不常见的特殊字符
        text = re.sub(r'[{}[\]()<>`~!@#$%^&*_+=;:"\',.?\\|]', '', text)
        
        # 2. 合并过多的空格
        text = re.sub(r'\s{2,}', ' ', text)
        
        # 3. 移除首尾空白
        text = text.strip()
        
        # 4. 移除纯数字的短行（通常是游戏UI的干扰）
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # 如果整行都是数字且长度短，可能是干扰
                if len(line) < 4 and line.isdigit():
                    continue
                # 如果行太长（超过40字符），可能是识别错误，截断
                if len(line) > 40:
                    line = line[:40] + "..."
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def ocr_for_game(self, img_array, mode='balanced', region_type='monster', use_preprocess=False):
        """
        游戏专用OCR - 使用平衡模式+无预处理（最佳效果）
        """
        try:
            # 根据区域类型选择模式
            if region_type == 'monster':
                # 怪物名称通常较短，但用户反馈平衡模式更好
                mode = 'balanced'
            else:
                # 事件描述可能较长，用balanced模式
                mode = 'balanced'
            
            config = self.get_game_tesseract_config(mode)
            
            # 直接识别，不预处理（用户反馈无预处理效果最好）
            if isinstance(img_array, np.ndarray):
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    pil_img = Image.fromarray(img_array)
                elif len(img_array.shape) == 2:
                    pil_img = Image.fromarray(img_array)
                else:
                    pil_img = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
            else:
                pil_img = img_array
            
            # 执行OCR
            start_time = time.time()
            text = pytesseract.image_to_string(
                pil_img,
                lang='chi_sim',
                config=config['config']
            )
            ocr_time = time.time() - start_time
            
            # 清理结果
            text = self._clean_ocr_text(text)
            
            if text:
                logging.info(f"[游戏OCR] 模式={mode}, 预处理={use_preprocess}, 耗时={ocr_time:.3f}s, 结果={repr(text[:100])}")
            
            return text
            
        except Exception as e:
            logging.error(f"游戏OCR失败: {e}")
            logging.error(traceback.format_exc())
            return None
    
    def _fuzzy_compare(self, text1, text2):
        """
        改进的模糊比较 - 专为游戏OCR设计
        允许：缺字、多字、错字、顺序错乱
        """
        if not text1 or not text2:
            return 0
        
        # 1. 移除所有空格和特殊字符
        text1_clean = re.sub(r'\s+', '', text1)
        text2_clean = re.sub(r'\s+', '', text2)
        
        # 2. 如果其中一个太短，直接返回简单比例
        if len(text1_clean) <= 3 or len(text2_clean) <= 3:
            # 检查是否包含关系
            if text1_clean in text2_clean or text2_clean in text1_clean:
                return 0.8
            return 0
        
        # 3. 字符级别的匹配
        chars1 = set(text1_clean)
        chars2 = set(text2_clean)
        common_chars = chars1.intersection(chars2)
        
        # 字符匹配度
        char_score = len(common_chars) / max(len(chars1), len(chars2)) if max(len(chars1), len(chars2)) > 0 else 0
        
        # 4. 顺序相似度（考虑OCR可能识别错顺序）
        seq_score = difflib.SequenceMatcher(None, text1_clean, text2_clean).ratio()
        
        # 5. 最终分数 = 字符匹配度 * 0.4 + 顺序相似度 * 0.6
        final_score = char_score * 0.4 + seq_score * 0.6
        
        # 6. 如果文字长度差异大，惩罚
        len_ratio = min(len(text1_clean), len(text2_clean)) / max(len(text1_clean), len(text2_clean)) if max(len(text1_clean), len(text2_clean)) > 0 else 0
        final_score *= len_ratio
        
        return final_score
    
    def fuzzy_match_game_text(self, ocr_text, threshold=0.3):
        """
        高容错模糊匹配 - 允许部分字符错误
        
        threshold: 相似度阈值，越低越容易匹配
        推荐设置：
          - 短文本（2-4字）: 0.5-0.6
          - 中文本（5-8字）: 0.3-0.4
          - 长文本（8+字）: 0.2-0.3
        """
        if not ocr_text or len(ocr_text.strip()) < 2:
            return None, None
        
        ocr_text = ocr_text.strip()
        best_match = None
        best_score = 0
        best_type = None
        
        # 根据文本长度动态调整阈值
        text_len = len(ocr_text)
        if text_len <= 4:
            threshold = max(threshold, 0.5)
        elif text_len <= 8:
            threshold = max(threshold, 0.3)
        else:
            threshold = max(threshold, 0.2)
        
        # 尝试匹配怪物
        for monster_name in self.monster_data:
            score = self._fuzzy_compare(ocr_text, monster_name)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = monster_name
                best_type = 'monster'
        
        # 如果怪物匹配失败，尝试事件
        if best_score < threshold:
            for event_name in self.event_data:
                score = self._fuzzy_compare(ocr_text, event_name)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = event_name
                    best_type = 'event'
        
        logging.info(f"[模糊匹配] OCR: {repr(ocr_text)}, 匹配: {best_type}={best_match}, 分数: {best_score:.2f}")
        
        if best_score >= threshold:
            return best_type, best_match
        return None, None
    
    def count_chinese_chars(self, text):
        """统计文本中的中文字符数量"""
        if not text:
            return 0
        return sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    
    def ocr_with_timeout(self, processed_img, timeout=3, psm=0):
        """使用超时机制执行OCR，仅使用PaddleOCR（psm参数保留以兼容调用，但PaddleOCR不使用）"""
        # 使用线程锁防止并发调用
        if not self.ocr_lock.acquire(blocking=False):
            logging.warning("[OCR] OCR已在进行中，跳过本次识别（可能因为上次OCR未完成）")
            return None
            
        try:
            # 检查PaddleOCR是否可用
            if not self.paddle_ocr:
                logging.error("[OCR] PaddleOCR未初始化，无法进行OCR识别")
                return None
            
            # 准备图像数据
            buf = io.BytesIO()
            Image.fromarray(processed_img).save(buf, format='PNG')
            img_bytes = buf.getvalue()
            
            # 统一使用线程超时策略，避免打包环境的同步阻塞问题
            # 初始化结果变量和事件
            result = [None]  # 使用列表存储结果，便于线程间共享
            ocr_done = threading.Event()
            
            # 定义OCR线程
            def ocr_thread():
                try:
                    # 直接在线程中执行OCR，仅使用PaddleOCR
                    ocr_result = direct_ocr(img_bytes, psm=psm, paddle_ocr=self.paddle_ocr)
                    result[0] = ocr_result
                    ocr_done.set()
                except Exception as e:
                    logging.error(f"OCR线程异常: {e}")
                    logging.error(traceback.format_exc())
                    ocr_done.set()
            
            # 启动OCR线程
            thread = threading.Thread(target=ocr_thread, daemon=True)
            thread.start()
            
            # 等待OCR完成或超时
            if ocr_done.wait(timeout=timeout):
                return result[0]
            else:
                logging.warning("OCR识别超时，已跳过本次识别")
                # 超时但不终止线程，让它在后台继续运行
                return None
                
        except Exception as e:
            logging.error(f"OCR处理异常: {e}")
            logging.error(traceback.format_exc())
            return None
        finally:
            # 确保释放锁
            self.ocr_lock.release()
    
    def ocr_with_timeout_raw(self, img_bytes, timeout=10):
        """使用超时机制执行OCR，直接使用图像字节（用于PaddleOCR）"""
        # 使用线程锁防止并发调用
        if not self.ocr_lock.acquire(blocking=False):
            logging.warning("[OCR] OCR已在进行中，跳过本次识别（可能因为上次OCR未完成）")
            return None
            
        try:
            # 检查PaddleOCR是否可用
            if not self.paddle_ocr:
                logging.error("[OCR] PaddleOCR未初始化，无法进行OCR识别")
                return None
            
            # 统一使用线程超时策略，避免打包环境的同步阻塞问题
            # 初始化结果变量和事件
            result = [None]  # 使用列表存储结果，便于线程间共享
            ocr_done = threading.Event()
            
            # 定义OCR线程
            def ocr_thread():
                try:
                    # 直接在线程中执行OCR，仅使用PaddleOCR
                    ocr_result = direct_ocr(img_bytes, psm=0, paddle_ocr=self.paddle_ocr)
                    result[0] = ocr_result
                    ocr_done.set()
                except Exception as e:
                    logging.error(f"OCR线程异常: {e}")
                    logging.error(traceback.format_exc())
                    ocr_done.set()
            
            # 启动OCR线程
            thread = threading.Thread(target=ocr_thread, daemon=True)
            thread.start()
            
            # 等待OCR完成或超时
            if ocr_done.wait(timeout=timeout):
                return result[0]
            else:
                logging.warning("OCR识别超时，已跳过本次识别")
                # 超时但不终止线程，让它在后台继续运行
                return None
                
        except Exception as e:
            logging.error(f"OCR处理异常: {e}")
            logging.error(traceback.format_exc())
            return None
        finally:
            # 确保释放锁
            self.ocr_lock.release()

    def find_best_match(self, text):
        """统一识别怪物或事件，返回('monster'/'event', 名称)或(None, None)"""
        if not text:
            return None, None
        
        # 检查匹配结果缓存（基于OCR文本）
        text_key = text.strip()[:100]  # 使用前100个字符作为key
        if text_key in self.match_cache:
            logging.debug("使用匹配结果缓存")
            return self.match_cache[text_key]
            
        def clean_text(s):
            """清理英文文本：保留字母和空格"""
            if not isinstance(s, str):
                return ""
            # 保留字母和空格，移除其他字符
            s = re.sub(r'[^a-zA-Z\s]', ' ', s)
            # 合并多个空格为单个空格并转小写
            return ' '.join(s.split()).lower()
            
        def clean_text_chinese(s):
            """清理中文文本：保留中文字符、字母、数字和空格"""
            if not isinstance(s, str):
                return ""
            # 保留中文字符、字母、数字和空格
            s = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', s)
            # 合并多个空格为单个空格
            return ' '.join(s.split())
        
        def clean_text_chinese_no_space(s):
            """清理中文文本：移除所有空格，只保留中文字符、字母、数字"""
            if not isinstance(s, str):
                return ""
            # 保留中文字符、字母、数字，移除所有空格和其他字符
            s = re.sub(r'[^\u4e00-\u9fff\w]', '', s)
            return s
        
        def clean_text_chinese_only(s):
            """清理文本：只保留纯中文字符，排除所有数字、字母、标点等"""
            if not isinstance(s, str):
                return ""
            # 只保留中文字符（\u4e00-\u9fff），排除所有其他字符（包括数字0-9、字母、标点等）
            s = re.sub(r'[^\u4e00-\u9fff]', '', s)
            return s
        
        def extract_name_candidates(line):
            """从OCR文本中提取可能的名称候选（过滤无关词，优化：优先从开头提取、优先长词）"""
            if not line:
                return []
            
            # 常见无关词（游戏UI中常见的词，但不是怪物/事件名称）
            # 注意：不包含数字字符（'二'、'三'、'四'、'五'、'六'等），因为这些可能是合法名称的一部分（如"三明治艺术家"）
            common_noise_words = {
                '奖励', '人', '全', '合', '使', '倒', '含', '和', '由', '国', '蕊', 
                '本', '上', '站', '机', '作', '区'
            }
            
            # 关键优化：如果包含"奖励"，只保留"奖励"之前的内容
            # 因为所有怪物都有"奖励"两个字，这是奖励部分的标识
            if '奖励' in line:
                reward_index = line.find('奖励')
                if reward_index > 0:
                    line = line[:reward_index].strip()
                elif reward_index == 0:
                    # 如果"奖励"在开头，说明没有名称，返回空
                    return []
            
            # 只保留纯中文字符（排除所有数字、字母、标点等）
            clean_zh_only = clean_text_chinese_only(line)
            
            # 如果清理后没有内容，返回空
            if not clean_zh_only or len(clean_zh_only) < 2:
                return []
            
            candidates = []
            
            # 优化策略：优先从开头提取，优先长词，同时提取包含关键词的候选
            # 策略1：从开头提取2-8个连续字符（最可能匹配）
            for length in range(min(8, len(clean_zh_only)), 1, -1):  # 从长到短
                candidate = clean_zh_only[:length]
                # 过滤掉只包含无关词的候选
                if not all(c in common_noise_words for c in candidate):
                    candidates.append(candidate)
            
            # 策略2：提取包含关键词的长候选（用于事件名称，如"朱尔斯的咖啡店"）
            # 关键词列表（常见的事件/物品名称中的关键词）
            keywords = ['的', '咖啡', '店', '朱尔斯', '失落', '宝箱', '事件', '物品']
            for keyword in keywords:
                if keyword in clean_zh_only:
                    keyword_index = clean_zh_only.find(keyword)
                    # 从关键词前后提取候选（优先长词）
                    # 向前提取（包含关键词）
                    for start in range(max(0, keyword_index - 6), keyword_index + 1):
                        for length in range(min(10, len(clean_zh_only) - start), len(keyword), -1):
                            if start + length <= len(clean_zh_only):
                                candidate = clean_zh_only[start:start+length]
                                if keyword in candidate and len(candidate) >= 3:
                                    if not all(c in common_noise_words for c in candidate):
                                        if candidate not in candidates:
                                            candidates.append(candidate)
            
            # 策略3：如果从开头提取的候选不足，再从其他位置提取
            if len(candidates) < 15:  # 增加候选数量限制
                for start in range(1, len(clean_zh_only)):  # 从位置1开始（位置0已在策略1中处理）
                    for length in range(min(8, len(clean_zh_only) - start), 1, -1):  # 从长到短
                        candidate = clean_zh_only[start:start+length]
                        # 过滤掉只包含无关词的候选
                        if not all(c in common_noise_words for c in candidate):
                            if candidate not in candidates:  # 避免重复
                                candidates.append(candidate)
                                if len(candidates) >= 15:  # 增加候选数量限制
                                    break
                    if len(candidates) >= 15:
                        break
            
            # 去重并排序（优先长词，然后按位置）
            candidates = sorted(set(candidates), key=lambda x: (-len(x), x))
            
            # 限制候选数量（最多返回前15个，优先长词）
            candidates = sorted(set(candidates), key=lambda x: (-len(x), x))
            return candidates[:15]
        
        def should_debug_log(text):
            """检查是否应该输出调试日志（包含特定调试字符）"""
            debug_chars = {'血', '确', '奇', '兵'}
            return any(char in text for char in debug_chars)
            
        # 处理文本行：同时支持英文和中文
        raw_lines = [line.strip() for line in str(text).split('\n') if line.strip()]
        lines_english = []
        lines_chinese = []
        
        for line in raw_lines:
            clean_en = clean_text(line)
            clean_zh = clean_text_chinese(line)
            
            # 排除包含"奖励"的完整行（因为"奖励"及其后面的内容都不是怪物名称）
            if '奖励' in clean_zh:
                # 只提取"奖励"之前的部分
                reward_index = clean_zh.find('奖励')
                if reward_index > 0:
                    clean_zh = clean_zh[:reward_index].strip()
                elif reward_index == 0:
                    # 如果"奖励"在开头，跳过这一行
                    continue
            
            if len(clean_en) >= 3:
                lines_english.append(clean_en)
            if len(clean_zh) >= 2:  # 中文至少2个字符
                lines_chinese.append(clean_zh)
                # 调试：如果包含特定调试字符，记录详细信息（DEBUG级别）
                if should_debug_log(clean_zh):
                    logging.debug(f"[文本处理] 原始行: {repr(line)}, 清理后: {repr(clean_zh)}")
                
                # 提取名称候选并添加到匹配列表
                # 注意：传入已处理过"奖励"的clean_zh，而不是原始line
                name_candidates = extract_name_candidates(clean_zh)
                if should_debug_log(clean_zh):
                    logging.debug(f"[名称提取] 从 {repr(clean_zh)} 提取的候选: {name_candidates[:5]}")
                for candidate in name_candidates:
                    if candidate not in lines_chinese:  # 避免重复
                        lines_chinese.append(candidate)
                        if should_debug_log(candidate):
                            logging.debug(f"[名称提取] 添加候选: {repr(candidate)}")
        
        # 记录OCR文本行用于调试（DEBUG级别）
        if lines_english or lines_chinese:
            logging.debug(f"[匹配调试] OCR文本行(英文): {lines_english[:5]}")
            logging.debug(f"[匹配调试] OCR文本行(中文): {lines_chinese[:10]}")  # 显示更多候选名称
        
        best_type = None
        best_name = None
        best_ratio = 0.0
        
        # 记录所有匹配结果用于调试
        all_matches = []
        
        # 优化：先匹配事件，再匹配怪物（事件名称通常更长更具体，优先级更高）
        # 匹配事件（同时支持英文和中文）
        # 优化：先做快速匹配（完全匹配和部分匹配），再做慢速匹配（相似度）
        logging.debug(f"[匹配调试] 开始匹配事件，共有 {len(self.events)} 个事件，{len(lines_chinese)} 行中文文本")
        for event in self.events:
            event_name_zh = event.get('name', '')  # 中文名称
            event_name_en = event.get('name_en', '')  # 英文名称
            
            # 先尝试中文匹配（快速路径）
            if event_name_zh:
                # 只使用纯中文字符进行匹配（排除所有数字、字母、标点等）
                event_clean_zh_only = clean_text_chinese_only(event_name_zh)
                
                for line in lines_chinese:
                    line_clean_only = clean_text_chinese_only(line)
                    
                    # 调试日志：记录关键匹配尝试（已为DEBUG级别，无需修改）
                    if '失落' in event_name_zh or '宝箱' in event_name_zh or '咖啡' in event_name_zh or '朱尔斯' in event_name_zh:
                        logging.debug(f"[匹配调试] 尝试匹配事件: {event_name_zh} (清理后: {event_clean_zh_only}) vs OCR行: {line} (清理后: {line_clean_only})")
                    
                    # 快速匹配1：完全匹配（纯中文字符）- 最快，立即返回并缓存
                    if line_clean_only == event_clean_zh_only and len(line_clean_only) >= 2:
                        logging.info(f"找到完全匹配的事件(中文): {event_name_zh}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2：部分匹配：检查事件名称是否包含在OCR文本中
                    if event_clean_zh_only in line_clean_only and len(event_clean_zh_only) >= 2:
                        logging.info(f"找到部分匹配的事件(事件名在OCR文本中): {event_name_zh}, OCR行: {line}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2.5：反向部分匹配：检查OCR文本是否包含在事件名称中（降低阈值）
                    if len(line_clean_only) >= 2 and line_clean_only in event_clean_zh_only:
                        ratio = len(line_clean_only) / len(event_clean_zh_only) if event_clean_zh_only else 0
                        if ratio > 0.5:  # 降低阈值到50%
                            logging.info(f"找到部分匹配的事件(OCR文本在事件名中): {event_name_zh}, OCR行: {line}, 匹配度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    
                    # 改进的匹配：检查关键字符匹配（提高容错性）
                    # 提取事件名称的关键字符（至少2个连续字符）
                    if len(event_clean_zh_only) >= 2 and len(line_clean_only) >= 2:
                        # 计算字符匹配度
                        matched_chars = sum(1 for c in event_clean_zh_only if c in line_clean_only)
                        match_ratio = matched_chars / len(event_clean_zh_only) if event_clean_zh_only else 0
                        
                        # 对于长事件名称（5+字符），降低字符匹配阈值
                        if len(event_clean_zh_only) >= 5:
                            # 长事件名称：至少匹配60%的字符
                            if match_ratio >= 0.6:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.3:  # 降低相似度要求
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                        # 降低阈值：对于4字符的事件名称，至少匹配3个字符（75%）或2个字符（50%）
                        elif len(event_clean_zh_only) == 4:
                            # 4字符名称（如"失落宝箱"）：至少匹配3个字符（75%）或2个字符且相似度>0.4
                            if match_ratio >= 0.75:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.3:  # 降低相似度要求
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                            elif match_ratio >= 0.5:  # 至少2个字符匹配
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.4:  # 相似度要求稍高
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                        elif match_ratio > 0.5:  # 其他长度的事件名称，至少50%的字符匹配
                            logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}")
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    # 慢速匹配：相似度匹配（只在快速匹配失败时进行）
                    if len(line_clean_only) >= 2:  # 降低到至少2个字符
                        ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                        if ratio > 0.5:  # 降低阈值到0.5以提高容错性
                            logging.info(f"找到相似匹配的事件: {event_name_zh}, OCR行: {line}, 相似度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                        elif ratio > 0.3:  # 中等相似度，记录但不立即返回（降低阈值）
                            all_matches.append({
                                'type': 'event',
                                'name': event_name_zh,
                                'line': line,
                                'ratio': ratio,
                                'common_words': []
                            })
                            if ratio > best_ratio:
                                logging.debug(f"[最佳匹配更新] 事件: {event_name_zh}, 相似度: {ratio:.2f} > 当前最佳: {best_ratio:.2f}")
                                best_ratio = ratio
                                best_type = 'event'
                                best_name = event_name_zh
            
            # 再尝试英文匹配 - 优化：提前退出完全匹配
            if event_name_en:
                event_clean_en = clean_text(event_name_en)
                for line in lines_english:
                    # 完全匹配 - 立即返回
                    if line == event_clean_en:
                        logging.info(f"找到完全匹配的事件(英文): {event_name_en}")
                        result = ('event', event_name_zh)  # 返回中文名称
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 包含匹配（检查单词级别的匹配）
                    event_words = set(event_clean_en.split())
                    line_words = set(line.split())
                    common_words = event_words & line_words
                    
                    if len(common_words) > 0:
                        ratio = difflib.SequenceMatcher(None, line, event_clean_en).ratio()
                        all_matches.append({
                            'type': 'event',
                            'name': event_name_zh,
                            'line': line,
                            'ratio': ratio,
                            'common_words': list(common_words)
                        })
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_type = 'event'
                            best_name = event_name_zh
        
        # 匹配怪物（优先使用中文，因为新数据源使用中文名称作为key）
        for monster_name in self.monster_data:
            monster_info = self.monster_data[monster_name]
            monster_name_en = monster_info.get('name', '') if isinstance(monster_info, dict) else ''
            
            # 先尝试中文匹配（新数据源使用中文名称作为key）
            # 只使用纯中文字符进行匹配（排除所有数字、字母、标点等）
            monster_clean_zh_only = clean_text_chinese_only(monster_name)
            
            # 提取怪物名称的关键字符（用于字符级别匹配）
            monster_chars = set(monster_clean_zh_only)
            
            for line in lines_chinese:
                # 只使用纯中文字符进行匹配
                line_clean_zh_only = clean_text_chinese_only(line)
                
                # 完全匹配（纯中文字符）
                if line_clean_zh_only == monster_clean_zh_only and len(line_clean_zh_only) >= 2:
                    logging.info(f"找到完全匹配的怪物(中文): {monster_name}")
                    result = ('monster', monster_name)
                    if len(self.match_cache) >= self.match_cache_max_size:
                        oldest_key = next(iter(self.match_cache))
                        del self.match_cache[oldest_key]
                    self.match_cache[text_key] = result
                    return result
                
                # 部分匹配：怪物名称在OCR文本中（降低阈值到0.5）
                if monster_clean_zh_only in line_clean_zh_only and len(monster_clean_zh_only) >= 2:
                    ratio = len(monster_clean_zh_only) / len(line_clean_zh_only) if line_clean_zh_only else 0
                    if ratio > 0.5:  # 降低阈值
                        logging.info(f"找到部分匹配的怪物(中文): {monster_name}, 匹配度: {ratio:.2f}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                
                # 部分匹配：OCR文本在怪物名称中（降低阈值到0.5）
                if line_clean_zh_only in monster_clean_zh_only and len(line_clean_zh_only) >= 2:
                    ratio = len(line_clean_zh_only) / len(monster_clean_zh_only) if monster_clean_zh_only else 0
                    if ratio > 0.5:  # 降低阈值
                        logging.info(f"找到部分匹配的怪物(中文): {monster_name}, 匹配度: {ratio:.2f}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                
                # 字符级别匹配：检查关键字符是否都在OCR文本中
                if len(monster_chars) >= 2 and len(line_clean_zh_only) >= 2:
                    line_chars = set(line_clean_zh_only)
                    matched_chars = monster_chars & line_chars
                    char_match_ratio = len(matched_chars) / len(monster_chars) if monster_chars else 0
                    
                    # 根据名称长度调整字符匹配阈值
                    # 短名称（2-3字符）：需要较高匹配度（60%）
                    # 中等名称（4字符）：需要中等匹配度（50%）
                    # 长名称（5+字符）：需要较低匹配度（40%），但至少匹配2个字符
                    monster_name_len = len(monster_clean_zh_only)
                    if monster_name_len == 2:
                        # 2字符名称：降低字符匹配要求，只要匹配1个字符即可（50%），因为OCR容易识别错误
                        required_char_ratio = 0.5  # 从0.6降低到0.5
                        min_matched_chars = 1      # 从2降低到1
                    elif monster_name_len == 3:
                        required_char_ratio = 0.6
                        min_matched_chars = 2
                    elif monster_name_len == 4:
                        required_char_ratio = 0.5
                        min_matched_chars = 2
                    else:  # 5+ 字符
                        required_char_ratio = 0.4
                        min_matched_chars = max(2, int(monster_name_len * 0.4))  # 至少40%的字符
                    
                    # 如果匹配了足够的字符
                    if char_match_ratio >= required_char_ratio and len(matched_chars) >= min_matched_chars:
                        # 进一步检查相似度（对于长名称，降低相似度要求）
                        ratio = difflib.SequenceMatcher(None, line_clean_zh_only, monster_clean_zh_only).ratio()
                        # 长名称（5+字符）的相似度阈值更低
                        similarity_threshold = 0.30 if monster_name_len >= 5 else 0.35
                        
                        # 调试日志：对于特定调试字符相关的匹配，记录详细信息（DEBUG级别）
                        if should_debug_log(monster_clean_zh_only) and should_debug_log(line_clean_zh_only):
                            logging.debug(f"[字符匹配调试] {monster_name}({monster_clean_zh_only}) vs OCR({line_clean_zh_only}): 字符匹配度={char_match_ratio:.2f}, 相似度={ratio:.2f}, 阈值={similarity_threshold:.2f}")
                        
                        if ratio > similarity_threshold:
                            logging.info(f"找到字符匹配的怪物(中文): {monster_name}, 字符匹配度: {char_match_ratio:.2f}, 相似度: {ratio:.2f}, 名称长度: {monster_name_len}")
                            result = ('monster', monster_name)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                
                # 模糊匹配（根据名称长度调整阈值）
                if len(line_clean_zh_only) >= 2:  # 至少2个字符
                    ratio = difflib.SequenceMatcher(None, line_clean_zh_only, monster_clean_zh_only).ratio()
                    monster_name_len = len(monster_clean_zh_only)
                    
                    # 根据名称长度调整相似度阈值
                    if monster_name_len <= 2:
                        # 2字符名称：进一步降低阈值，提高容错性（因为OCR容易识别错误，如"毒蛇"）
                        immediate_threshold = 0.35  # 从0.40降低到0.35，进一步提高"毒蛇"识别率
                        candidate_threshold = 0.20   # 从0.25降低到0.20
                    elif monster_name_len == 3:
                        # 3字符名称：需要较高相似度
                        immediate_threshold = 0.5
                        candidate_threshold = 0.35
                    elif monster_name_len == 4:
                        # 中等名称：中等相似度（降低阈值，因为OCR可能识别错误）
                        immediate_threshold = 0.40  # 从0.45降低到0.40
                        candidate_threshold = 0.30
                    else:  # 5+ 字符
                        # 长名称：较低相似度即可
                        immediate_threshold = 0.40
                        candidate_threshold = 0.30
                    
                    # 调试日志：对于特定调试字符相关的匹配，记录详细信息（DEBUG级别）
                    if should_debug_log(monster_clean_zh_only) and should_debug_log(line_clean_zh_only):
                        logging.debug(f"[匹配调试] {monster_name}({monster_clean_zh_only}) vs OCR({line_clean_zh_only}): 相似度={ratio:.2f}, 阈值={immediate_threshold:.2f}, 候选阈值={candidate_threshold:.2f}")
                    
                    if ratio > immediate_threshold:
                        logging.info(f"找到相似匹配的怪物(中文): {monster_name}, 相似度: {ratio:.2f}, 名称长度: {monster_name_len}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    elif ratio > candidate_threshold:  # 候选匹配
                        all_matches.append({
                            'type': 'monster',
                            'name': monster_name,
                            'line': line,
                            'ratio': ratio,
                            'common_words': []
                        })
                        if ratio > best_ratio:
                            logging.debug(f"[最佳匹配更新] 怪物: {monster_name}, 相似度: {ratio:.2f} > 当前最佳: {best_ratio:.2f}")
                            best_ratio = ratio
                            best_type = 'monster'
                            best_name = monster_name
            
            # 再尝试英文匹配（兼容旧数据源）
            if monster_name_en:
                monster_clean_en = clean_text(monster_name_en)
                for line in lines_english:
                # 完全匹配
                    if line == monster_clean_en:
                        logging.info(f"找到完全匹配的怪物(英文): {monster_name_en}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                # 包含匹配（检查单词级别的匹配）
                    monster_words = set(monster_clean_en.split())
                line_words = set(line.split())
                common_words = monster_words & line_words
                
                if len(common_words) > 0:
                    # 如果有共同单词，计算相似度
                    ratio = difflib.SequenceMatcher(None, line, monster_clean_en).ratio()
                    all_matches.append({
                        'type': 'monster',
                        'name': monster_name,
                        'line': line,
                        'ratio': ratio,
                        'common_words': list(common_words)
                    })
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_type = 'monster'
                        best_name = monster_name
                        
        # 事件匹配已移到前面，这里不再重复匹配
        for event in self.events:
            event_name_zh = event.get('name', '')  # 中文名称
            event_name_en = event.get('name_en', '')  # 英文名称
            
            # 先尝试中文匹配（快速路径）
            if event_name_zh:
                # 只使用纯中文字符进行匹配（排除所有数字、字母、标点等）
                event_clean_zh_only = clean_text_chinese_only(event_name_zh)
                
                for line in lines_chinese:
                    line_clean_only = clean_text_chinese_only(line)
                    
                    # 调试日志：记录关键匹配尝试（已为DEBUG级别，无需修改）
                    if '失落' in event_name_zh or '宝箱' in event_name_zh:
                        logging.debug(f"[匹配调试] 尝试匹配事件: {event_name_zh} (清理后: {event_clean_zh_only}) vs OCR行: {line} (清理后: {line_clean_only})")
                    
                    # 快速匹配1：完全匹配（纯中文字符）- 最快，立即返回并缓存
                    if line_clean_only == event_clean_zh_only and len(line_clean_only) >= 2:
                        logging.info(f"找到完全匹配的事件(中文): {event_name_zh}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2：部分匹配：检查事件名称是否包含在OCR文本中
                    if event_clean_zh_only in line_clean_only and len(event_clean_zh_only) >= 2:
                        logging.info(f"找到部分匹配的事件(事件名在OCR文本中): {event_name_zh}, OCR行: {line}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2.5：反向部分匹配：检查OCR文本是否包含在事件名称中（降低阈值）
                    if len(line_clean_only) >= 2 and line_clean_only in event_clean_zh_only:
                        ratio = len(line_clean_only) / len(event_clean_zh_only) if event_clean_zh_only else 0
                        if ratio > 0.5:  # 降低阈值到50%
                            logging.info(f"找到部分匹配的事件(OCR文本在事件名中): {event_name_zh}, OCR行: {line}, 匹配度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    
                    # 改进的匹配：检查关键字符匹配（提高容错性）
                    # 提取事件名称的关键字符（至少2个连续字符）
                    if len(event_clean_zh_only) >= 2 and len(line_clean_only) >= 2:
                        # 计算字符匹配度
                        matched_chars = sum(1 for c in event_clean_zh_only if c in line_clean_only)
                        match_ratio = matched_chars / len(event_clean_zh_only) if event_clean_zh_only else 0
                        
                        # 降低阈值：对于4字符的事件名称，至少匹配3个字符（75%）或2个字符（50%）
                        if len(event_clean_zh_only) == 4:
                            # 4字符名称（如"失落宝箱"）：至少匹配3个字符（75%）或2个字符且相似度>0.4
                            if match_ratio >= 0.75:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.3:  # 降低相似度要求
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                            elif match_ratio >= 0.5:  # 至少2个字符匹配
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.4:  # 相似度要求稍高
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                        elif match_ratio > 0.5:  # 其他长度的事件名称，至少50%的字符匹配
                            logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    # 慢速匹配：相似度匹配（只在快速匹配失败时进行）
                    if len(line_clean_only) >= 2:  # 降低到至少2个字符
                        ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                        if ratio > 0.5:  # 降低阈值到0.5以提高容错性
                            logging.info(f"找到相似匹配的事件: {event_name_zh}, OCR行: {line}, 相似度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                        elif ratio > 0.3:  # 中等相似度，记录但不立即返回（降低阈值）
                            all_matches.append({
                                'type': 'event',
                                'name': event_name_zh,
                                'line': line,
                                'ratio': ratio,
                                'common_words': []
                            })
                            if ratio > best_ratio:
                                logging.debug(f"[最佳匹配更新] 事件: {event_name_zh}, 相似度: {ratio:.2f} > 当前最佳: {best_ratio:.2f}")
                                best_ratio = ratio
                                best_type = 'event'
                                best_name = event_name_zh
            
            # 再尝试英文匹配 - 优化：提前退出完全匹配
            if event_name_en:
                event_clean_en = clean_text(event_name_en)
                for line in lines_english:
                    # 完全匹配 - 立即返回
                    if line == event_clean_en:
                        logging.info(f"找到完全匹配的事件(英文): {event_name_en}")
                        result = ('event', event_name_zh)  # 返回中文名称
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 包含匹配（检查单词级别的匹配）
                    event_words = set(event_clean_en.split())
                line_words = set(line.split())
                common_words = event_words & line_words
                
                if len(common_words) > 0:
                    # 如果有共同单词，计算相似度
                    ratio = difflib.SequenceMatcher(None, line, event_clean_en).ratio()
                    all_matches.append({
                        'type': 'event',
                        'name': event_name_zh,
                        'line': line,
                        'ratio': ratio,
                        'common_words': list(common_words)
                    })
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_type = 'event'
                        best_name = event_name_zh
        
        # 输出所有匹配结果用于调试（DEBUG级别）
        if all_matches:
            logging.debug(f"[匹配调试] 找到 {len(all_matches)} 个候选匹配:")
        for match in sorted(all_matches, key=lambda x: x['ratio'], reverse=True)[:5]:
                logging.debug(f"  - {match['type']}: {match['name']}, 相似度: {match['ratio']:.2f}, OCR行: {match['line'][:30]}")
        else:
            logging.debug(f"[匹配调试] 未找到任何候选匹配（all_matches为空）")
        
        # 匹配阈值：根据匹配到的名称长度动态调整
        result = None, None
        # 根据最佳匹配的名称长度调整阈值
        # 短名称（2-3字符）：需要较高相似度（0.4），避免误匹配
        # 中等名称（4字符）：需要中等相似度（0.35）
        # 长名称（5+字符）：可以使用较低相似度（0.3）
        if best_name:
            name_len = len(clean_text_chinese_only(best_name))
            if name_len <= 3:
                threshold = 0.40  # 短名称需要较高相似度，避免误匹配
            elif name_len == 4:
                threshold = 0.35  # 中等名称
            else:
                threshold = 0.30  # 长名称可以使用较低相似度
            logging.debug(f"[最终阈值判断] 最佳匹配: {best_type} - {best_name} (名称长度: {name_len}字符, 相似度: {best_ratio:.2f}, 阈值: {threshold:.2f})")
        else:
            threshold = 0.35  # 默认阈值（中等）
            logging.debug(f"[最终阈值判断] 无最佳匹配 (best_name=None, best_ratio={best_ratio:.2f}, 默认阈值: {threshold:.2f})")
        
        if best_ratio >= threshold:
            logging.info(f"[最终阈值判断] ✅ 匹配成功: {best_type} - {best_name} (相似度: {best_ratio:.2f} >= 阈值: {threshold:.2f})")
            result = best_type, best_name
        else:
            logging.debug(f"[最终阈值判断] ❌ 匹配失败: 最佳相似度 {best_ratio:.2f} < 阈值 {threshold:.2f} (最佳名称: {best_name})")
        
        # 缓存匹配结果（限制缓存大小）
        if len(self.match_cache) >= self.match_cache_max_size:
            # 删除最旧的缓存项（FIFO）
            oldest_key = next(iter(self.match_cache))
            del self.match_cache[oldest_key]
        self.match_cache[text_key] = result
        
        return result

    def get_text_at_cursor(self, region_type='monster'):
        """
        获取鼠标指向位置的文字
        
        Args:
            region_type: 'monster' 或 'item'
                - 'monster': 怪物/事件，优先使用动态计算的名称区域
                - 'item': 物品，优先使用动态计算的名称区域
        """
        try:
            # 获取游戏窗口
            hwnd, window_rect = self.get_game_window()
            if not hwnd or not window_rect:
                logging.warning("未找到游戏窗口")
                return None

            # 获取鼠标位置
            cursor_x, cursor_y = win32gui.GetCursorPos()
            
            # 检查窗口坐标有效性
            if len(window_rect) != 4 or window_rect[0] >= window_rect[2] or window_rect[1] >= window_rect[3]:
                logging.error(f"无效的游戏窗口坐标: {window_rect}")
                # 使用备用方案：根据类型选择不同的小区域
                return self._get_text_with_small_area(cursor_x, cursor_y, region_type)
            
            # 临时测试：直接使用鼠标右侧的固定区域，不进行相对位置计算
            # 这样可以测试是否是相对位置计算的问题导致成功率低
            if region_type == 'monster':
                # 怪物/事件：名称在鼠标右侧
                # 优化：缩小识别区域，减少背景干扰
                # 水平范围：从鼠标位置向右延伸，但限制最大宽度，避免包含过多背景
                max_horizontal_width = 800  # 最大水平宽度，减少背景干扰
                x1 = cursor_x  # 鼠标位置作为左边界
                x2 = min(window_rect[2], cursor_x + max_horizontal_width)  # 限制右边界，不超过窗口边界
                
                # 垂直范围：根据鼠标位置动态调整，但缩小范围以减少干扰
                window_height = window_rect[3] - window_rect[1]
                relative_y = cursor_y - window_rect[1]  # 鼠标相对于窗口顶部的距离
                relative_y_ratio = relative_y / window_height if window_height > 0 else 0.5
                
                # 缩小垂直搜索范围，减少背景干扰
                base_height = 150  # 基础搜索范围（从200缩小到150）
                max_height = 250   # 最大搜索范围（从400缩小到250）
                
                # 计算向上和向下的搜索范围
                upward_range = int(base_height + (max_height - base_height) * (1 - relative_y_ratio))
                downward_range = int(base_height + (max_height - base_height) * relative_y_ratio)
                
                y1 = max(window_rect[1], cursor_y - upward_range)  # 向上搜索
                y2 = min(window_rect[3], cursor_y + downward_range)  # 向下搜索
                
                logging.info(f"[区域检测] 使用鼠标右侧优化区域(怪物): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}, 垂直位置比例: {relative_y_ratio:.2f}, 向上: {upward_range}px, 向下: {downward_range}px, 最大宽度: {max_horizontal_width}px")
            else:  # region_type == 'item'
                # 物品：使用全屏识别，然后根据字体大小筛选
                # 物品名称比其他文字大60%以上，利用这个特征筛选
                logging.info(f"[区域检测] 物品识别：使用全屏识别+字体大小筛选")
                return self._ocr_item_by_font_size(cursor_x, cursor_y, window_rect)

            # 检查截图坐标有效性
            if x1 >= x2 or y1 >= y2:
                logging.warning(f"[区域检测] 截图坐标无效: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                # 使用备用方案
                return self._get_text_with_small_area(cursor_x, cursor_y, region_type)
            
            # 使用固定区域进行OCR
            return self._ocr_from_region(x1, y1, x2, y2, cursor_x, cursor_y, window_rect, region_type)
            
            # 以下代码暂时注释，用于测试固定区域的成功率
            # # 优先尝试：使用动态计算的名称区域（基于相对位置关系）
            # # position.json中的坐标只是用来计算相对位置关系，不用于检测鼠标是否在图标区域内
            # # 假设鼠标位置在图标区域内，根据相对位置关系计算名称区域
            # if self.position_config and (self.monster_icon_name_offset if region_type == 'monster' else self.item_icon_name_offset):
            #     # 从position.json获取图标区域的尺寸（用于构建以鼠标位置为基准的图标区域）
            #     icon_area = self._build_icon_area_from_cursor(cursor_x, cursor_y, region_type)
            #     if icon_area:
            #         logging.info(f"[区域检测] 鼠标位置: ({cursor_x}, {cursor_y}), 构建的图标区域: min_x={icon_area['min_x']}, max_x={icon_area['max_x']}, min_y={icon_area['min_y']}, max_y={icon_area['max_y']}")
            #         name_area = self.calculate_name_area_from_icon(icon_area, region_type)
            #         if name_area:
            #             x1, y1, x2, y2 = name_area
            #             logging.info(f"[区域检测] 使用动态计算的名称区域({region_type}): ({x1}, {y1}) -> ({x2}, {y2})")
            #             # 确保坐标在窗口范围内
            #             x1 = max(window_rect[0], x1)
            #             y1 = max(window_rect[1], y1)
            #             x2 = min(window_rect[2], x2)
            #             y2 = min(window_rect[3], y2)
            #             
            #             if x1 < x2 and y1 < y2:
            #                 logging.info(f"[区域检测] 调整后的名称区域: ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            #                 # 使用计算出的名称区域进行OCR
            #                 return self._ocr_from_region(x1, y1, x2, y2, cursor_x, cursor_y, window_rect)
            #             else:
            #                 logging.warning(f"[区域检测] 调整后的名称区域无效: ({x1}, {y1}) -> ({x2}, {y2})")
            #         else:
            #             logging.warning(f"[区域检测] 无法计算名称区域")
            #     else:
            #         logging.warning(f"[区域检测] 无法构建图标区域，将使用固定小区域")
            # else:
            #     logging.info(f"[区域检测] 位置配置不可用，将使用固定小区域")
            
            # # 备用方案：使用固定的小区域
            # # 计算鼠标相对于窗口的位置
            # relative_x = cursor_x - window_rect[0]
            # relative_y = cursor_y - window_rect[1]
            # 
            # # 根据类型定义不同的截图区域
            # if region_type == 'monster':
            #     # 怪物/事件：名称在鼠标右上角
            #     # 区域：从鼠标位置向右上角延伸，宽度400px，高度200px
            #     area_width = 400
            #     area_height = 200
            #     x1 = cursor_x  # 鼠标位置作为左边界
            #     y1 = max(window_rect[1], cursor_y - area_height)  # 从鼠标上方开始
            #     x2 = min(window_rect[2], cursor_x + area_width)  # 向右延伸
            #     y2 = cursor_y  # 鼠标位置作为下边界
            #     logging.info(f"[区域检测] 使用固定小区域(怪物): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            # else:  # region_type == 'item'
            #     # 物品：名称在鼠标上方
            #     # 区域：鼠标上方居中，宽度300px，高度150px
            #     area_width = 300
            #     area_height = 150
            #     x1 = max(window_rect[0], cursor_x - area_width // 2)  # 居中
            #     y1 = max(window_rect[1], cursor_y - area_height)  # 从鼠标上方开始
            #     x2 = min(window_rect[2], x1 + area_width)
            #     y2 = cursor_y  # 鼠标位置作为下边界
            #     logging.info(f"[区域检测] 使用固定小区域(物品): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            # 
            # # 检查截图坐标有效性
            # if x1 >= x2 or y1 >= y2:
            #     logging.warning(f"[区域检测] 截图坐标无效: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            #     # 使用备用方案
            #     return self._get_text_with_small_area(cursor_x, cursor_y, region_type)
            # 
            # # 使用固定区域进行OCR
            # return self._ocr_from_region(x1, y1, x2, y2, cursor_x, cursor_y, window_rect)
            
            # 备用方案：使用固定的小区域
            # 计算鼠标相对于窗口的位置
            relative_x = cursor_x - window_rect[0]
            relative_y = cursor_y - window_rect[1]
            
            # 根据类型定义不同的截图区域
            if region_type == 'monster':
                # 怪物/事件：名称在鼠标右上角
                # 区域：从鼠标位置向右上角延伸，宽度400px，高度200px
                area_width = 400
                area_height = 200
            x1 = cursor_x  # 鼠标位置作为左边界
                y1 = max(window_rect[1], cursor_y - area_height)  # 从鼠标上方开始
                x2 = min(window_rect[2], cursor_x + area_width)  # 向右延伸
                y2 = cursor_y  # 鼠标位置作为下边界
                logging.info(f"[区域检测] 使用固定小区域(怪物): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            else:  # region_type == 'item'
                # 物品：名称在鼠标上方
                # 区域：鼠标上方居中，宽度300px，高度200px（向上移动更多）
                area_width = 300
                area_height = 200  # 从150增加到200，向上移动更多
                x1 = max(window_rect[0], cursor_x - area_width // 2)  # 居中
                y1 = max(window_rect[1], cursor_y - area_height)  # 从鼠标上方开始（向上移动更多）
                x2 = min(window_rect[2], x1 + area_width)
                y2 = cursor_y  # 鼠标位置作为下边界
                logging.info(f"[区域检测] 使用固定小区域(物品): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")

            # 检查截图坐标有效性
            if x1 >= x2 or y1 >= y2:
                logging.warning(f"[区域检测] 截图坐标无效: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                # 使用备用方案
                return self._get_text_with_small_area(cursor_x, cursor_y, region_type)
            
            # 使用固定区域进行OCR
            return self._ocr_from_region(x1, y1, x2, y2, cursor_x, cursor_y, window_rect, region_type)
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            logging.error(traceback.format_exc())
            return None
    
    def _ocr_from_region(self, x1, y1, x2, y2, cursor_x, cursor_y, window_rect, region_type='monster'):
        """
        从指定区域进行OCR识别
        
        Args:
            x1, y1, x2, y2: 截图区域的坐标
            cursor_x, cursor_y: 鼠标坐标（用于调试）
            window_rect: 窗口坐标
            region_type: 'monster' 或 'item'，用于选择OCR模式
        
        Returns:
            str: OCR识别结果文本，或None
        """
        try:
            # 截取区域图像
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception as e:
                logging.error(f'截图失败: {e}')
                return None
            img_array = np.array(screenshot)
            
            # 保存调试图像
            debug_img = img_array.copy()
            # 在调试图像上画一个红色十字光标（鼠标在截图区域中的位置）
            mouse_in_region_x = cursor_x - x1
            mouse_in_region_y = cursor_y - y1
            cv2.line(debug_img, (mouse_in_region_x-10, mouse_in_region_y), (mouse_in_region_x+10, mouse_in_region_y), (0,0,255), 2)
            cv2.line(debug_img, (mouse_in_region_x, mouse_in_region_y-10), (mouse_in_region_x, mouse_in_region_y+10), (0,0,255), 2)
            # 画区域边界（绿色矩形）
            cv2.rectangle(debug_img, (0, 0), (x2-x1-1, y2-y1-1), (0, 255, 0), 2)
            
            # 保存到debug_capture.png（临时文件，会被清理）
            cv2.imwrite('debug_capture.png', cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
            
            # 保存带时间戳的截图到data/temp目录
            try:
                # 确定基础目录
                if is_packaged_environment():
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(__file__)
                
                # 创建data/temp目录
                temp_dir = os.path.join(base_dir, 'data', 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成时间戳文件名
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 精确到毫秒
                screenshot_filename = f'ocr_region_{timestamp}.png'
                screenshot_path = os.path.join(temp_dir, screenshot_filename)
                
                # 保存截图
                cv2.imwrite(screenshot_path, cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
                logging.info(f"[截图保存] 识别区域截图已保存: {screenshot_path}")
            except Exception as e:
                logging.error(f"[截图保存] 保存识别区域截图失败: {e}")
            
            logging.debug(f"截图区域: ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            
            # 尝试从缓存获取OCR结果（基于原始图像hash）
            import hashlib
            img_hash = hashlib.md5(img_array.tobytes()).hexdigest()
            if img_hash in self.ocr_cache:
                logging.debug("使用OCR缓存结果")
                return self.ocr_cache[img_hash]
            
            # OCR识别：使用优化后的Tesseract（PSM 11 + OEM 1，原始图像）
            # 基于测试结果：原始图像+PSM11+OEM1效果最好（匹配次数最多）
            text = None
            
            # 策略1：首先尝试原始图像（最快，匹配次数最多）
            try:
                text = self.ocr_for_game(img_array, mode='balanced', region_type=region_type, use_preprocess=False)
                if text and text.strip():
                    logging.info(f"[OCR] 原始图像识别成功: {repr(text[:100])}")
            except Exception as e:
                logging.warning(f"[OCR] 原始图像识别失败: {e}")
            
            # 策略2：如果原始图像失败，尝试去噪+增强（分数最高，但速度较慢）
            if not text or not text.strip() or len(text.strip()) < 2:
                try:
                    # 去噪+增强预处理
                    if len(img_array.shape) == 3:
                        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    else:
                        gray = img_array.copy()
                    
                    # 去噪
                    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                    
                    # CLAHE增强
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(denoised)
                    
                    # 使用增强后的图像进行OCR
                    text_enhanced = self.ocr_for_game(enhanced, mode='balanced', region_type=region_type, use_preprocess=False)
                    if text_enhanced and text_enhanced.strip() and len(text_enhanced.strip()) >= 2:
                        logging.info(f"[OCR] 去噪+增强识别成功: {repr(text_enhanced[:100])}")
                        text = text_enhanced
                except Exception as e:
                    logging.warning(f"[OCR] 去噪+增强识别失败: {e}")
            
            if not text or not text.strip():
                logging.warning("[OCR] 所有策略都未能识别出有效文本")
                text = None
            else:
                logging.info(f"[OCR] OCR最终识别结果: {repr(text) if text else 'None'}")
            
            # 缓存OCR结果（限制缓存大小）
                    if text:
                if len(self.ocr_cache) >= self.ocr_cache_max_size:
                    # 删除最旧的缓存项（FIFO）
                    oldest_key = next(iter(self.ocr_cache))
                    del self.ocr_cache[oldest_key]
                self.ocr_cache[img_hash] = text
            
            return text if text else None
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            logging.error(traceback.format_exc())
            return None
    
    def _ocr_item_by_font_size(self, cursor_x, cursor_y, window_rect):
        """
        根据鼠标位置截取指定区域进行OCR识别
        如果鼠标位置为(0,0)，则图片范围为x -400~400，y 400~0
        即：x范围从鼠标左侧400px到右侧400px（宽度800px），y范围从鼠标上方400px到鼠标位置（高度400px）
        """
        try:
            # 定义区域大小
            # x范围：cursor_x - 400 到 cursor_x + 400（宽度800px，以鼠标为中心）
            # y范围：cursor_y - 400 到 cursor_y（高度400px，从鼠标上方400px到鼠标位置）
            x_offset = 400  # 左右各400px
            y_offset = 400  # 上方400px
            
            # 计算截图区域坐标
            x1 = max(window_rect[0], cursor_x - x_offset)  # 左侧边界
            x2 = min(window_rect[2], cursor_x + x_offset)  # 右侧边界
            y1 = max(window_rect[1], cursor_y - y_offset)  # 上边界（鼠标上方400px）
            y2 = min(window_rect[3], cursor_y)  # 下边界（鼠标位置）
            
            # 检查坐标有效性
            if x1 >= x2 or y1 >= y2:
                logging.warning(f"[物品OCR] 截图坐标无效: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                return None
            
            logging.info(f"[物品OCR] 截图区域: ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}, 鼠标位置: ({cursor_x}, {cursor_y})")
            
            # 截取区域图像
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception as e:
                logging.error(f'截图失败: {e}')
                return None
            
            img_array = np.array(screenshot)
            
            # 保存调试图像
            debug_img = img_array.copy()
            # 在调试图像上画一个红色十字光标（鼠标在截图区域中的位置）
            mouse_in_region_x = cursor_x - x1
            mouse_in_region_y = cursor_y - y1
            cv2.line(debug_img, (mouse_in_region_x-10, mouse_in_region_y), (mouse_in_region_x+10, mouse_in_region_y), (0,0,255), 2)
            cv2.line(debug_img, (mouse_in_region_x, mouse_in_region_y-10), (mouse_in_region_x, mouse_in_region_y+10), (0,0,255), 2)
            # 画区域边界（绿色矩形）
            cv2.rectangle(debug_img, (0, 0), (x2-x1-1, y2-y1-1), (0, 255, 0), 2)
            
            # 保存调试截图
            try:
                if is_packaged_environment():
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(__file__)
                
                temp_dir = os.path.join(base_dir, 'data', 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                screenshot_filename = f'ocr_item_region_{timestamp}.png'
                screenshot_path = os.path.join(temp_dir, screenshot_filename)
                cv2.imwrite(screenshot_path, cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
                logging.info(f"[截图保存] 物品区域截图已保存: {screenshot_path}")
            except Exception as e:
                logging.error(f"[截图保存] 保存区域截图失败: {e}")
            
            # 转换为PIL Image
            if len(img_array.shape) == 3:
                pil_img = Image.fromarray(img_array)
            else:
                pil_img = Image.fromarray(img_array)
            
            # 如果图像太大，先缩放以加快OCR速度并防止挂起
            max_dimension = 2000
            if pil_img.width > max_dimension or pil_img.height > max_dimension:
                scale = min(max_dimension / pil_img.width, max_dimension / pil_img.height)
                new_width = int(pil_img.width * scale)
                new_height = int(pil_img.height * scale)
                try:
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            
            # 使用 image_to_data 获取文本的位置和大小信息
            try:
                ocr_data = pytesseract.image_to_data(
                    pil_img,
                    lang='chi_sim',
                    config='--oem 1 --psm 11 -c preserve_interword_spaces=1',
                    output_type=pytesseract.Output.DICT
                )
            except Exception as e:
                logging.error(f"[物品OCR] image_to_data失败: {e}")
                return None
            
            # 解析OCR数据，提取文本和字体大小（高度）
            text_items = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                if not text or int(ocr_data['conf'][i]) < 0:  # 跳过空文本和低置信度
                    continue
                
                # 获取文本的位置和大小
                left = ocr_data['left'][i]
                top = ocr_data['top'][i]
                width = ocr_data['width'][i]
                height = ocr_data['height'][i]
                conf = int(ocr_data['conf'][i])
                
                # 只保留中文字符较多的文本（至少1个中文字符，允许"锅铲"等2字符物品）
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                if chinese_chars >= 1:
                    # 排除常见的类型标签和描述词汇（这些不是物品名称）
                    type_labels = ['武器', '伙伴', '小型', '中型', '大型', '水系', '火系', '科技', '奖励', 
                                  '物品', '造成', '攻克', '持续', '减速', '加速', '冻结', '治疗', '护盾',
                                  '伤害', '获得', '使用', '触发', '秒', '倍', '提高', '降低', '增加', '减少',
                                  '食物', '工具', '速度', '受到', '一定', '战斗', '信和']
                    # 排除只包含描述词汇的文本
                    if text not in type_labels and not all(c in type_labels for c in text):
                        text_items.append({
                            'text': text,
                            'height': height,
                            'width': width,
                            'left': left,
                            'top': top,
                            'conf': conf,
                            'chinese_count': chinese_chars
                        })
            
            if not text_items:
                logging.warning("[物品OCR] 未识别到有效文本")
                return None
            
            # 按字体高度排序，找出最大的文本
            text_items.sort(key=lambda x: x['height'], reverse=True)
            
            # 记录所有文本的字体大小用于调试
            logging.info(f"[物品OCR] 识别到 {len(text_items)} 个有效文本，字体大小（高度）:")
            all_texts = []
            for idx, item in enumerate(text_items[:10]):  # 只显示前10个
                logging.info(f"  {idx+1}. {item['text']}: 高度={item['height']}px, 宽度={item['width']}px, 置信度={item['conf']}%")
                all_texts.append(item['text'])
            
            # 检查是否包含"锅铲"相关的字
            if any('锅' in t or '铲' in t for t in all_texts):
                logging.info(f"[物品OCR] ⚠️ 检测到可能包含'锅'或'铲'的文本: {[t for t in all_texts if '锅' in t or '铲' in t]}")
            
            # 尝试合并相邻的文本（如"临时"+"大棒"或"临时"+"大"+"棒"）
            # 按位置排序，找出可能相邻的文本
            text_items_sorted = sorted(text_items, key=lambda x: (x['top'], x['left']))
            merged_texts = []
            
            # 改进的合并逻辑：支持多次合并（如"临时"+"大"+"棒"）
            used_indices = set()
            for i, item in enumerate(text_items_sorted):
                if i in used_indices:
                    continue
                    
                merged_text = item['text']
                merged_height = item['height']
                merged_width = item['width']
                merged_left = item['left']
                merged_top = item['top']
                current_indices = {i}
                
                # 多次合并：继续查找右侧相邻的文本
                changed = True
                while changed:
                    changed = False
                    for j, other_item in enumerate(text_items_sorted):
                        if j in used_indices or j in current_indices:
                            continue
                        # 检查是否在同一行（垂直距离小于字体高度的1.5倍）
                        vertical_distance = abs(merged_top - other_item['top'])
                        if vertical_distance <= merged_height * 1.5:
                            # 检查是否在右侧（水平距离小于字体宽度的3倍）
                            horizontal_distance = other_item['left'] - (merged_left + merged_width)
                            if 0 <= horizontal_distance <= merged_width * 3:
                                # 合并文本
                                merged_text = merged_text + other_item['text']
                                merged_width = other_item['left'] + other_item['width'] - merged_left
                                merged_height = max(merged_height, other_item['height'])
                                current_indices.add(j)
                                changed = True
                                logging.info(f"[物品OCR] 🔗 合并相邻文本: {merged_text} (包含 {len(current_indices)} 个文本)")
                                break
                
                # 标记已使用的索引
                used_indices.update(current_indices)
                
                merged_texts.append({
                    'text': merged_text,
                    'height': merged_height,
                    'width': merged_width,
                    'chinese_count': sum(1 for c in merged_text if '\u4e00' <= c <= '\u9fff')
                })
            
            # 按字体高度排序合并后的文本
            merged_texts.sort(key=lambda x: x['height'], reverse=True)
            
            # 优先检查是否能匹配到物品名称（快速匹配）
            # 先提取所有物品名称的中文字符，用于快速匹配
            if not hasattr(self, '_item_names_cache'):
                self._item_names_cache = []
                for item_name_en, item_data in self.items_data.items():
                    item_name_zh = item_data.get('name_zh', '')
                    if item_name_zh:
                        item_name_zh_clean = re.sub(r'[^\u4e00-\u9fff]', '', item_name_zh)
                        if item_name_zh_clean:
                            self._item_names_cache.append(item_name_zh_clean)
            
            def quick_match_item(text):
                """快速检查文本是否能匹配到物品名称"""
                if not text or len(text) < 1:
                    return False
                text_clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
                if len(text_clean) < 1:
                    return False
                # 检查是否在物品名称中（部分匹配）
                for item_name_zh_clean in self._item_names_cache:
                    # 如果OCR文本在物品名称中，或物品名称在OCR文本中
                    if text_clean in item_name_zh_clean or item_name_zh_clean in text_clean:
                        # 计算匹配度
                        match_ratio = min(len(text_clean), len(item_name_zh_clean)) / max(len(text_clean), len(item_name_zh_clean))
                        if match_ratio >= 0.4:  # 至少40%匹配
                            return True
                return False
            
            # 筛选：优先选择能匹配到物品名称的文本
            matched_items = []
            unmatched_items = []
            for item in merged_texts:
                if quick_match_item(item['text']):
                    matched_items.append(item)
                else:
                    unmatched_items.append(item)
            
            # 优先从匹配的文本中选择
            if matched_items:
                # 按字体高度排序匹配的文本
                matched_items.sort(key=lambda x: x['height'], reverse=True)
                # 优先选择最大的匹配文本
                item_name = matched_items[0]['text']
                logging.info(f"[物品OCR] ✅ 找到匹配物品名称的文本: {item_name}, 高度: {matched_items[0]['height']}px")
                return item_name
            
            # 如果没有匹配的，使用原来的逻辑（按字体大小筛选）
            if len(merged_texts) >= 2:
                largest_height = merged_texts[0]['height']
                second_largest_height = merged_texts[1]['height']
                size_ratio = largest_height / second_largest_height if second_largest_height > 0 else 0
                
                # 检查最大的文本是否比第二大的大60%以上
                if size_ratio >= 1.6:
                    item_name = merged_texts[0]['text']
                    logging.info(f"[物品OCR] ✅ 找到最大文本（字体大小筛选）: {item_name}, 高度: {largest_height}px, 第二大: {second_largest_height}px, 比例: {size_ratio:.2f}")
                    return item_name
                else:
                    # 如果最大的文本不够大，尝试前几个最大的文本
                    # 优先选择高度大、中文字符多、且不是描述词汇的文本
                    for item in merged_texts[:10]:  # 检查前10个最大的文本
                        if item['chinese_count'] >= 1:  # 至少1个中文字符
                            # 再次过滤描述词汇
                            text_clean = item['text'].strip()
                            if text_clean and text_clean not in ['物品', '造成', '攻克', '持续', '减速', '加速', '冻结', '治疗', '护盾', '伤害', '获得', '使用', '触发', '食物', '工具', '速度', '受到', '一定', '战斗', '信和']:
                                logging.info(f"[物品OCR] ⚠️ 选择文本（未满足60%阈值，比例: {size_ratio:.2f}）: {text_clean}, 高度: {item['height']}px")
                                return text_clean
                    # 如果都过滤掉了，返回最大的文本
                    if merged_texts:
                        logging.warning(f"[物品OCR] ⚠️ 所有文本都被过滤，返回最大文本: {merged_texts[0]['text']}, 高度: {merged_texts[0]['height']}px")
                        return merged_texts[0]['text']
            else:
                # 只有一个文本，直接返回
                item_name = merged_texts[0]['text'] if merged_texts else text_items[0]['text']
                logging.info(f"[物品OCR] 只有一个文本: {item_name}, 高度: {merged_texts[0]['height'] if merged_texts else text_items[0]['height']}px")
                return item_name
            
            # 如果都没有满足条件，返回最大的文本
            if merged_texts:
                logging.warning(f"[物品OCR] 未找到满足60%阈值的文本，返回最大文本: {merged_texts[0]['text']}")
                return merged_texts[0]['text']
            
            return None
            
        except Exception as e:
            logging.error(f"物品OCR失败: {e}")
            logging.error(traceback.format_exc())
            return None
                    logging.error(f'[{region["name"]}] 截图失败: {e}')
                    continue
                
                img_array = np.array(screenshot)
                
                # 保存调试图像
                debug_img = img_array.copy()
                # 在调试图像上画一个红色十字光标（鼠标在截图区域中的位置）
                mouse_in_region_x, mouse_in_region_y = region['cursor_offset']
                cv2.line(debug_img, (mouse_in_region_x-10, mouse_in_region_y), (mouse_in_region_x+10, mouse_in_region_y), (0,0,255), 2)
                cv2.line(debug_img, (mouse_in_region_x, mouse_in_region_y-10), (mouse_in_region_x, mouse_in_region_y+10), (0,0,255), 2)
                # 画区域边界（绿色矩形）
                cv2.rectangle(debug_img, (0, 0), (x2-x1-1, y2-y1-1), (0, 255, 0), 2)
                
                # 保存调试截图
                try:
                    if is_packaged_environment():
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        base_dir = os.path.dirname(__file__)
                    
                    temp_dir = os.path.join(base_dir, 'data', 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                    screenshot_filename = f'ocr_item_{region["name"]}_{timestamp}.png'
                    screenshot_path = os.path.join(temp_dir, screenshot_filename)
                    cv2.imwrite(screenshot_path, cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
                    logging.info(f"[截图保存] 物品{region['name']}区域截图已保存: {screenshot_path}")
                except Exception as e:
                    logging.error(f"[截图保存] 保存{region['name']}区域截图失败: {e}")
                
                # 转换为PIL Image
                if len(img_array.shape) == 3:
                    pil_img = Image.fromarray(img_array)
                else:
                    pil_img = Image.fromarray(img_array)
                
                # 如果图像太大，先缩放以加快OCR速度并防止挂起
                max_dimension = 2000
                if pil_img.width > max_dimension or pil_img.height > max_dimension:
                    scale = min(max_dimension / pil_img.width, max_dimension / pil_img.height)
                    new_width = int(pil_img.width * scale)
                    new_height = int(pil_img.height * scale)
                    try:
                        pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    except AttributeError:
                        pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                
                # 使用 image_to_data 获取文本的位置和大小信息
                try:
                    ocr_data = pytesseract.image_to_data(
                        pil_img,
                        lang='chi_sim',
                        config='--oem 1 --psm 11 -c preserve_interword_spaces=1',
                        output_type=pytesseract.Output.DICT
                    )
                except Exception as e:
                    logging.error(f"[物品OCR] [{region['name']}] image_to_data失败: {e}")
                    continue
                
                # 解析OCR数据，提取文本和字体大小（高度）
                text_items = []
                n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                if not text or int(ocr_data['conf'][i]) < 0:  # 跳过空文本和低置信度
                    continue
                
                # 获取文本的位置和大小
                left = ocr_data['left'][i]
                top = ocr_data['top'][i]
                width = ocr_data['width'][i]
                height = ocr_data['height'][i]
                conf = int(ocr_data['conf'][i])
                
                # 只保留中文字符较多的文本（至少1个中文字符，允许"锅铲"等2字符物品）
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                if chinese_chars >= 1:
                    # 排除常见的类型标签和描述词汇（这些不是物品名称）
                    type_labels = ['武器', '伙伴', '小型', '中型', '大型', '水系', '火系', '科技', '奖励', 
                                  '物品', '造成', '攻克', '持续', '减速', '加速', '冻结', '治疗', '护盾',
                                  '伤害', '获得', '使用', '触发', '秒', '倍', '提高', '降低', '增加', '减少',
                                  '食物', '工具', '速度', '受到', '一定', '战斗', '信和']
                    # 排除只包含描述词汇的文本
                    if text not in type_labels and not all(c in type_labels for c in text):
                        text_items.append({
                            'text': text,
                            'height': height,
                            'width': width,
                            'left': left,
                            'top': top,
                            'conf': conf,
                            'chinese_count': chinese_chars
                        })
            
                if not text_items:
                    logging.warning(f"[物品OCR] [{region['name']}] 未识别到有效文本")
                    continue
                
                # 按字体高度排序，找出最大的文本
                text_items.sort(key=lambda x: x['height'], reverse=True)
                
                # 记录所有文本的字体大小用于调试
                logging.info(f"[物品OCR] [{region['name']}] 识别到 {len(text_items)} 个有效文本，字体大小（高度）:")
                all_texts = []
                for idx, item in enumerate(text_items[:10]):  # 只显示前10个
                    logging.info(f"  {idx+1}. {item['text']}: 高度={item['height']}px, 宽度={item['width']}px, 置信度={item['conf']}%")
                    all_texts.append(item['text'])
                
                # 检查是否包含"锅铲"相关的字
                if any('锅' in t or '铲' in t for t in all_texts):
                    logging.info(f"[物品OCR] [{region['name']}] ⚠️ 检测到可能包含'锅'或'铲'的文本: {[t for t in all_texts if '锅' in t or '铲' in t]}")
                
                # 尝试合并相邻的文本（如"临时"+"大棒"或"临时"+"大"+"棒"）
                # 按位置排序，找出可能相邻的文本
                text_items_sorted = sorted(text_items, key=lambda x: (x['top'], x['left']))
                merged_texts = []
                
                # 改进的合并逻辑：支持多次合并（如"临时"+"大"+"棒"）
                used_indices = set()
                for i, item in enumerate(text_items_sorted):
                    if i in used_indices:
                        continue
                        
                    merged_text = item['text']
                    merged_height = item['height']
                    merged_width = item['width']
                    merged_left = item['left']
                    merged_top = item['top']
                    current_indices = {i}
                    
                    # 多次合并：继续查找右侧相邻的文本
                    changed = True
                    while changed:
                        changed = False
                        for j, other_item in enumerate(text_items_sorted):
                            if j in used_indices or j in current_indices:
                                continue
                            # 检查是否在同一行（垂直距离小于字体高度的1.5倍）
                            vertical_distance = abs(merged_top - other_item['top'])
                            if vertical_distance <= merged_height * 1.5:
                                # 检查是否在右侧（水平距离小于字体宽度的3倍）
                                horizontal_distance = other_item['left'] - (merged_left + merged_width)
                                if 0 <= horizontal_distance <= merged_width * 3:
                                    # 合并文本
                                    merged_text = merged_text + other_item['text']
                                    merged_width = other_item['left'] + other_item['width'] - merged_left
                                    merged_height = max(merged_height, other_item['height'])
                                    current_indices.add(j)
                                    changed = True
                                    logging.info(f"[物品OCR] [{region['name']}] 🔗 合并相邻文本: {merged_text} (包含 {len(current_indices)} 个文本)")
                                    break
                    
                    # 标记已使用的索引
                    used_indices.update(current_indices)
                    
                    merged_texts.append({
                        'text': merged_text,
                        'height': merged_height,
                        'width': merged_width,
                        'chinese_count': sum(1 for c in merged_text if '\u4e00' <= c <= '\u9fff'),
                        'region': region['name']
                    })
                
                # 按字体高度排序合并后的文本
                merged_texts.sort(key=lambda x: x['height'], reverse=True)
                
                # 优先检查是否能匹配到物品名称（快速匹配）
                # 先提取所有物品名称的中文字符，用于快速匹配
                if not hasattr(self, '_item_names_cache'):
                    self._item_names_cache = []
                    for item_name_en, item_data in self.items_data.items():
                        item_name_zh = item_data.get('name_zh', '')
                        if item_name_zh:
                            item_name_zh_clean = re.sub(r'[^\u4e00-\u9fff]', '', item_name_zh)
                            if item_name_zh_clean:
                                self._item_names_cache.append(item_name_zh_clean)
                
                def quick_match_item(text):
                    """快速检查文本是否能匹配到物品名称"""
                    if not text or len(text) < 1:
                        return False
                    text_clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
                    if len(text_clean) < 1:
                        return False
                    # 检查是否在物品名称中（部分匹配）
                    for item_name_zh_clean in self._item_names_cache:
                        # 如果OCR文本在物品名称中，或物品名称在OCR文本中
                        if text_clean in item_name_zh_clean or item_name_zh_clean in text_clean:
                            # 计算匹配度
                            match_ratio = min(len(text_clean), len(item_name_zh_clean)) / max(len(text_clean), len(item_name_zh_clean))
                            if match_ratio >= 0.4:  # 至少40%匹配
                                return True
                    return False
                
                # 筛选：优先选择能匹配到物品名称的文本
                matched_items = []
                unmatched_items = []
                for item in merged_texts:
                    if quick_match_item(item['text']):
                        matched_items.append(item)
                    else:
                        unmatched_items.append(item)
                
                # 计算该区域的最佳候选文本和评分
                region_best = None
                region_score = 0
                
                # 优先从匹配的文本中选择
                if matched_items:
                    # 按字体高度排序匹配的文本
                    matched_items.sort(key=lambda x: x['height'], reverse=True)
                    region_best = matched_items[0]['text']
                    region_score = 100 + matched_items[0]['height']  # 匹配的文本给高分
                    logging.info(f"[物品OCR] [{region['name']}] ✅ 找到匹配物品名称的文本: {region_best}, 高度: {matched_items[0]['height']}px")
                else:
                    # 如果没有匹配的，使用原来的逻辑（按字体大小筛选）
                    if len(merged_texts) >= 2:
                        largest_height = merged_texts[0]['height']
                        second_largest_height = merged_texts[1]['height']
                        size_ratio = largest_height / second_largest_height if second_largest_height > 0 else 0
                        
                        # 检查最大的文本是否比第二大的大60%以上
                        if size_ratio >= 1.6:
                            region_best = merged_texts[0]['text']
                            region_score = 50 + largest_height  # 字体大小筛选的文本给中等分
                            logging.info(f"[物品OCR] [{region['name']}] ✅ 找到最大文本（字体大小筛选）: {region_best}, 高度: {largest_height}px, 第二大: {second_largest_height}px, 比例: {size_ratio:.2f}")
                        else:
                            # 如果最大的文本不够大，尝试前几个最大的文本
                            for item in merged_texts[:10]:  # 检查前10个最大的文本
                                if item['chinese_count'] >= 1:  # 至少1个中文字符
                                    # 再次过滤描述词汇
                                    text_clean = item['text'].strip()
                                    if text_clean and text_clean not in ['物品', '造成', '攻克', '持续', '减速', '加速', '冻结', '治疗', '护盾', '伤害', '获得', '使用', '触发', '食物', '工具', '速度', '受到', '一定', '战斗', '信和']:
                                        region_best = text_clean
                                        region_score = 30 + item['height']  # 未满足阈值的文本给低分
                                        logging.info(f"[物品OCR] [{region['name']}] ⚠️ 选择文本（未满足60%阈值，比例: {size_ratio:.2f}）: {region_best}, 高度: {item['height']}px")
                                        break
                            if not region_best and merged_texts:
                                region_best = merged_texts[0]['text']
                                region_score = 10 + merged_texts[0]['height']
                                logging.warning(f"[物品OCR] [{region['name']}] ⚠️ 所有文本都被过滤，返回最大文本: {region_best}, 高度: {merged_texts[0]['height']}px")
                    else:
                        # 只有一个文本，直接返回
                        region_best = merged_texts[0]['text'] if merged_texts else text_items[0]['text']
                        region_score = 20 + (merged_texts[0]['height'] if merged_texts else text_items[0]['height'])
                        logging.info(f"[物品OCR] [{region['name']}] 只有一个文本: {region_best}, 高度: {merged_texts[0]['height'] if merged_texts else text_items[0]['height']}px")
                
                # 更新最佳结果
                if region_best and region_score > best_score:
                    best_score = region_score
                    best_result = {
                        'text': region_best,
                        'region': region['name'],
                        'score': region_score
                    }
            
            # 返回最佳结果
            if best_result:
                logging.info(f"[物品OCR] ✅ 最终选择: {best_result['text']} (来自{best_result['region']}区域, 评分: {best_result['score']:.1f})")
                return best_result['text']
            
            logging.warning("[物品OCR] 所有区域都未识别到有效文本")
            return None
            
        except Exception as e:
            logging.error(f"物品OCR（字体大小筛选）失败: {e}")
            logging.error(traceback.format_exc())
            return None
    
    def get_game_log_path(self):
        """获取游戏日志文件路径"""
        try:
            userprofile = os.environ.get('USERPROFILE', '')
            if not userprofile:
                return None
            
            log_path = os.path.join(
                userprofile,
                'AppData', 'LocalLow', 'Tempo Storm', 'The Bazaar', 'Player.log'
            )
            return log_path
        except Exception as e:
            logging.error(f"获取游戏日志路径失败: {e}")
            return None
    
    def start_log_monitor(self):
        """启动游戏日志监控线程"""
        log_path = self.get_game_log_path()
        if not log_path:
            logging.warning("无法获取游戏日志路径，日志监控功能将不可用")
            return
        
        if not os.path.exists(log_path):
            logging.info(f"游戏日志文件不存在: {log_path}，等待文件创建...")
        
        self.log_monitor_running = True
        self.log_monitor_thread = threading.Thread(target=self.monitor_game_log, args=(log_path,), daemon=True)
        self.log_monitor_thread.start()
        logging.info("游戏日志监控线程已启动")
    
    def monitor_game_log(self, log_path):
        """监控游戏日志文件，解析物品信息"""
        import time as time_module
        
        # 等待日志文件存在
        max_wait_time = 60  # 最多等待60秒
        wait_start = time_module.time()
        while not os.path.exists(log_path) and (time_module.time() - wait_start) < max_wait_time:
            time_module.sleep(2)
        
        if not os.path.exists(log_path):
            logging.warning(f"游戏日志文件不存在: {log_path}，日志监控功能将不可用")
            return
        
        logging.info(f"开始监控游戏日志: {log_path}")
        
        # 编译正则表达式
        # 注意：TemplateId后面没有空格，直接跟UUID
        re_purchase = re.compile(r"Card Purchased: InstanceId:\s*([^\s]+)\s*-\s*TemplateId([^\s-]+(?:-[^\s-]+){4})\s*-\s*Target:([^\s]+)")
        re_id = re.compile(r"ID:\s*\[([^\]]+)\]")
        re_owner = re.compile(r"- Owner:\s*\[([^\]]+)\]")
        re_section = re.compile(r"- Section:\s*\[([^\]]+)\]")
        
        # 读取位置
        last_file_size = 0
        file_position = 0
        
        try:
            # 首次读取：建立完整的映射关系
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 建立InstanceId到TemplateId的映射
                    # 注意：由于items.json中没有UUID字段，TemplateId无法直接匹配到物品
                    # 日志映射功能暂时无法使用，但保留代码以便将来扩展
                    for match in re_purchase.finditer(content):
                        instance_id = match.group(1)
                        template_id = match.group(2)
                        with self.log_data_lock:
                            self.instance_to_template[instance_id] = template_id
                            # 通过TemplateId查找物品中文名称（会失败，因为items.json中没有UUID）
                            self._update_template_name_mapping(template_id)
                    
                    file_position = len(content)
                    last_file_size = os.path.getsize(log_path)
                    # 统计信息
                    unique_templates = len(self.template_to_name_zh)
                    total_instances = len(self.instance_to_template)
                    template_names = list(self.template_to_name_zh.values())
                    logging.info(f"初始扫描完成: {unique_templates} 种物品 ({', '.join(template_names)}), {total_instances} 个实例")
        except Exception as e:
            logging.error(f"初始扫描日志文件失败: {e}")
        
        # 持续监控日志文件
        while self.log_monitor_running:
            try:
                if not os.path.exists(log_path):
                    time_module.sleep(2)
                    continue
                
                current_file_size = os.path.getsize(log_path)
                
                # 检测文件是否被重置（文件变小）
                if current_file_size < last_file_size:
                    logging.info("检测到日志文件被重置，重新开始扫描...")
                    file_position = 0
                    with self.log_data_lock:
                        self.instance_to_template.clear()
                        self.template_to_name_zh.clear()
                        self.hand_items.clear()
                        self.stash_items.clear()
                        self.equipped_items.clear()
                
                last_file_size = current_file_size
                
                # 读取新内容
                if current_file_size > file_position:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(file_position)
                        new_lines = f.readlines()
                        file_position = f.tell()
                        
                        # 解析新行
                        current_instance_id = None
                        current_owner = None
                        current_section = None
                        
                        for line in new_lines:
                            line = line.strip()
                            
                            # 解析购买记录
                            purchase_match = re_purchase.search(line)
                            if purchase_match:
                                instance_id = purchase_match.group(1)
                                template_id = purchase_match.group(2)
                                target = purchase_match.group(3)
                                
                                with self.log_data_lock:
                                    self.instance_to_template[instance_id] = template_id
                                    self._update_template_name_mapping(template_id)
                                    
                                    # 根据Target判断位置
                                    if "Storage" in target:
                                        self.equipped_items.add(instance_id)
                            
                            # 解析物品信息
                            id_match = re_id.search(line)
                            if id_match:
                                current_instance_id = id_match.group(1)
                                if current_instance_id.startswith('itm_'):
                                    current_owner = None
                                    current_section = None
                            
                            owner_match = re_owner.search(line)
                            if owner_match:
                                current_owner = owner_match.group(1)
                            
                            section_match = re_section.search(line)
                            if section_match:
                                current_section = section_match.group(1)
                                
                                # 如果是玩家的物品，区分手牌和仓库
                                if current_owner == "Player" and current_instance_id and current_instance_id.startswith('itm_'):
                                    with self.log_data_lock:
                                        if current_section == "Hand":
                                            self.hand_items.add(current_instance_id)
                                            self.equipped_items.add(current_instance_id)  # 兼容旧代码
                                        elif current_section == "Stash" or current_section == "Storage":
                                            self.stash_items.add(current_instance_id)
                                            self.equipped_items.add(current_instance_id)  # 兼容旧代码
                
                time_module.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logging.error(f"监控日志文件时出错: {e}")
                time_module.sleep(5)
    
    def _update_template_name_mapping(self, template_id):
        """更新TemplateId到中文名称的映射"""
        if template_id in self.template_to_name_zh:
            return  # 已经存在，不需要更新
        
        # 优先从uuid_to_item_data（items_db.json）中查找
        if template_id in self.uuid_to_item_data:
            item_data = self.uuid_to_item_data[template_id]
            name_zh = item_data.get('name_zh', '')
            if name_zh:
                self.template_to_name_zh[template_id] = name_zh
                logging.debug(f"[日志映射] ✅ TemplateId: {template_id} -> 中文名称: {name_zh} (从items_db.json)")
                return
        
        # 如果uuid_to_item_data中没有，尝试在items_data中查找（兼容旧逻辑）
        for item_name_en, item_data in self.items_data.items():
            # 检查TemplateId是否匹配（可能是item_name_en或item_data中的id字段）
            if item_name_en == template_id or item_data.get('id') == template_id:
                name_zh = item_data.get('name_zh', '')
                if name_zh:
                    self.template_to_name_zh[template_id] = name_zh
                    logging.info(f"[日志映射] ✅ TemplateId: {template_id} -> 中文名称: {name_zh} (从items.json)")
                else:
                    logging.warning(f"[日志映射] ⚠️ TemplateId: {template_id} 找到物品但无中文名称: {item_name_en}")
                break
        else:
            # 如果都没找到，记录调试信息
            logging.debug(f"[日志映射] TemplateId: {template_id} 未找到匹配的物品")
    
    def get_hand_item_names(self):
        """获取手牌物品名称列表（用于物品识别辅助）"""
        with self.log_data_lock:
            hand_names = []
            for instance_id in self.hand_items:
                template_id = self.instance_to_template.get(instance_id)
                if template_id:
                    name_zh = self.template_to_name_zh.get(template_id)
                    if name_zh:
                        hand_names.append(name_zh)
                    else:
                        # 如果没有找到名称，记录Template ID以便调试
                        logging.debug(f"[手牌物品] InstanceId: {instance_id} -> TemplateId: {template_id} (未找到中文名称)")
            return hand_names
    
    def get_stash_item_names(self):
        """获取仓库物品名称列表（用于物品识别辅助）"""
        with self.log_data_lock:
            stash_names = []
            for instance_id in self.stash_items:
                template_id = self.instance_to_template.get(instance_id)
                if template_id:
                    name_zh = self.template_to_name_zh.get(template_id)
                    if name_zh:
                        stash_names.append(name_zh)
            return stash_names
    
    def _get_text_with_small_area(self, cursor_x, cursor_y, region_type='monster'):
        """使用小区域截图的备用方案"""
        try:
            logging.info(f"使用小区域截图备用方案 ({region_type})")
            
            # 根据类型定义不同的截图区域
            if region_type == 'monster':
                # 怪物/事件：名称在鼠标右上角
                area_width = 400
                area_height = 200
                x1 = cursor_x  # 鼠标位置作为左边界
                y1 = max(0, cursor_y - area_height)  # 从鼠标上方开始
                x2 = cursor_x + area_width
                y2 = cursor_y  # 鼠标位置作为下边界
            else:  # region_type == 'item'
                # 物品：名称在鼠标上方
                area_width = 300
                area_height = 150
                x1 = max(0, cursor_x - area_width // 2)  # 居中
                y1 = max(0, cursor_y - area_height)  # 从鼠标上方开始
            x2 = x1 + area_width
                y2 = cursor_y  # 鼠标位置作为下边界
            
            # 确保不超出屏幕边界
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            if x2 > screen_width:
                x2 = screen_width
                x1 = max(0, x2 - area_width)
            if y1 < 0:
                y1 = 0
                y2 = min(screen_height, y1 + area_height)
            
            logging.info(f"小区域截图({region_type}): ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            
            # 截取区域图像
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception as e:
                logging.error(f'固定区域截图失败: {e}')
                return None
            
            img_array = np.array(screenshot)
            
            # 保存调试图像
            debug_img = img_array.copy()
            # 在调试图像上画一个红色十字光标（鼠标在区域中心）
            center_x = area_width // 2
            center_y = area_height // 2
            cv2.line(debug_img, (center_x-10, center_y), (center_x+10, center_y), (0,0,255), 2)
            cv2.line(debug_img, (center_x, center_y-10), (center_x, center_y+10), (0,0,255), 2)
            cv2.imwrite('debug_capture_fixed.png', cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
            
            # 尝试从缓存获取OCR结果（基于图像hash）
            import hashlib
            img_hash = hashlib.md5(img_array.tobytes()).hexdigest()
            if img_hash in self.ocr_cache:
                logging.debug("使用OCR缓存结果（固定区域）")
                return self.ocr_cache[img_hash]
            
            # OCR识别：使用游戏专用OCR（平衡模式+无预处理，效果最好）
            text = self.ocr_for_game(img_array, mode='balanced', region_type=region_type, use_preprocess=False)
            logging.debug(f"固定区域OCR原始识别结果:\n{text}")
            
            # 缓存OCR结果（限制缓存大小）
            if text:
                if len(self.ocr_cache) >= self.ocr_cache_max_size:
                    # 删除最旧的缓存项（FIFO）
                    oldest_key = next(iter(self.ocr_cache))
                    del self.ocr_cache[oldest_key]
                self.ocr_cache[img_hash] = text
            
            return text if text else None
            
        except Exception as e:
            logging.error(f"固定区域截图失败: {e}")
            return None

    def create_info_window(self):
        """创建信息窗口"""
        try:
            # 创建主窗口
            self.info_window = tk.Toplevel()
            self.info_window.title("The Bazaar Helper")
            self.info_window.attributes('-alpha', 0.95)  # 设置透明度
            # 注释掉 overrideredirect，让窗口有标准边框，便于录屏
            # self.info_window.overrideredirect(True)  # 无边框窗口
            self.info_window.attributes('-topmost', True)  # 保持在顶层
            
            # 设置窗口背景色为深色
            bg_color = '#1C1810'  # 深褐色背景
            fg_color = '#E8D4B9'  # 浅色文字
            self.info_window.configure(bg=bg_color)
            
            # 创建可滚动框架
            self.scrollable_frame = ScrollableFrame(self.info_window, bg=bg_color)
            self.scrollable_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # 获取内部框架作为内容容器
            self.content_frame = self.scrollable_frame.get_inner_frame()
            
            # 创建事件选项容器
            self.event_options_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.event_options_frame.pack(fill='x', expand=True)
            
            # 创建技能容器
            self.skills_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.skills_frame.pack(fill='x', expand=True)
            
            # 创建物品容器
            self.items_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.items_frame.pack(fill='x', expand=True)
            
            # 初始隐藏窗口
            self.info_window.withdraw()
            
            logging.debug("信息窗口创建成功")
            
        except Exception as e:
            logging.error(f"创建信息窗口失败: {e}")
            if self.info_window:
                self.info_window.destroy()
                self.info_window = None

    def adjust_window_size(self, pos_x, pos_y):
        """调整窗口大小"""
        try:
            # 获取游戏窗口大小
            _, game_rect = self.get_game_window()
            if not game_rect:
                return
            # 计算最大窗口高度（游戏窗口高度的80%）
            game_height = game_rect[3] - game_rect[1]
            max_window_height = int(game_height * 0.8)
            # 固定窗口宽度
            window_width = 600
            
            # 更新内容框架以获取实际高度
            self.content_frame.update_idletasks()
            content_height = self.content_frame.winfo_reqheight() + 20  # 添加一些额外空间
            
            # 根据内容高度确定窗口高度
            if content_height <= max_window_height:
                # 内容不多，窗口高度适应内容
                window_height = content_height
            else:
                # 内容超出最大高度，使用最大高度
                window_height = max_window_height
            
            # 调整窗口位置（确保不超出屏幕边界）
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            if pos_x + window_width > screen_width:
                pos_x = max(0, screen_width - window_width)
            if pos_y + window_height > screen_height:
                pos_y = max(0, screen_height - window_height)
                
            self.info_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
            
            # 更新滚动区域，决定是否显示滚动条
            self.scrollable_frame.update_scrollregion()
            
            logging.debug(f"窗口大小调整完成: {window_width}x{window_height}, 位置: {pos_x}, {pos_y}")
        except Exception as e:
            logging.error(f"调整窗口大小失败: {e}")
            logging.error(traceback.format_exc())

    def clear_frames(self):
        """清空所有内容框架"""
        try:
            # 检查窗口组件是否存在且有效
            if not hasattr(self, 'event_options_frame') or not self.event_options_frame.winfo_exists():
                return
            if not hasattr(self, 'skills_frame') or not self.skills_frame.winfo_exists():
                return
            if not hasattr(self, 'items_frame') or not self.items_frame.winfo_exists():
                return
            if not hasattr(self, 'content_frame') or not self.content_frame.winfo_exists():
                return
            
        # 只清空子元素，不destroy主Frame本身
            try:
        for widget in self.event_options_frame.winfo_children():
            widget.destroy()
            except tk.TclError:
                pass  # 窗口已被销毁，忽略错误
            
            try:
        for widget in self.skills_frame.winfo_children():
            widget.destroy()
            except tk.TclError:
                pass  # 窗口已被销毁，忽略错误
            
            try:
        for widget in self.items_frame.winfo_children():
            widget.destroy()
            except tk.TclError:
                pass  # 窗口已被销毁，忽略错误
            
        # 控制框架的显示/隐藏
            try:
        self.event_options_frame.pack_forget()
        self.skills_frame.pack_forget()
        self.items_frame.pack_forget()
            except tk.TclError:
                pass  # 窗口已被销毁，忽略错误
            
        # 清理content_frame下的所有spacer（Frame），只destroy不是三大主Frame的spacer
            try:
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget not in [self.event_options_frame, self.skills_frame, self.items_frame]:
                widget.destroy()
            except tk.TclError:
                pass  # 窗口已被销毁，忽略错误
        except Exception as e:
            logging.error(f"清空框架时出错: {e}")
            # 不抛出异常，允许继续执行

    def get_monster_icon_path(self, icon_filename, icon_type='skill'):
        """获取怪物相关的图标路径（技能/物品/怪物）"""
        # icon_type: 'skill', 'item', 'monster'
        try:
            if is_packaged_environment():
                workspace_dir = os.path.dirname(sys.executable)
            else:
                workspace_dir = os.path.abspath(os.path.dirname(__file__))
            
            # 新目录结构：data/icon/skill/, data/icon/item/, data/icon/monster/
            icon_dir = os.path.join(workspace_dir, 'data', 'icon', icon_type)
            
            # 处理icon文件名（可能包含skill/前缀）
            if icon_filename.startswith('skill/'):
                icon_filename = icon_filename.replace('skill/', '')
            
            icon_path = os.path.join(icon_dir, icon_filename)
            if os.path.exists(icon_path):
                logging.debug(f"找到{icon_type}图标: {icon_path}")
                return icon_path
            
            # 如果找不到，返回None（不尝试下载，因为应该已经存在）
            logging.debug(f"未找到{icon_type}图标: {icon_path}")
            return None
        except Exception as e:
            logging.error(f"获取怪物图标路径失败: {e}")
            return None
    
    def get_local_icon_path(self, icon_url, event_name_en='', option_name_en='', icons_dir='icons'):
        """从多个可能的图标路径查找图标，找不到则自动下载（带缓存）"""
        # 检查缓存
        cache_key = f"{icon_url}_{event_name_en}_{option_name_en}"
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
            # 获取工作目录（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                workspace_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                workspace_dir = os.path.abspath(os.path.dirname(__file__))
            
        # 如果是相对路径，直接返回
        if icon_url and not icon_url.startswith('http'):
            # 处理事件图标的特殊目录结构 (反斜杠格式)
            if '\\' in icon_url and 'icons\\' in icon_url:
                # 事件图标路径格式: icons\A Strange Mushroom\Trade It for Something.webp
                # 需要特殊处理，移除 icons\ 前缀
                icon_relative_path = icon_url.replace('icons\\', '').replace('\\', os.sep)
                event_icon_path = os.path.join(workspace_dir, '6.0', 'crawlers', 'event_details_final', 'icons', icon_relative_path)
                if os.path.exists(event_icon_path):
                    logging.debug(f"找到事件图标: {event_icon_path}")
                    self.icon_cache[cache_key] = event_icon_path
                    return event_icon_path
            
            # 处理怪物图标的路径格式 (正斜杠格式)
            elif icon_url.startswith('icons/'):
                # 怪物图标路径格式: icons/Prince Marianas_Electric Eels.webp
                # 移除 icons/ 前缀
                icon_relative_path = icon_url.replace('icons/', '')
                monster_icon_path = os.path.join(workspace_dir, '6.0', 'crawlers', 'monster_details_v3', 'icons', icon_relative_path)
                if os.path.exists(monster_icon_path):
                    logging.debug(f"找到怪物图标: {monster_icon_path}")
                    self.icon_cache[cache_key] = monster_icon_path
                    return monster_icon_path
            
            # 普通图标路径查找 (兼容其他格式)
            icon_paths = [
                os.path.join(workspace_dir, '6.0', 'crawlers', 'monster_details_v3', 'icons'),
                os.path.join(workspace_dir, '6.0', 'crawlers', 'event_details_final', 'icons'),
                os.path.join(workspace_dir, 'icons')
            ]
            for icon_path in icon_paths:
                full_path = os.path.join(icon_path, icon_url)
                if os.path.exists(full_path):
                    self.icon_cache[cache_key] = full_path
                    return full_path
        
        # 处理HTTP URL：从新的事件图标目录查找
        if icon_url and icon_url.startswith('http') and event_name_en:
            # 从 data/icon/event/ 目录查找
            # 格式: data/icon/event/{event_name_en}/{option_name_en}.webp
            
            # 处理文件夹名称中的特殊字符（如单引号）
            event_name_en_clean = event_name_en.replace("'", "").replace("'", "")
            
            # 尝试多个可能的文件夹名称
            possible_dirs = [event_name_en, event_name_en_clean]
            event_icon_dir = None
            for dir_name in possible_dirs:
                test_dir = os.path.join(workspace_dir, 'data', 'icon', 'event', dir_name)
                if os.path.exists(test_dir):
                    event_icon_dir = test_dir
                    break
            
            if event_icon_dir and os.path.exists(event_icon_dir):
                # 优先使用选项的英文名称匹配
                if option_name_en:
                    # 清理选项名称：移除单引号和空格
                    option_name_clean = option_name_en.replace("'", "").replace("'", "").replace(' ', '')
                    for filename in os.listdir(event_icon_dir):
                        if filename.endswith('.webp') or filename.endswith('.png'):
                            filename_base = os.path.splitext(filename)[0].replace("'", "").replace("'", "").replace(' ', '')
                            # 检查文件名是否包含选项名称（忽略大小写、空格和单引号）
                            if option_name_clean.lower() in filename_base.lower() or \
                               filename_base.lower() in option_name_clean.lower():
                                icon_path = os.path.join(event_icon_dir, filename)
                                logging.info(f"从新目录找到事件图标(选项匹配): {icon_path}")
                                self.icon_cache[cache_key] = icon_path
                                return icon_path
                
                # 如果选项名称匹配失败，尝试从URL提取文件名
                parsed_url = urlparse(icon_url)
                url_filename = os.path.basename(parsed_url.path)
                # 移除查询参数和扩展名，只保留文件名部分
                if '@' in url_filename:
                    url_filename = url_filename.split('@')[0]
                
                if url_filename:
                    # 遍历目录查找匹配的文件
                    for filename in os.listdir(event_icon_dir):
                        if filename.endswith('.webp') or filename.endswith('.png'):
                            # 检查文件名是否与URL相关
                            if url_filename.lower() in filename.lower() or filename.lower() in url_filename.lower():
                                icon_path = os.path.join(event_icon_dir, filename)
                                logging.debug(f"从新目录找到事件图标(URL匹配): {icon_path}")
                                self.icon_cache[cache_key] = icon_path
                                return icon_path
                
                # 如果都没找到，返回目录中的第一个图标（作为备选）
                for filename in sorted(os.listdir(event_icon_dir)):
                    if filename.endswith('.webp') or filename.endswith('.png'):
                        icon_path = os.path.join(event_icon_dir, filename)
                        logging.debug(f"使用备选事件图标: {icon_path}")
                        self.icon_cache[cache_key] = icon_path
                        return icon_path
        
        # 如果都没找到，尝试从旧路径查找
        if icon_url and icon_url.startswith('http'):
            # 尝试从旧的event_details_final目录查找
            old_event_icon_dir = os.path.join(workspace_dir, '6.0', 'crawlers', 'event_details_final', 'icons')
            if event_name_en and os.path.exists(old_event_icon_dir):
                event_folder = os.path.join(old_event_icon_dir, event_name_en)
                if os.path.exists(event_folder):
                    # 查找匹配的图标文件
                    for filename in os.listdir(event_folder):
                        if filename.endswith('.webp') or filename.endswith('.png'):
                            icon_path = os.path.join(event_folder, filename)
                            logging.debug(f"从旧目录找到事件图标: {icon_path}")
                            self.icon_cache[cache_key] = icon_path
                            return icon_path
        
            return None

        if not icon_url or not icon_url.startswith('http'):
            logging.warning(f"无效的图标URL: {icon_url}")
            return None

        try:
            # 清理文件名，移除查询参数
            parsed_url = urlparse(icon_url)
            filename = os.path.basename(parsed_url.path)
            # 允许@字符
            filename = re.sub(r'[^\w\-_.@]', '_', filename)

            # 尝试多个可能的图标路径
            # 获取工作目录（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                workspace_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                workspace_dir = os.path.abspath(os.path.dirname(__file__))
            icon_paths = [
                os.path.join(workspace_dir, '6.0', 'crawlers', 'monster_details_v3', 'icons'),
                os.path.join(workspace_dir, '6.0', 'crawlers', 'event_details_final', 'icons'),
                os.path.join(workspace_dir, icons_dir)
            ]
            
            for icons_path in icon_paths:
                icon_file_path = os.path.join(icons_path, filename)
                if os.path.exists(icon_file_path):
                    logging.debug(f"找到本地图标: {icon_file_path}")
                    self.icon_cache[icon_url] = icon_file_path
                    return icon_file_path
            
            # 如果都没找到，使用第一个路径进行下载
            icons_path = icon_paths[0]
            icon_file_path = os.path.join(icons_path, filename)

            logging.debug(f"查找本地图标路径: {icon_file_path}")
            if os.path.exists(icon_file_path):
                logging.debug(f"找到本地图标: {icon_file_path}")
                self.icon_cache[icon_url] = icon_file_path
                return icon_file_path

            # 本地没有，尝试下载（在后台线程中）
            logging.debug(f"开始下载图标: {icon_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(icon_url, headers=headers, timeout=5, verify=False)
            if resp.status_code == 200:
                os.makedirs(icons_path, exist_ok=True)
                with open(icon_file_path, 'wb') as f:
                    f.write(resp.content)
                logging.debug(f"图标下载成功: {icon_file_path}")
                self.icon_cache[icon_url] = icon_file_path
                return icon_file_path
            else:
                logging.warning(f"下载图标失败，状态码: {resp.status_code}")
                return None

        except Exception as e:
            logging.error(f"处理图标失败: {e}")
            return None

    def format_monster_info(self, monster_name):
        """格式化怪物信息显示"""
        try:
            if not monster_name:
                return False
            
            # 确保窗口已创建
            if not self.info_window or not self.info_window.winfo_exists():
                logging.warning("信息窗口不存在，重新创建...")
                self.create_info_window()
            
            # 检查窗口组件是否存在（在访问之前）
            if not hasattr(self, 'skills_frame') or not self.skills_frame.winfo_exists():
                logging.warning("skills_frame 不存在，重新创建窗口组件...")
                self.create_info_window()
            if not hasattr(self, 'items_frame') or not self.items_frame.winfo_exists():
                logging.warning("items_frame 不存在，重新创建窗口组件...")
                self.create_info_window()
            if not hasattr(self, 'content_frame') or not self.content_frame.winfo_exists():
                logging.warning("content_frame 不存在，重新创建窗口组件...")
                self.create_info_window()
                
            if monster_name not in self.monster_data:
                logging.warning(f"未找到怪物数据: {monster_name}")
                self.clear_frames()
                # 显示未找到数据的提示
                try:
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                not_found_frame = IconFrame(self.skills_frame)
                not_found_frame.pack(fill='x', pady=0)
                not_found_frame.update_content(
                    monster_name,
                    "未找到该怪物的数据，请稍后再试。",
                    None
                )
                except tk.TclError as e:
                    logging.error(f"显示未找到数据失败: {e}")
                    return False
                return True
                
            monster = self.monster_data[monster_name]
            logging.debug(f"怪物数据: {monster}")
            self.clear_frames()
            
            has_skills = False
            # 显示技能
            if monster.get('skills'):
                has_skills = True
                try:
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                except tk.TclError as e:
                    logging.error(f"pack skills_frame 失败: {e}")
                    return False
                for skill in monster['skills']:
                    skill_frame = IconFrame(self.skills_frame)
                    skill_frame.pack(fill='x', pady=0)
                    
                    # 获取技能名称和描述（优先使用中文）
                    skill_name_en = skill.get('name', '')
                    skill_name_zh = skill.get('name_zh', skill_name_en)
                    skill_description = ''
                    
                    # 从skills_data中获取描述信息
                    if skill_name_en in self.skills_data:
                        skill_info = self.skills_data[skill_name_en]
                        skill_description = skill_info.get('description_zh', '')
                        skill_icon = skill_info.get('icon', '')
                        skill_aspect_ratio = float(skill_info.get('aspect_ratio', 1.0))
                    else:
                        skill_description = skill.get('description', '')
                        skill_icon = skill.get('icon', '')
                        skill_aspect_ratio = 1.0
                    
                    # 获取技能图标（优先使用新目录结构）
                    icon_path = None
                    if skill_icon:
                        # 新格式：skill/Above_the_Clouds.webp 或直接文件名
                        if skill_icon.startswith('skill/'):
                            icon_path = self.get_monster_icon_path(skill_icon, 'skill')
                        else:
                            icon_path = self.get_monster_icon_path(skill_icon, 'skill')
                    elif skill.get('icon'):
                        icon_path = self.get_local_icon_path(skill['icon'])
                    elif skill.get('icon_url'):
                        icon_path = self.get_local_icon_path(skill['icon_url'])
                    
                    skill_frame.update_content(
                        skill_name_zh,
                        skill_description,
                        icon_path,
                        skill_aspect_ratio
                    )
                    
            # 显示物品
            if monster.get('items'):
                if has_skills:
                    # 添加分隔条
                    try:
                    separator = tk.Frame(self.content_frame, height=2, bg='#3A7BBA')
                    separator.pack(fill='x', pady=5, padx=10)
                    except tk.TclError as e:
                        logging.error(f"创建分隔条失败: {e}")
                        return False
                
                try:
                self.items_frame.pack(fill='x', pady=0, padx=0)
                except tk.TclError as e:
                    logging.error(f"pack items_frame 失败: {e}")
                    return False
                # 统计相同物品的数量
                items_count = {}
                items_info = {}
                for item in monster['items']:
                    name = item.get('name', '')
                    if name:
                        items_count[name] = items_count.get(name, 0) + 1
                        if name not in items_info:
                            items_info[name] = item
                            
                # 显示物品信息
                item_keys = list(items_info.keys())
                for idx, item_name in enumerate(item_keys):
                    item = items_info[item_name]
                    item_frame = IconFrame(self.items_frame)
                    
                    # 设置物品框架的边距
                    item_frame.pack(fill='x', pady=0)
                        
                    # 获取物品名称和描述（优先使用中文）
                    item_name_zh = item.get('name_zh', item_name)
                    item_description = ''
                    
                    # 从items_data中获取描述信息
                    if item_name in self.items_data:
                        item_info = self.items_data[item_name]
                        item_description = item_info.get('description_zh', '')
                        item_icon = item_info.get('icon', '')
                        item_aspect_ratio = float(item_info.get('aspect_ratio', 1.0))
                    else:
                        item_description = item.get('description', '')
                        item_icon = item.get('icon', '')
                        item_aspect_ratio = float(item.get('aspect_ratio', 1.0))
                        
                    # 处理物品名称（如果有多个相同物品，显示数量）
                    display_name = item_name_zh
                    if items_count[item_name] > 1:
                        display_name = f"{item_name_zh} x{items_count[item_name]}"
                        
                    # 获取物品图标（优先使用新目录结构）
                    icon_path = None
                    if item_icon:
                        # 新格式：直接文件名，如 28_Hour_Fitness.webp
                        icon_path = self.get_monster_icon_path(item_icon, 'item')
                    elif item.get('icon'):
                        icon_path = self.get_local_icon_path(item['icon'])
                    elif item.get('icon_url'):
                        icon_path = self.get_local_icon_path(item['icon_url'])
                    
                    item_frame.update_content(
                        display_name,
                        item_description,
                        icon_path,
                        item_aspect_ratio
                    )
                    
            # 如果既没有技能也没有物品，显示提示信息
            if not monster.get('skills') and not monster.get('items'):
                try:
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                not_found_frame = IconFrame(self.skills_frame)
                not_found_frame.pack(fill='x', pady=0)
                not_found_frame.update_content(
                    monster_name,
                    "该怪物没有技能和物品数据。",
                    None
                )
                except tk.TclError as e:
                    logging.error(f"显示提示信息失败: {e}")
                    return False
                
            return True
            
        except Exception as e:
            logging.error(f"格式化怪物信息失败: {e}")
            logging.error(traceback.format_exc())
            return False

    def find_best_event_match(self, text):
        """查找最佳匹配的事件"""
        if not text:
            return None
            
        def clean_text(text):
            if not isinstance(text, str):
                return ""
            # 只保留字母和空格
            cleaned = re.sub(r'[^a-zA-Z\s]', '', text)
            # 移除多余空格并转换为小写
            return ' '.join(cleaned.split()).lower()
        
        try:
            # 将OCR结果按行分割并清理
            lines = str(text).split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned = clean_text(line.strip())
                if len(cleaned) >= 3:  # 只保留有意义的行（至少3个字母）
                    cleaned_lines.append(cleaned)
                    
            logging.debug(f"清理后的文本行: {cleaned_lines}")
            
            # 遍历所有事件寻找匹配
            for line in cleaned_lines:
                if not line:
                    continue
                    
                # 遍历所有事件寻找匹配
                for event in self.events:
                    clean_event_name = clean_text(event['name'])
                    
                    # 完全匹配
                    if line == clean_event_name:
                        logging.info(f"找到完全匹配的事件: {event['name']}")
                        return event
                    
                    # 部分匹配（事件名称是行的一部分）
                    if clean_event_name in line:
                        logging.info(f"找到部分匹配的事件: {event['name']}")
                        return event
                    
                    # 反向部分匹配（行是事件名称的一部分）
                    if len(line) >= 3 and line in clean_event_name:
                        logging.info(f"找到反向部分匹配的事件: {event['name']}")
                        return event
            
            logging.debug("未找到匹配的事件")
            return None
            
        except Exception as e:
            logging.error(f"事件匹配时出错: {e}")
            logging.error(traceback.format_exc())
            return None

    def format_event_info(self, event_name):
        """格式化事件信息显示"""
        try:
            logging.info(f"尝试格式化事件信息: {event_name}")
            logging.info(f"当前event_data中的键: {list(self.event_data.keys())[:10]}")  # 显示前10个键用于调试
            
            if event_name not in self.event_data:
                logging.error(f"找不到事件选项数据: {event_name}")
                logging.error(f"可用的事件名称: {list(self.event_data.keys())}")
                return False

            options = self.event_data[event_name]
            if not options:
                logging.error(f"事件选项数据为空: {event_name}")
                return False
            
            logging.info(f"找到 {len(options)} 个事件选项")

            # 确保窗口已创建
            if not self.info_window or not self.info_window.winfo_exists():
                logging.warning("信息窗口不存在，重新创建...")
                self.create_info_window()
            
            # 检查窗口组件是否存在
            if not hasattr(self, 'event_options_frame') or not self.event_options_frame.winfo_exists():
                logging.warning("event_options_frame 不存在，重新创建窗口组件...")
                self.create_info_window()
            if not hasattr(self, 'content_frame') or not self.content_frame.winfo_exists():
                logging.warning("content_frame 不存在，重新创建窗口组件...")
                self.create_info_window()

            # 清除现有内容
            self.clear_frames()

            # 显示事件选项框架
            try:
            self.event_options_frame.pack(fill='x', pady=0)
            except tk.TclError as e:
                logging.error(f"pack event_options_frame 失败: {e}")
                return False

            # 获取事件的英文名称（用于查找图标文件夹）
            event_name_en = self.event_name_map.get(event_name, '')
            # 处理文件夹名称中的特殊字符（如单引号）
            if event_name_en:
                # 移除单引号，因为文件夹名可能没有单引号
                event_name_en_clean = event_name_en.replace("'", "").replace("'", "")
            else:
                event_name_en_clean = ''
            
            logging.debug(f"事件: {event_name}, 英文名: {event_name_en}, 清理后: {event_name_en_clean}")

            for option in options:
                # 优先使用中文名称和描述
                option_name = option.get('name_zh', option.get('name', ''))
                option_description = option.get('description_zh', option.get('description', ''))
                option_name_en = option.get('name', '')  # 英文名称用于查找图标
                
                icon_path = None
                # 尝试多种方式查找图标
                if option.get('icon'):
                    icon_path = self.get_local_icon_path(option['icon'], event_name_en_clean, option_name_en)
                elif option.get('icon_url'):
                    icon_path = self.get_local_icon_path(option['icon_url'], event_name_en_clean, option_name_en)
                
                if not icon_path:
                    logging.warning(f"未找到图标: 事件={event_name_en_clean}, 选项={option_name_en}, URL={option.get('icon_url', '')}")
                
                aspect_ratio = float(option.get('aspect_ratio', 1.0))
                option_frame = IconFrame(self.event_options_frame)
                option_frame.pack(fill='x', pady=0)
                option_frame.update_content(
                    option_name,
                    option_description,
                    icon_path,
                    aspect_ratio
                )

            if not options:
                self.event_options_frame.pack(fill='x', pady=0)
                not_found_frame = IconFrame(self.event_options_frame)
                not_found_frame.pack(fill='x', pady=0)
                not_found_frame.update_content(
                    event_name,
                    "未找到该事件的数据，请稍后再试。",
                    None
                )

            return True

        except Exception as e:
            logging.error(f"格式化事件信息时出错: {e}")
            logging.error(traceback.format_exc())
            return False

    def _do_show_info(self, text, pos_x, pos_y):
        """实际执行显示信息的操作（在主线程中调用）"""
        try:
            # 确保窗口已创建
            if not self.info_window or not self.info_window.winfo_exists():
                logging.warning("信息窗口不存在，重新创建...")
                self.create_info_window()
            
            logging.info(f"开始更新信息显示，OCR文本: {text}")
            match_type, match_name = self.find_best_match(text)
            logging.info(f"匹配结果: type={match_type}, name={match_name}")
            
            display_success = False
            if match_type == 'event':
                logging.info(f"尝试显示事件: {match_name}")
                display_success = self.format_event_info(match_name)
                logging.info(f"format_event_info 返回: {display_success}")
            elif match_type == 'monster':
                display_success = self.format_monster_info(match_name)
                
            if not display_success:
                logging.warning(f"显示失败: match_type={match_type}, match_name={match_name}")
                if match_type:
                    self.show_info_message(f"未找到该{match_type}的数据，请稍后再试。", None)
                else:
                    self.show_info_message("未能识别到怪物或事件名称。", None)
                return
            
            logging.info(f"准备显示窗口，位置: {pos_x}, {pos_y}, ctrl_pressed: {self.ctrl_pressed}")
                
            # 设置初始位置
            self.info_window.geometry(f"+{pos_x}+{pos_y}")
            
            # 更新窗口布局
            self.info_window.update_idletasks()
            
            # 调整窗口大小
            self._do_adjust_window(pos_x, pos_y)
            
            # 显示窗口并置顶（如果匹配成功就显示，不依赖ctrl_pressed状态）
            if display_success:
                logging.info(f"显示窗口: {match_type} - {match_name}")
                self.info_window.deiconify()
                self.info_window.lift()
                self.info_window.attributes('-topmost', True)
            else:
                logging.warning(f"匹配成功但显示失败，不显示窗口")
            
            logging.debug(f"{match_type}信息显示完成，位置: {pos_x}, {pos_y}")
            
        except Exception as e:
            logging.error(f"信息显示异常: {e}")
            logging.error(traceback.format_exc())
    
    def _do_hide_info(self):
        """实际执行隐藏信息窗口的操作（在主线程中调用）"""
        try:
            if self.info_window and self.info_window.winfo_exists():
                self.info_window.withdraw()
        except Exception as e:
            logging.error(f"隐藏信息窗口失败: {e}")
    
    def find_item_by_name(self, text):
        """根据OCR文本查找物品，返回物品数据或None
        优先使用日志数据辅助匹配，提高识别准确率
        """
        if not text or not self.items_data:
            return None
        
        # 清理文本，提取中文名称
        def clean_text_chinese_only(s):
            if not isinstance(s, str):
                return ""
            s = re.sub(r'[^\u4e00-\u9fff]', '', s)
            return s
        
        text_clean = clean_text_chinese_only(text)
        if not text_clean or len(text_clean) < 2:
            return None
        
        # 优先使用日志数据中的物品名称映射（更准确）
        # 注意：由于items.json中没有UUID字段，日志中的TemplateId无法直接匹配
        # 暂时禁用日志辅助匹配，专注于OCR匹配
        log_best_match = None
        log_best_ratio = 0.0
        log_best_name = None
        
        with self.log_data_lock:
            log_items_count = len(self.template_to_name_zh)
            if log_items_count > 0:
                logging.info(f"[日志辅助匹配] 检查 {log_items_count} 个日志物品，OCR文本: {text_clean}")
                # 检查日志中是否有匹配的物品名称
                for template_id, name_zh in self.template_to_name_zh.items():
                    name_zh_clean = clean_text_chinese_only(name_zh)
                    if not name_zh_clean:
                        continue
                    
                    # 完全匹配
                    if text_clean == name_zh_clean:
                        # 通过TemplateId查找物品数据（需要找到对应的物品）
                        for item_name_en, item_data in self.items_data.items():
                            if item_data.get('name_zh') == name_zh:
                                logging.info(f"[日志辅助匹配] ✅ 完全匹配: {text_clean} -> {name_zh} (TemplateId: {template_id})")
                                return item_data
                    
                    # 部分匹配（OCR文本在物品名称中，优先）
                    if text_clean in name_zh_clean:
                        ratio = len(text_clean) / len(name_zh_clean)
                        if ratio >= 0.3:
                            for item_name_en, item_data in self.items_data.items():
                                if item_data.get('name_zh') == name_zh:
                                    logging.info(f"[日志辅助匹配] ✅ 部分匹配(OCR在名称中): {text_clean} -> {name_zh} (TemplateId: {template_id}, 相似度: {ratio:.2f})")
                                    return item_data
                    
                    # 模糊匹配
                    ratio = difflib.SequenceMatcher(None, text_clean, name_zh_clean).ratio()
                    if ratio > log_best_ratio and ratio >= 0.30:
                        for item_name_en, item_data in self.items_data.items():
                            if item_data.get('name_zh') == name_zh:
                                log_best_ratio = ratio
                                log_best_match = item_data
                                log_best_name = name_zh
                
                # 如果日志辅助匹配找到了较好的结果，优先返回
                if log_best_match and log_best_ratio >= 0.30:
                    logging.info(f"[日志辅助匹配] ✅ 模糊匹配: {text_clean} -> {log_best_name} (相似度: {log_best_ratio:.2f})")
                    return log_best_match
            else:
                logging.debug(f"[日志辅助匹配] 日志物品映射为空（TemplateId无法匹配到items.json，因为items.json中没有UUID字段）")
            
            # 检查日志中是否有匹配的物品名称
            for template_id, name_zh in self.template_to_name_zh.items():
                name_zh_clean = clean_text_chinese_only(name_zh)
                if not name_zh_clean:
                    continue
                
                # 完全匹配
                if text_clean == name_zh_clean:
                    # 通过TemplateId查找物品数据
                    for item_name_en, item_data in self.items_data.items():
                        if item_data.get('id') == template_id or item_name_en == template_id:
                            logging.info(f"[日志辅助匹配] ✅ 完全匹配: {text_clean} -> {name_zh} (TemplateId: {template_id})")
                            return item_data
                
                # 部分匹配（OCR文本在物品名称中，或物品名称在OCR文本中）
                if name_zh_clean in text_clean or text_clean in name_zh_clean:
                    ratio = min(len(name_zh_clean), len(text_clean)) / max(len(name_zh_clean), len(text_clean))
                    # 降低阈值到0.3，因为日志数据更可靠，且OCR可能只识别部分文本
                    if ratio >= 0.3:
                        for item_name_en, item_data in self.items_data.items():
                            if item_data.get('id') == template_id or item_name_en == template_id:
                                # 如果OCR文本在物品名称中（如"工具"在"工具箱"中），优先返回
                                if text_clean in name_zh_clean:
                                    logging.info(f"[日志辅助匹配] ✅ 部分匹配(OCR在名称中): {text_clean} -> {name_zh} (TemplateId: {template_id}, 相似度: {ratio:.2f})")
                                    return item_data
                                # 否则记录为候选
                                if ratio > log_best_ratio:
                                    log_best_ratio = ratio
                                    log_best_match = item_data
                                    log_best_name = name_zh
                                    logging.debug(f"[日志辅助匹配] 候选部分匹配: {text_clean} -> {name_zh} (相似度: {ratio:.2f})")
                
                # 模糊匹配（使用SequenceMatcher，因为OCR可能识别错误）
                ratio = difflib.SequenceMatcher(None, text_clean, name_zh_clean).ratio()
                # 对于日志数据，使用更低的阈值（0.30），因为更可靠
                if ratio > log_best_ratio and ratio >= 0.30:
                    for item_name_en, item_data in self.items_data.items():
                        if item_data.get('id') == template_id or item_name_en == template_id:
                            log_best_ratio = ratio
                            log_best_match = item_data
                            log_best_name = name_zh
                            logging.debug(f"[日志辅助匹配] 候选模糊匹配: {text_clean} -> {name_zh} (相似度: {ratio:.2f})")
        
        # 如果日志辅助匹配找到了较好的结果，优先返回
        if log_best_match and log_best_ratio >= 0.30:
            logging.info(f"[日志辅助匹配] ✅ 模糊匹配: {text_clean} -> {log_best_name} (相似度: {log_best_ratio:.2f})")
            return log_best_match
        elif log_best_match:
            logging.info(f"[日志辅助匹配] ⚠️ 候选匹配: {text_clean} -> {log_best_name} (相似度: {log_best_ratio:.2f}, 低于阈值0.30)")
        
        # 如果日志数据中没有匹配，使用原有的OCR匹配逻辑
        logging.info(f"[OCR匹配] 日志辅助匹配未找到，使用OCR匹配，检查 {len(self.items_data)} 个物品")
        best_match = None
        best_ratio = 0.0
        
        for item_name_en, item_data in self.items_data.items():
            item_name_zh = item_data.get('name_zh', '')
            if not item_name_zh:
                continue
            
            item_name_zh_clean = clean_text_chinese_only(item_name_zh)
            if not item_name_zh_clean:
                continue
            
            # 完全匹配
            if text_clean == item_name_zh_clean:
                logging.info(f"[OCR匹配] ✅ 完全匹配: {text_clean} -> {item_name_zh}")
                return item_data
            
            # 部分匹配（OCR文本在物品名称中，优先）
            if text_clean in item_name_zh_clean:
                ratio = len(text_clean) / len(item_name_zh_clean)
                # 对于2字符名称，如果OCR文本在物品名称中，直接匹配（如"工具"在"工具箱"中）
                if item_name_len == 2 and text_clean == item_name_zh_clean:
                    # 完全匹配，直接返回
                    logging.info(f"[OCR匹配] ✅ 完全匹配(2字符): {text_clean} -> {item_name_zh}")
                    return item_data
                # 对于部分匹配（如"临时"在"临时大棒"中），降低阈值到0.25
                if ratio > best_ratio and ratio >= 0.25:  # 从0.3降低到0.25，允许"临时"匹配"临时大棒"
                    best_ratio = ratio
                    best_match = item_data
                    logging.debug(f"[OCR匹配] 候选部分匹配(OCR在名称中): {text_clean} -> {item_name_zh} (相似度: {ratio:.2f})")
            
            # 部分匹配（物品名称在OCR文本中）
            if item_name_zh_clean in text_clean:
                ratio = len(item_name_zh_clean) / len(text_clean)
                if ratio > best_ratio and ratio >= 0.3:
                    best_ratio = ratio
                    best_match = item_data
                    logging.debug(f"[OCR匹配] 候选部分匹配(名称在OCR中): {text_clean} -> {item_name_zh} (相似度: {ratio:.2f})")
            
            # 模糊匹配（根据名称长度动态调整阈值）
            ratio = difflib.SequenceMatcher(None, text_clean, item_name_zh_clean).ratio()
            
            # 根据物品名称长度动态调整阈值
            item_name_len = len(item_name_zh_clean)
            if item_name_len == 2:
                # 2字符名称：降低阈值到0.4，因为OCR容易识别错误
                threshold = 0.4
            elif item_name_len == 3:
                # 3字符名称：中等阈值
                threshold = 0.45
            elif item_name_len == 4:
                # 4字符名称：较高阈值
                threshold = 0.5
            else:
                # 5+字符名称：高阈值
                threshold = 0.5
            
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = item_data
                logging.debug(f"[OCR匹配] 候选模糊匹配: {text_clean} -> {item_name_zh} (相似度: {ratio:.2f}, 阈值: {threshold:.2f})")
        
        # 最终阈值检查（根据最佳匹配的名称长度）
        if best_match:
            best_name_len = len(clean_text_chinese_only(best_match.get('name_zh', '')))
            if best_name_len == 2:
                final_threshold = 0.4
            elif best_name_len == 3:
                final_threshold = 0.45
            elif best_name_len == 4:
                # 4字符名称：如果OCR文本在物品名称中（部分匹配），降低阈值到0.25
                # 检查是否是部分匹配
                best_name_zh_clean = clean_text_chinese_only(best_match.get('name_zh', ''))
                if text_clean in best_name_zh_clean:
                    final_threshold = 0.25  # 允许"临时"匹配"临时大棒"
                else:
                    final_threshold = 0.5
            else:
                final_threshold = 0.5
            
            if best_ratio >= final_threshold:
                logging.info(f"[OCR匹配] ✅ 找到匹配: {text_clean} -> {best_match.get('name_zh', '')} (相似度: {best_ratio:.2f}, 阈值: {final_threshold:.2f})")
                return best_match
            else:
                logging.warning(f"[OCR匹配] ❌ 未找到匹配: {text_clean} (最佳相似度: {best_ratio:.2f}, 低于阈值{final_threshold:.2f})")
                return None
        else:
            logging.warning(f"[OCR匹配] ❌ 未找到匹配: {text_clean} (未找到候选)")
            return None
    
    def parse_enchantments(self, enchantments_text):
        """解析附魔文本，返回附魔列表"""
        if not enchantments_text:
            return []
        
        enchantments = []
        # 按双换行符分割附魔
        parts = enchantments_text.split('\n\n')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 每部分的第一行是标题，其余是描述
            lines = part.split('\n')
            if len(lines) >= 1:
                title = lines[0].strip()
                description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
                if title:
                    enchantments.append({
                        'title': title,
                        'description': description
                    })
        
        return enchantments
    
    def get_enchantment_title_color(self, title):
        """根据附魔标题返回对应的标题文字颜色（不是背景色）"""
        color_map = {
            '黄金': '#FFD700',  # 黄色
            '沉重': '#F44336',  # 红色
            '寒冰': '#4FC3F7',  # 浅蓝色
            '疾速': '#4CAF50',  # 绿色
            '护盾': '#FFD700',  # 黄色
            '回复': '#4CAF50',  # 绿色
            '毒性蔓延': '#4CAF50',  # 绿色
            '炽焰': '#FF9800',  # 橙色
            '闪亮': '#FFD700',  # 黄色
            '致命': '#F44336',  # 红色
            '辉耀': '#2196F3',  # 蓝色
            '黑曜石': '#F44336',  # 红色
        }
        
        # 检查是否包含关键词
        for key, color in color_map.items():
            if key in title:
                return color
        
        # 默认颜色（白色，和描述文字一致）
        return '#E8E8E8'
    
    def _do_show_enchantments(self, text, pos_x, pos_y):
        """实际执行显示附魔信息的操作（在主线程中调用）"""
        try:
            # 确保窗口已创建
            if not self.info_window or not self.info_window.winfo_exists():
                logging.warning("信息窗口不存在，重新创建...")
                self.create_info_window()
            
            logging.info(f"开始查找物品附魔，OCR文本: {text}")
            
            # 查找物品
            item_data = self.find_item_by_name(text)
            if not item_data:
                logging.warning(f"未找到物品: {text}")
                self.show_info_message("未能识别到物品名称。", None)
                return
            
            item_name = item_data.get('name_zh', item_data.get('name', ''))
            logging.info(f"找到物品: {item_name}")
            
            # 解析附魔信息
            enchantments_text = item_data.get('enchantments', '')
            if not enchantments_text:
                logging.warning(f"物品 {item_name} 没有附魔信息")
                self.show_info_message(f"{item_name} 没有附魔信息。", None)
                return
            
            enchantments = self.parse_enchantments(enchantments_text)
            if not enchantments:
                logging.warning(f"物品 {item_name} 的附魔信息解析失败")
                self.show_info_message(f"{item_name} 的附魔信息解析失败。", None)
                return
            
            logging.info(f"找到 {len(enchantments)} 个附魔")
            
            # 清除现有内容
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # 创建附魔显示容器
            enchantments_container = tk.Frame(self.content_frame, bg='#1C1810')
            enchantments_container.pack(fill='both', expand=True, padx=10, pady=10)
            
            # 创建标题
            title_label = tk.Label(
                enchantments_container,
                text=f"{item_name} - 附魔",
                font=('Microsoft YaHei', 14, 'bold'),
                bg='#1C1810',
                fg='#E8D4B9',
                anchor='w'
            )
            title_label.pack(fill='x', pady=(0, 10))
            
            # 创建卡片容器（网格布局，每行2个）
            cards_frame = tk.Frame(enchantments_container, bg='#1C1810')
            cards_frame.pack(fill='both', expand=True)
            
            # 显示每个附魔卡片
            for i, enchantment in enumerate(enchantments):
                row = i // 2
                col = i % 2
                
                # 获取标题颜色（不是背景色）
                title_color = self.get_enchantment_title_color(enchantment['title'])
                # 背景色统一使用和事件/怪物窗口一致的颜色
                bg_color = '#1C1810'
                
                # 创建卡片框架
                card_frame = tk.Frame(
                    cards_frame,
                    bg=bg_color,
                    relief='flat',
                    bd=2
                )
                card_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                
                # 配置网格权重
                cards_frame.grid_columnconfigure(col, weight=1)
                cards_frame.grid_rowconfigure(row, weight=1)
                
                # 创建卡片内容框架（带内边距）
                card_content = tk.Frame(card_frame, bg=bg_color)
                card_content.pack(fill='both', expand=True, padx=10, pady=10)
                
                # 标题（使用对应的颜色）
                title_label = tk.Label(
                    card_content,
                    text=enchantment['title'],
                    font=('Microsoft YaHei', 12, 'bold'),
                    bg=bg_color,
                    fg=title_color,  # 使用对应的标题颜色
                    anchor='w',
                    wraplength=250
                )
                title_label.pack(fill='x', pady=(0, 5))
                
                # 描述（保持白色）
                if enchantment['description']:
                    desc_label = tk.Label(
                        card_content,
                        text=enchantment['description'],
                        font=('Microsoft YaHei', 10),
                        bg=bg_color,
                        fg='#E8E8E8',
                        anchor='w',
                        justify='left',
                        wraplength=250
                    )
                    desc_label.pack(fill='x')
            
            # 设置初始位置
            self.info_window.geometry(f"+{pos_x}+{pos_y}")
            
            # 更新窗口布局
            self.info_window.update_idletasks()
            
            # 调整窗口大小
            self._do_adjust_window(pos_x, pos_y)
            
            # 显示窗口并置顶
            logging.info(f"显示附魔窗口: {item_name} ({len(enchantments)} 个附魔)")
            self.info_window.deiconify()
            self.info_window.lift()
            self.info_window.attributes('-topmost', True)
            
        except Exception as e:
            logging.error(f"显示附魔信息异常: {e}")
            logging.error(traceback.format_exc())
    
    def _do_adjust_window(self, pos_x, pos_y):
        """实际执行调整窗口大小的操作（在主线程中调用）"""
        try:
            if not self.info_window or not self.info_window.winfo_exists():
                return
            
            # 获取游戏窗口大小
            _, game_rect = self.get_game_window()
            if not game_rect:
                return
            
            # 计算最大窗口高度（游戏窗口高度的80%）
            game_height = game_rect[3] - game_rect[1]
            max_window_height = int(game_height * 0.8)
            # 固定窗口宽度
            window_width = 600
            
            # 更新内容框架以获取实际高度
            self.content_frame.update_idletasks()
            content_height = self.content_frame.winfo_reqheight() + 20  # 添加一些额外空间
            
            # 根据内容高度确定窗口高度
            if content_height <= max_window_height:
                window_height = content_height
            else:
                window_height = max_window_height
            
            # 调整窗口位置（确保不超出屏幕边界）
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            if pos_x + window_width > screen_width:
                pos_x = max(0, screen_width - window_width)
            if pos_y + window_height > screen_height:
                pos_y = max(0, screen_height - window_height)
                
            self.info_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
            
            # 更新滚动区域
            self.scrollable_frame.update_scrollregion()
            
        except Exception as e:
            logging.error(f"调整窗口大小失败: {e}")
    
    def _do_move_window(self, pos_x, pos_y):
        """只移动窗口位置，不调整大小（在主线程中调用）"""
        try:
            if not self.info_window or not self.info_window.winfo_exists():
                return
            
            # 获取当前窗口大小
            current_geometry = self.info_window.geometry()
            # 解析当前几何信息 (格式: "widthxheight+x+y")
            parts = current_geometry.split('+')
            if len(parts) >= 3:
                size_part = parts[0]
                current_width, current_height = map(int, size_part.split('x'))
            else:
                # 如果解析失败，使用默认大小
                current_width, current_height = 600, 400
            
            # 调整窗口位置（确保不超出屏幕边界）
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            if pos_x + current_width > screen_width:
                pos_x = max(0, screen_width - current_width)
            if pos_y + current_height > screen_height:
                pos_y = max(0, screen_height - current_height)
                
            # 只更新位置，保持原有大小
            self.info_window.geometry(f"{current_width}x{current_height}+{pos_x}+{pos_y}")
            
        except Exception as e:
            logging.error(f"移动窗口位置失败: {e}")
    
    def update_info_display(self, text, pos_x, pos_y):
        """更新信息显示（已弃用，保留以兼容旧代码）"""
        # 添加到GUI更新队列
        with self.gui_update_lock:
            self.gui_update_queue.append({
                'type': 'show',
                'text': text,
                'x': pos_x,
                'y': pos_y
            })

    def hide_info(self):
        """隐藏信息窗口"""
        try:
            if self.info_window:
                self.info_window.withdraw()
        except Exception as e:
            logging.error(f"隐藏信息窗口失败: {e}")

    def show_info_message(self, message, icon_url):
        """显示信息消息"""
        try:
            # 清除现有内容
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # 创建消息框架
            message_frame = tk.Frame(self.content_frame, bg='#1C1810')
            message_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # 创建消息标签
            message_label = tk.Label(
                message_frame,
                text=message,
                font=('Microsoft YaHei', 12),
                bg='#1C1810',
                fg='#E8D4B9',
                wraplength=500,
                justify='left'
            )
            message_label.pack(fill='both', expand=True, pady=20)
            
            # 更新窗口布局
            self.info_window.update_idletasks()
            
            # 显示窗口
            if self.info_window:
                self.info_window.deiconify()
                self.info_window.lift()
                self.info_window.attributes('-topmost', True)
        except Exception as e:
            logging.error(f"显示信息消息失败: {e}")
            logging.error(traceback.format_exc())

    def show_info(self, name, description, icon_url, pos_x=None, pos_y=None):
        print(f"显示信息: {name}")
        print(f"描述: {description}")
        print(f"图标URL: {icon_url}")
        
        # 清除现有内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 创建新的内容框架
        icon_path = self.get_local_icon_path(icon_url)
        print(f"本地图标路径: {icon_path}")
        
        frame = IconFrame(self.content_frame)
        frame.pack(fill='both', expand=True, padx=0, pady=0)  # 修改为fill='both'和expand=True
        frame.update_content(name, description, icon_path)
        
        # 更新窗口大小和位置
        self.info_window.update_idletasks()
        window_width = 600
        window_height = max(self.content_frame.winfo_reqheight(), 100)  # 设置最小高度
        print(f"窗口大小: {window_width}x{window_height}")
        
        # 如果提供了位置，就移动窗口
        if pos_x is not None and pos_y is not None:
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            print(f"屏幕大小: {screen_width}x{screen_height}")
            print(f"原始位置: {pos_x}, {pos_y}")
            
            # 确保窗口不会超出屏幕边界
            if pos_x + window_width > screen_width:
                pos_x = screen_width - window_width
            if pos_y + window_height > screen_height:
                pos_y = screen_height - window_height
            print(f"调整后位置: {pos_x}, {pos_y}")
                
            self.info_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        
        # 显示窗口
        self.info_window.deiconify()
        self.info_window.lift()
        self.info_window.attributes('-topmost', True)
        print("窗口已显示")

    def destroy_info_window(self):
        """销毁信息窗口及相关Frame"""
        try:
            # 先隐藏窗口
            if hasattr(self, 'info_window') and self.info_window:
                self.info_window.withdraw()
                
            # 解绑鼠标滚轮事件
            if hasattr(self, 'scrollable_frame') and self.scrollable_frame:
                try:
                    self.scrollable_frame.unbind_all("<MouseWheel>")
                except Exception:
                    pass
                
            # 清理所有子Frame
            if hasattr(self, 'content_frame') and self.content_frame:
                for widget in self.content_frame.winfo_children():
                    if isinstance(widget, IconFrame):
                        widget.destroy()  # 这会触发 IconFrame 的 destroy 方法
                    else:
                        widget.destroy()
                
            # 清理滚动框架
            if hasattr(self, 'scrollable_frame') and self.scrollable_frame:
                self.scrollable_frame.destroy()
                self.scrollable_frame = None
                self.content_frame = None
                
            if hasattr(self, 'event_options_frame') and self.event_options_frame:
                self.event_options_frame = None
                
            if hasattr(self, 'skills_frame') and self.skills_frame:
                self.skills_frame = None
                
            if hasattr(self, 'items_frame') and self.items_frame:
                self.items_frame = None
                
            # 最后销毁主窗口
            if hasattr(self, 'info_window') and self.info_window:
                self.info_window.destroy()
                self.info_window = None
                
        except Exception as e:
            logging.error(f"销毁信息窗口失败: {e}")
            logging.error(traceback.format_exc())

    def reset_game(self, icon, item):
        """重置游戏（关闭进程并清理配置）"""
        try:
            # 查找游戏进程
            game_process = None
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.name() == "The Bazaar.exe":
                        game_process = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if game_process:
                # 关闭游戏进程
                game_process.terminate()
                game_process.wait(timeout=5)

            # 清理游戏配置文件
            appdata_local = os.environ.get('LOCALAPPDATA', '')
            appdata_roaming = os.environ.get('APPDATA', '')
            
            # 可能的配置文件路径
            config_paths = [
                os.path.join(appdata_local, 'TheBazaar'),
                os.path.join(appdata_roaming, 'TheBazaar'),
                os.path.join(appdata_local, 'Tempo', 'TheBazaar'),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'TheBazaar')
            ]
            
            # 清理配置文件
            for path in config_paths:
                if os.path.exists(path):
                    try:
                        # 只删除特定的缓存文件，保留用户设置
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                if file.lower() in ['cache.dat', 'temp.dat', 'session.dat', 'network.dat', 'connection.dat']:
                                    full_path = os.path.join(root, file)
                                    os.remove(full_path)
                                    logging.info(f"已删除缓存文件: {full_path}")
                    except Exception as e:
                        logging.error(f"清理配置文件失败: {e}")

            # 重置网络设置
            self.reset_network()

            logging.info("游戏重置完成，请重新启动游戏")
                
        except Exception as e:
            logging.error(f"重置游戏失败: {e}")
            logging.error(traceback.format_exc())

    def reset_network(self):
        """重置网络设置"""
        try:
            # 清理DNS缓存
            subprocess.run(['ipconfig', '/flushdns'], shell=True, check=True)
            logging.info("DNS缓存已清理")

            # 重置网络适配器
            subprocess.run(['netsh', 'winsock', 'reset'], shell=True, check=True)
            subprocess.run(['netsh', 'int', 'ip', 'reset'], shell=True, check=True)
            logging.info("网络适配器已重置")

            # 重置防火墙规则
            subprocess.run(['netsh', 'advfirewall', 'reset'], shell=True, check=True)
            logging.info("防火墙规则已重置")

            # 添加游戏到防火墙例外
            game_path = None
            steam_path = os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Steam', 'steamapps', 'common', 'TheBazaar')
            if os.path.exists(steam_path):
                game_path = os.path.join(steam_path, 'The Bazaar.exe')
                
            if game_path and os.path.exists(game_path):
                subprocess.run([
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    'name="The Bazaar"',
                    f'dir=in', 'action=allow',
                    f'program="{game_path}"',
                    'enable=yes', 'profile=any'
                ], shell=True, check=True)
                logging.info("已将游戏添加到防火墙例外")

            # 优化网络设置
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 'autotuninglevel=normal'], shell=True, check=True)
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 'chimney=enabled'], shell=True, check=True)
            subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 'rss=enabled'], shell=True, check=True)
            logging.info("网络设置已优化")

        except Exception as e:
            logging.error(f"重置网络设置失败: {e}")
            logging.error(traceback.format_exc())

    def check_tesseract(self):
        """检查Tesseract OCR是否可用，并获取版本信息"""
        try:
            # 获取配置中的Tesseract路径
            tesseract_path = self.config.get_tesseract_path()
            
            # 检查文件是否存在
            if os.path.exists(tesseract_path) and os.path.isfile(tesseract_path):
                # 设置全局路径
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logging.info(f"Tesseract OCR路径设置为: {tesseract_path}")
                
                # 尝试获取版本信息
                try:
                    version_output = subprocess.run(
                        [tesseract_path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if version_output.returncode == 0:
                        version_lines = version_output.stdout.strip().split('\n')
                        if version_lines:
                            version_info = version_lines[0]  # 第一行通常是版本信息
                            logging.info(f"Tesseract OCR版本: {version_info}")
                            
                            # 检查是否为最新版本（5.5.2）
                            if '5.5.2' in version_info:
                                logging.info("Tesseract OCR已是最新版本 5.5.2")
                            elif '5.5.0' in version_info or '5.5.1' in version_info:
                                logging.warning(f"检测到Tesseract版本较旧: {version_info}，建议更新到5.5.2以获得更好的性能和准确性")
                            else:
                                logging.info(f"当前Tesseract版本: {version_info}")
                except Exception as e:
                    logging.debug(f"无法获取Tesseract版本信息: {e}")
                
                return True
            else:
                logging.error(f"Tesseract OCR路径不存在: {tesseract_path}")
                return False
        except Exception as e:
            logging.error(f"检查Tesseract OCR时出错: {e}")
            return False
            
    def show_tesseract_error(self):
        """显示Tesseract OCR错误提示"""
        try:
            # 创建提示窗口
            error_window = tk.Toplevel()
            error_window.title("Tesseract OCR未找到")
            error_window.geometry("500x200")
            error_window.resizable(False, False)
            error_window.attributes('-topmost', True)
            
            # 设置窗口图标
            try:
                icon_paths = [
                    "Bazaar_Lens.ico",
                    os.path.join(os.path.dirname(__file__), "Bazaar_Lens.ico"),
                    os.path.join("icons", "app_icon.ico")
                ]
                for path in icon_paths:
                    if os.path.exists(path):
                        error_window.iconbitmap(path)
                        break
            except Exception:
                pass
                
            # 创建提示信息
            frame = tk.Frame(error_window, padx=20, pady=20)
            frame.pack(fill='both', expand=True)
            
            label = tk.Label(
                frame, 
                text="未找到Tesseract OCR程序，OCR功能将无法使用。\n\n"
                     "请安装Tesseract OCR或从系统托盘菜单中设置正确的路径。\n"
                     "推荐安装版本: 5.5.2（最新版本，性能更好）",
                justify='left',
                wraplength=460
            )
            label.pack(pady=(0, 20))
            
            # 当前路径显示
            path_frame = tk.Frame(frame)
            path_frame.pack(fill='x', pady=(0, 10))
            
            path_label = tk.Label(path_frame, text="当前路径:")
            path_label.pack(side='left')
            
            current_path = tk.Entry(path_frame, width=50)
            current_path.insert(0, self.config.get_tesseract_path())
            current_path.config(state='readonly')
            current_path.pack(side='left', padx=(5, 0), fill='x', expand=True)
            
            # 按钮区域
            button_frame = tk.Frame(frame)
            button_frame.pack(fill='x', pady=(10, 0))
            
            # 下载按钮
            download_button = tk.Button(
                button_frame, 
                text="下载Tesseract OCR", 
                command=lambda: webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
            )
            download_button.pack(side='left', padx=(0, 10))
            
            # 继续按钮
            continue_button = tk.Button(
                button_frame, 
                text="继续使用", 
                command=error_window.destroy
            )
            continue_button.pack(side='right')
            
        except Exception as e:
            logging.error(f"显示Tesseract OCR错误提示时出错: {e}")

    def check_for_updates(self, manual=False):
        """检查更新
        manual: 是否为手动检查更新
        """
        try:
            # 如果不是手动检查，且24小时内已经检查过，则跳过
            if not manual:
                last_check = self.config.get("last_update_check", "")
                if last_check:
                    last_check_time = datetime.datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
                    if datetime.datetime.now() - last_check_time < datetime.timedelta(hours=24):
                        logging.info("24小时内已检查过更新，跳过检查")
                        return

            # 更新检查线程
            update_thread = threading.Thread(target=self._check_updates_thread, args=(manual,))
            update_thread.daemon = True
            update_thread.start()

        except Exception as e:
            logging.error(f"启动更新检查失败: {e}")
            if manual:
                self.system_tray.show_message("错误", "检查更新失败")

    def _check_updates_thread(self, manual):
        """更新检查线程"""
        try:
            # 记录检查时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.config.set("last_update_check", current_time)

            # 获取当前版本
            current_version = VERSION

            # 从服务器获取最新版本信息
            update_info = self._get_latest_version()
            if not update_info:
                if manual:
                    self.system_tray.show_message("更新检查", "当前已是最新版本")
                return

            latest_version = update_info.get("version")
            if not latest_version:
                return

            # 比较版本号
            if self._compare_versions(latest_version, current_version) > 0:
                # 有新版本可用
                self._show_update_dialog(update_info)
            elif manual:
                self.system_tray.show_message("更新检查", "当前已是最新版本")

        except Exception as e:
            logging.error(f"检查更新失败: {e}")
            if manual:
                self.system_tray.show_message("错误", "检查更新失败")

    def _get_latest_version(self):
        """从服务器获取最新版本信息"""
        try:
            # 加载更新配置
            update_config_path = os.path.join(os.path.dirname(__file__), "update_config.json")
            if not os.path.exists(update_config_path):
                logging.error("更新配置文件不存在")
                return None

            with open(update_config_path, 'r', encoding='utf-8') as f:
                update_config = json.load(f)

            # 获取更新API地址
            update_url = update_config.get("update_api")
            if not update_url:
                logging.error("更新API地址未配置")
                return None

            # 创建临时目录
            temp_dir = update_config.get("temp_dir", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            # 发送请求获取最新版本信息
            headers = {
                "User-Agent": "BazaarLens/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.get(update_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                release_info = response.json()
                
                # 解析GitHub Release信息
                update_info = {
                    "version": release_info["tag_name"].lstrip("v"),  # 移除版本号前的'v'
                    "description": release_info["body"],
                    "download_url": release_info["assets"][0]["browser_download_url"],
                    "release_date": release_info["published_at"],
                    "release_title": release_info["name"]
                }
                return update_info
            else:
                logging.error(f"获取更新信息失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            logging.error(f"获取最新版本信息失败: {e}")
            return None

    def _compare_versions(self, version1, version2):
        """比较版本号，返回1表示version1更新，-1表示version2更新，0表示相同"""
        try:
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]
            
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1 = v1_parts[i] if i < len(v1_parts) else 0
                v2 = v2_parts[i] if i < len(v2_parts) else 0
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
        except Exception as e:
            logging.error(f"比较版本号失败: {e}")
            return 0

    def _show_update_dialog(self, update_info):
        """显示更新对话框"""
        try:
            root = tk.Tk()
            root.withdraw()
            
            message = f"发现新版本: {update_info['version']}\n\n"
            message += f"更新说明:\n{update_info.get('description', '无')}\n\n"
            message += "是否现在更新？"
            
            if messagebox.askyesno("发现新版本", message):
                self._download_and_install_update(update_info)
            
            root.destroy()
        except Exception as e:
            logging.error(f"显示更新对话框失败: {e}")

    def _download_and_install_update(self, update_info):
        """下载并安装更新"""
        try:
            # 加载更新配置
            update_config_path = os.path.join(os.path.dirname(__file__), "update_config.json")
            with open(update_config_path, 'r', encoding='utf-8') as f:
                update_config = json.load(f)

            # 创建临时目录和备份目录
            temp_dir = update_config.get("temp_dir", "temp")
            backup_dir = update_config.get("backup_dir", "backups")
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(backup_dir, exist_ok=True)

            # 创建进度条窗口
            progress_window = tk.Toplevel()
            progress_window.title("正在更新")
            progress_window.geometry("300x150")
            progress_window.resizable(False, False)
            
            # 进度标签
            status_label = tk.Label(progress_window, text="正在下载更新...")
            status_label.pack(pady=20)
            
            # 进度条
            progress_bar = ttk.Progressbar(progress_window, length=200, mode='determinate')
            progress_bar.pack(pady=10)
            
            def update_progress(current, total):
                progress = int((current / total) * 100)
                progress_bar['value'] = progress
                status_label.config(text=f"正在下载更新... {progress}%")
                progress_window.update()
            
            # 下载文件
            download_url = update_info['download_url']
            local_file = os.path.join(temp_dir, f"BazaarLens_v{update_info['version']}.exe")
            
            # 设置下载请求头
            headers = {
                "User-Agent": "BazaarLens/1.0"
            }
            
            response = requests.get(download_url, headers=headers, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(local_file, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(chunk_size=4096):
                    downloaded += len(data)
                    f.write(data)
                    update_progress(downloaded, total_size)
            
            # 关闭进度窗口
            progress_window.destroy()
            
            # 备份当前程序
            if update_config.get("auto_backup", True):
                current_exe = os.path.join(os.path.dirname(__file__), "Bazaar_Lens.exe")
                if os.path.exists(current_exe):
                    backup_file = os.path.join(backup_dir, f"Bazaar_Lens_backup_v{VERSION}.exe")
                    shutil.copy2(current_exe, backup_file)
                    logging.info(f"已备份当前版本到: {backup_file}")
            
            # 替换当前程序
            try:
                os.replace(local_file, "Bazaar_Lens.exe")
            except PermissionError:
                # 如果直接替换失败，使用批处理文件在重启后替换
                self._create_update_batch(local_file)
                if messagebox.askyesno("更新准备就绪", "更新文件已准备就绪，需要重启程序才能完成更新。\n是否现在重启？"):
                    self.restart_application()
                return
            
            # 提示重启
            if messagebox.askyesno("更新完成", "更新已完成，需要重启程序才能生效。\n是否现在重启？"):
                self.restart_application()
            
        except Exception as e:
            logging.error(f"下载安装更新失败: {e}")
            messagebox.showerror("错误", "更新失败，请稍后重试")

    def _create_update_batch(self, update_file):
        """创建更新批处理文件"""
        try:
            batch_content = f'''@echo off
:check
tasklist | find /i "Bazaar_Lens.exe" > nul
if errorlevel 1 (
    timeout /t 1 /nobreak
    copy /y "{update_file}" "Bazaar_Lens.exe"
    start "" "Bazaar_Lens.exe"
    del "%~f0"
) else (
    timeout /t 2 /nobreak
    goto check
)
'''
            batch_file = "update.bat"
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            # 启动批处理文件
            subprocess.Popen(['start', 'update.bat'], shell=True)
            
        except Exception as e:
            logging.error(f"创建更新批处理文件失败: {e}")
            raise

    def restart_application(self):
        """重启应用程序"""
        try:
            # 启动新进程
            subprocess.Popen([sys.executable] + sys.argv)
            # 退出当前进程
            self.stop()
            sys.exit(0)
        except Exception as e:
            logging.error(f"重启程序失败: {e}")
            messagebox.showerror("错误", "重启程序失败，请手动重启")

class SystemTray:
    def __init__(self, helper):
        self.helper = helper
        self.icon = None
        self.create_tray_icon()
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            # 创建托盘图标，尝试多个位置查找图标文件
            icon_path = "Bazaar_Lens.ico"
            icon_paths = [
                "Bazaar_Lens.ico",  # 当前目录
                os.path.join(os.path.dirname(__file__), "Bazaar_Lens.ico"),  # 脚本所在目录
                os.path.join(os.path.abspath("."), "Bazaar_Lens.ico"),  # 绝对路径
                os.path.join("icons", "app_icon.ico"),  # icons子目录
            ]
            
            # 尝试不同路径加载图标
            loaded = False
            for path in icon_paths:
                try:
                    if os.path.exists(path):
                        image = Image.open(path)
                        loaded = True
                        logging.info(f"成功加载图标: {path}")
                        break
                except Exception as e:
                    logging.warning(f"尝试加载图标失败: {path}, 错误: {e}")
            
            # 如果所有路径都失败，使用内存中创建的简单图标
            if not loaded:
                logging.warning("无法加载图标文件，使用内存创建的图标")
                # 创建一个简单的彩色图标
                image = Image.new('RGB', (64, 64), color = (73, 109, 137))
            
            # 系统托盘菜单
            menu = (
                pystray.MenuItem("帮助 Help", self.show_help),
                pystray.MenuItem("设置识别安装位置 Set OCR Path", self.set_ocr_path_simple),
                pystray.MenuItem("清理日志文件 Clean Logs", self.clean_log_files),
                pystray.MenuItem("退出 Quit", self.quit_app)
                # 以下选项暂时隐藏
                # pystray.MenuItem("Auto Update", self.toggle_auto_update, checked=lambda item: self.helper.config.get("auto_update", True)),
                # pystray.MenuItem("Check for Updates", self.check_for_updates),
                # pystray.MenuItem("Show Console", self.toggle_console, checked=lambda item: self.helper.config.get("show_console", False)),
                # pystray.MenuItem("Debug Window Detection", self.debug_window_detection),
                # pystray.MenuItem("Debug Icon Loading", self.debug_icon_loading),
                # pystray.MenuItem("Cleanup Legacy Icons", self.cleanup_legacy_icons),
            )
            self.icon = pystray.Icon("BazaarHelper", image, "Bazaar Helper", menu)
            
        except Exception as e:
            logging.error(f"创建系统托盘图标失败: {e}")
            logging.error(traceback.format_exc())

    def toggle_auto_update(self, icon, item):
        """切换自动更新设置"""
        try:
            current_setting = self.helper.config.get("auto_update", True)
            new_setting = not current_setting
            self.helper.config.set("auto_update", new_setting)
            logging.info(f"自动更新设置已更改为: {new_setting}")
            self.show_message("设置已更改", f"自动更新已{'启用' if new_setting else '禁用'}")
        except Exception as e:
            logging.error(f"切换自动更新设置失败: {e}")
            self.show_message("错误", "更改自动更新设置失败")

    def check_for_updates(self, manual=False):
        """手动检查更新"""
        try:
            self.helper.check_for_updates(manual=True)
        except Exception as e:
            logging.error(f"检查更新失败: {e}")
            self.show_message("错误", "检查更新失败")

    def show_help(self, icon, item):
        """显示帮助信息"""
        try:
            # 尝试找到Help.txt文件
            help_file_paths = [
                "Help.txt",  # 当前目录
                os.path.join(os.path.dirname(__file__), "Help.txt"),  # 脚本所在目录
            ]
            
            help_file = None
            for path in help_file_paths:
                if os.path.exists(path):
                    help_file = path
                    break
            
            if help_file:
                # 使用默认文本编辑器打开Help.txt
                if sys.platform == 'win32':
                    os.startfile(help_file)
                else:
                    subprocess.run(['xdg-open', help_file])
                logging.info(f"已打开帮助文件: {help_file}")
            else:
                logging.error("未找到Help.txt文件")
                self.show_help_error()
            
        except Exception as e:
            logging.error(f"显示帮助信息失败: {e}")
            self.show_help_error()

    def show_help_error(self):
        """显示帮助文件加载失败的错误信息"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", "无法打开帮助文件。\n请确保Help.txt文件存在于程序目录中。")
        root.destroy()

    def clean_log_files(self, icon, item):
        """清理日志文件"""
        try:
            # 查找所有日志文件
            log_files = []
            
            # 获取日志文件所在的目录
            log_file_path = get_log_file_path()
            log_dir = os.path.dirname(log_file_path)
            
            # 查找主日志文件和备份文件
            if os.path.exists(log_dir):
                for filename in os.listdir(log_dir):
                    if filename.startswith('bazaar_helper.log'):
                        filepath = os.path.join(log_dir, filename)
                        if os.path.isfile(filepath):
                            size = os.path.getsize(filepath)
                            log_files.append((filename, filepath, size))
            
            if not log_files:
                self.show_message("提示", "没有找到日志文件")
                return
            
            # 计算总大小
            total_size = sum(f[2] for f in log_files)
            size_mb = total_size / (1024 * 1024)
            
            # 显示确认对话框
            root = tk.Tk()
            root.withdraw()
            message = f"找到 {len(log_files)} 个日志文件，总大小: {size_mb:.2f} MB\n"
            message += f"位置: {log_dir}\n\n"
            message += "文件列表:\n"
            for filename, _, size in log_files:
                message += f"  - {filename} ({size/(1024*1024):.2f} MB)\n"
            message += "\n是否要删除这些日志文件？\n\n注意：当前正在使用的日志文件将被清空而不是删除。"
            
            result = messagebox.askyesno("确认清理", message)
            root.destroy()
            
            if result:
                deleted_count = 0
                cleared_count = 0
                failed_count = 0
                
                for filename, filepath, _ in log_files:
                    try:
                        if filename == 'bazaar_helper.log':
                            # 当前使用的日志文件，清空内容而不是删除
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write('')
                            cleared_count += 1
                            logging.info("日志文件已清空")
                        else:
                            # 备份日志文件，直接删除
                            os.remove(filepath)
                            deleted_count += 1
                    except Exception as e:
                        logging.error(f"清理日志文件失败: {filename}, 错误: {e}")
                        failed_count += 1
                
                message = f"清理完成！\n\n"
                if cleared_count > 0:
                    message += f"清空文件: {cleared_count} 个\n"
                if deleted_count > 0:
                    message += f"删除文件: {deleted_count} 个\n"
                if failed_count > 0:
                    message += f"失败: {failed_count} 个\n"
                
                self.show_message("清理完成", message)
            
        except Exception as e:
            logging.error(f"清理日志文件时出错: {e}")
            self.show_message("错误", "清理日志文件失败")
    
    def quit_app(self, icon, item):
        """退出应用程序"""
        try:
            # 先停止图标
            icon.stop()
            # 停止主程序
            if self.helper:
                self.helper.stop()
            # 确保程序完全退出
            os._exit(0)
        except Exception as e:
            logging.error(f"退出程序时出错: {e}")
            os._exit(1)  # 强制退出
    
    def cleanup_legacy_icons(self, icon, item):
        """清理系统托盘中的遗留图标"""
        try:
            self.helper.cleanup_system_tray_icons()
            self.show_message("清理完成", "已清理系统托盘中的遗留图标")
        except Exception as e:
            logging.error(f"清理遗留图标失败: {e}")
            self.show_message("错误", "清理遗留图标失败")
    
    def debug_window_detection(self, icon, item):
        """调试窗口检测"""
        try:
            # 强制重新检测游戏窗口
            hwnd, rect = self.helper.get_game_window()
            
            if hwnd and rect:
                window_text = win32gui.GetWindowText(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                
                # 获取客户端区域
                try:
                    client_rect = win32gui.GetClientRect(hwnd)
                    client_width = client_rect[2]
                    client_height = client_rect[3]
                    client_info = f"客户端区域: {client_width}x{client_height}"
                except:
                    client_info = "无法获取客户端区域"
                
                message = f"""当前检测到的游戏窗口:
标题: {window_text}
窗口坐标: {rect}
窗口尺寸: {width}x{height}
{client_info}

如果窗口尺寸异常小，请尝试：
1. 确保游戏窗口正常显示（不要最小化）
2. 重启游戏
3. 检查游戏是否使用全屏模式"""
                
                self.show_message("窗口检测调试", message)
                logging.info(f"调试窗口检测结果: {window_text}, 尺寸: {width}x{height}, 坐标: {rect}")
            else:
                self.show_message("窗口检测失败", "未找到游戏窗口，请确保游戏正在运行")
                
        except Exception as e:
            logging.error(f"调试窗口检测失败: {e}")
            self.show_message("错误", f"调试窗口检测失败: {e}")
    
    def debug_icon_loading(self, icon, item):
        """调试图标加载"""
        try:
            # 检查图标目录
            # 获取工作目录（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                workspace_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在当前目录下
                workspace_dir = os.path.abspath(os.path.dirname(__file__))
            icon_paths = [
                os.path.join(workspace_dir, '6.0', 'crawlers', 'monster_details_v3', 'icons'),
                os.path.join(workspace_dir, '6.0', 'crawlers', 'event_details_final', 'icons'),
                os.path.join(workspace_dir, 'icons')
            ]
            
            icon_info = []
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    # 对于事件图标目录，需要递归统计子目录中的文件
                    if 'event_details_final' in icon_path:
                        webp_count = 0
                        for root, dirs, files in os.walk(icon_path):
                            webp_count += len([f for f in files if f.endswith('.webp')])
                        icon_info.append(f"✓ {icon_path}: {webp_count} 个 .webp 文件（包含子目录）")
                    else:
                        files = os.listdir(icon_path)
                        webp_files = [f for f in files if f.endswith('.webp')]
                        icon_info.append(f"✓ {icon_path}: {len(webp_files)} 个 .webp 文件")
                else:
                    icon_info.append(f"✗ {icon_path}: 目录不存在")
            
            # 测试怪物图标
            test_monster_icon = "icons/Prince Marianas_Electric Eels.webp"
            test_monster_path = self.helper.get_local_icon_path(test_monster_icon)
            
            # 测试事件图标
            test_event_icon = "icons\\Tiny Furry Monster\\Play Hide and Seek.webp"
            test_event_path = self.helper.get_local_icon_path(test_event_icon)
            
            message = f"""图标目录检查:
{chr(10).join(icon_info)}

测试图标加载:
怪物图标路径: {test_monster_icon}
解析结果: {test_monster_path}
文件存在: {'是' if test_monster_path and os.path.exists(test_monster_path) else '否'}

事件图标路径: {test_event_icon}
解析结果: {test_event_path}
文件存在: {'是' if test_event_path and os.path.exists(test_event_path) else '否'}

图标缓存: {len(self.helper.icon_cache)} 个条目"""
            
            self.show_message("图标加载调试", message)
            logging.info(f"图标调试结果: 缓存{len(self.helper.icon_cache)}个，怪物图标{test_monster_path}，事件图标{test_event_path}")
            
        except Exception as e:
            logging.error(f"调试图标加载失败: {e}")
            self.show_message("错误", f"调试图标加载失败: {e}")
            
    def run(self):
        """运行系统托盘"""
        if self.icon:
            self.icon.run()

    def set_ocr_path_simple(self, icon, item):
        """设置OCR路径"""
        try:
            # 创建临时的顶层窗口作为文件对话框的父窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            # 获取当前OCR路径的目录作为初始目录
            current_path = self.helper.config.get_tesseract_path()
            initial_dir = os.path.dirname(current_path) if os.path.exists(os.path.dirname(current_path)) else "C:/"
            
            # 打开文件选择对话框
            file_path = filedialog.askopenfilename(
                parent=root,
                title="选择 tesseract-ocr.exe 文件",
                filetypes=[("可执行文件", "*.exe")],
                initialdir=initial_dir
            )
            
            # 销毁临时窗口
            root.destroy()
            
            if file_path:
                # 验证选择的文件是否为tesseract.exe
                if os.path.basename(file_path).lower() == "tesseract.exe":
                    # 更新配置
                    if self.helper.config.set_tesseract_path(file_path):
                        # 更新全局路径
                        pytesseract.pytesseract.tesseract_cmd = file_path
                        # 提示成功
                        logging.info(f"Tesseract OCR路径已设置为: {file_path}")
                        # 显示成功消息
                        self.show_message("设置成功", f"Tesseract OCR路径已设置为:\n{file_path}")
                        return True
                    else:
                        logging.error("保存OCR路径配置失败")
                        self.show_message("错误", "保存OCR路径配置失败")
                else:
                    logging.error("选择的文件不是tesseract.exe")
                    self.show_message("错误", "请选择正确的tesseract.exe文件")
            return False
        except Exception as e:
            logging.error(f"设置OCR路径时出错: {e}")
            logging.error(traceback.format_exc())  # 添加详细错误信息

    def show_message(self, title, message):
        """显示消息对话框"""
        try:
            # 创建临时的顶层窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            # 显示消息
            messagebox.showinfo(title, message, parent=root)
            
            # 销毁临时窗口
            root.destroy()
        except Exception as e:
            logging.error(f"显示消息时出错: {e}")
            logging.error(traceback.format_exc())  # 添加详细错误信息

    def toggle_console(self, icon, item):
        """切换控制台显示状态"""
        try:
            current_setting = self.helper.config.get("show_console", False)
            new_setting = not current_setting
            self.helper.config.set("show_console", new_setting)
            
            if new_setting:
                show_console()
            else:
                hide_console()
                
            logging.info(f"控制台显示设置已更改为: {new_setting}")
        except Exception as e:
            logging.error(f"切换控制台显示状态失败: {e}")
            self.show_message("错误", "更改控制台显示设置失败")

def kill_existing_processes():
    """杀死所有已存在的 Bazaar_Lens.exe 进程（除了当前进程）"""
    try:
        current_pid = os.getpid()
        killed_count = 0
        
        # 获取当前可执行文件的名称
        current_exe_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else __file__)
        if not current_exe_name.endswith('.exe'):
            current_exe_name = 'Bazaar_Lens.exe'  # 打包后的名称
        
        logging.info(f"当前进程PID: {current_pid}, 可执行文件名: {current_exe_name}")
        
        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                # 跳过当前进程
                if proc.pid == current_pid:
                    continue
                
                # 检查进程名是否匹配
                proc_name = proc.info.get('name', '')
                if proc_name and current_exe_name.lower() in proc_name.lower():
                    logging.info(f"发现已存在的进程: PID={proc.pid}, Name={proc_name}")
                    # 终止进程
                    proc.terminate()
                    # 等待进程结束（最多3秒）
                    try:
                        proc.wait(timeout=3)
                        logging.info(f"成功终止进程: PID={proc.pid}")
                        killed_count += 1
                    except psutil.TimeoutExpired:
                        # 如果进程没有在3秒内结束，强制杀死
                        proc.kill()
                        logging.info(f"强制杀死进程: PID={proc.pid}")
                        killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logging.warning(f"处理进程时出错: {e}")
                continue
        
        if killed_count > 0:
            logging.info(f"已终止 {killed_count} 个已存在的进程")
            # 等待一小段时间确保资源释放
            time.sleep(0.5)
        else:
            logging.info("没有发现已存在的进程")
            
        return killed_count
        
    except Exception as e:
        logging.error(f"杀死已存在进程时出错: {e}")
        return 0

if __name__ == "__main__":
    helper = None
    mutex = None
    
    try:
        # 显示控制台窗口
        hide_console()
        
        # 检查管理员权限
        if not is_admin():
            run_as_admin()
        else:
            # 杀死已存在的进程
            logging.info("检查并终止已存在的进程...")
            killed = kill_existing_processes()
            if killed > 0:
                logging.info(f"已终止 {killed} 个旧进程，现在启动新进程")
            
            # 创建互斥锁（仅用于标记当前实例）
            mutex_name = "BazaarLens_SingleInstance"
            try:
                mutex = win32event.CreateMutex(None, False, mutex_name)
                last_error = win32api.GetLastError()
                if last_error == winerror.ERROR_ALREADY_EXISTS:
                    logging.info("检测到互斥锁已存在，但旧进程应该已被终止")
                else:
                    logging.info("成功创建互斥锁")
            except Exception as e:
                logging.warning(f"创建互斥锁失败，继续运行: {e}")
                mutex = None
            
            # 创建并隐藏 tk 根窗口
            root = tk.Tk()
            root.withdraw()
            
            # 创建主程序实例
            helper = BazaarHelper()
            
            # 创建并运行系统托盘（在新线程中运行）
            tray_thread = threading.Thread(target=lambda: helper.system_tray.run(), daemon=True)
            tray_thread.start()
            
            # 运行主程序
            helper.run()
            
    except KeyboardInterrupt:
        logging.info("接收到键盘中断信号")
        pass
    except Exception as e:
        logging.error(f"主程序异常: {e}")
        logging.error(traceback.format_exc())
    finally:
        # 释放互斥锁和资源
        if helper:
            try:
                helper.stop()
            except Exception as e:
                logging.error(f"停止helper时出错: {e}")
        
        if mutex:
            try:
                win32api.CloseHandle(mutex)
            except Exception as e:
                logging.error(f"关闭互斥锁时出错: {e}")
        
        # 使用sys.exit代替os._exit以允许清理
        sys.exit(0) 