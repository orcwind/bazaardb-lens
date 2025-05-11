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

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bazaar_helper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
        return pytesseract.image_to_string(
            img,
            config='--psm 6 --oem 3 -l eng'
        ).strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

# 添加不使用进程池的OCR函数
def direct_ocr(img_bytes):
    """直接在当前线程执行OCR，不使用进程池"""
    from PIL import Image
    import pytesseract
    import io
    try:
        # 使用全局设置的tesseract_cmd路径
        img = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(
            img,
            config='--psm 6 --oem 3 -l eng'
        ).strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

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
            input("按Enter键退出...")
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
            
            # 描述左对齐
            if description:
                self.desc_label.config(text=description, anchor='w', justify='left', bg=bg_color)
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
        self.default_config = {
            "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
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
        self.ctrl_pressed = False
        self.last_check_time = time.time()
        self.check_interval = 0.1  # 缩短检查间隔到0.1秒
        self.is_running = True
        self.info_window = None
        self.current_text = None
        self.monster_data = {}
        self.event_data = {}
        
        # 添加配置管理器
        self.config = ConfigManager()
        
        # 添加OCR线程锁
        self.ocr_lock = threading.Lock()
        
        # 检测运行环境
        self.is_packaged = is_packaged_environment()
        if self.is_packaged:
            logging.info("检测到打包环境，使用简化OCR策略")
        else:
            logging.info("检测到开发环境，使用标准OCR策略")
            
        # 检查OCR依赖
        if not self.check_tesseract():
            self.show_tesseract_error()
        
        # 加载数据
        self.load_monster_data()
        self.load_event_data()
        
        # 创建信息窗口（但保持隐藏状态）
        self.create_info_window()
        
        # 启动保活线程
        self.keep_alive_thread = threading.Thread(target=self.keep_alive, daemon=True)
        self.keep_alive_thread.start()

        # 创建系统托盘
        self.system_tray = SystemTray(self)

        # 启动自动更新检查
        if self.config.get("auto_update", True):
            self.check_for_updates()

        # 根据配置决定是否显示控制台
        if not self.config.get("show_console", False):
            hide_console()

    def keep_alive(self):
        """保活机制，检查Ctrl键状态和程序响应"""
        VK_CONTROL = 0x11  # Ctrl键的虚拟键码
        last_action_time = 0  # 上次执行动作的时间
        debounce_delay = 0.5  # 防抖动延迟(秒)
        
        while self.is_running:
            try:
                current_time = time.time()
                # 使用win32api检查Ctrl键状态
                ctrl_state = win32api.GetAsyncKeyState(VK_CONTROL)
                is_ctrl_pressed = (ctrl_state & 0x8000) != 0
                
                # Ctrl键状态发生变化
                if is_ctrl_pressed != self.ctrl_pressed:
                    self.ctrl_pressed = is_ctrl_pressed
                    if is_ctrl_pressed:
                        # 添加防抖动: 检查距离上次动作的时间是否足够
                        if current_time - last_action_time >= debounce_delay:
                            # Ctrl键被按下，获取并显示信息
                            text = self.get_text_at_cursor()
                            if text:
                                x, y = pyautogui.position()
                                self.update_info_display(text, x, y)
                                last_action_time = current_time
                    else:
                        # Ctrl键释放，立即隐藏信息
                        if self.info_window and self.info_window.winfo_exists():
                            self.info_window.withdraw()
                
                # 更新窗口位置（如果窗口显示中且Ctrl键仍然按下）
                if self.ctrl_pressed and self.info_window and self.info_window.winfo_exists():
                    x, y = pyautogui.position()
                    self.adjust_window_size(x, y)
                
                # 短暂休眠以减少CPU使用
                time.sleep(0.01)
                
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

    def load_monster_data(self):
        """加载怪物数据"""
        try:
            with open('data/monsters.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.monster_data = {monster['name']: monster for monster in data['monsters']}
            logging.info(f"成功加载怪物数据，共 {len(self.monster_data)} 个怪物")
        except Exception as e:
            logging.error(f"加载怪物数据失败: {e}")
            self.monster_data = {}

    def load_event_data(self):
        """加载事件数据"""
        try:
            with open('data/events.json', 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                logging.info(f"已加载 {len(self.events)} 个事件")
            # 直接从 events.json 提取所有事件选项
            self.event_data = {}
            for event in self.events:
                if 'name' in event and 'options' in event:
                    self.event_data[event['name']] = event['options']
                else:
                    logging.warning(f"事件 {event.get('name', '')} 缺少 options 字段")
        except Exception as e:
            logging.error(f"加载事件数据时出错: {e}")
            self.events = []
            self.event_data = {}

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        try:
            hwnd = win32gui.FindWindow(None, "The Bazaar")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 11")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 12")
                
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
                logging.debug(f"找到游戏窗口: {rect}")
                return hwnd, rect
                
            logging.warning("未找到游戏窗口")
            return None, None
        except Exception as e:
            logging.error(f"获取游戏窗口失败: {e}")
            return None, None

    def preprocess_image(self, img):
        """图像预处理优化"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # 二值化
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # 保存二值化图像用于调试
            cv2.imwrite('debug_binary.png', binary)
            
            return binary
            
        except Exception as e:
            logging.error(f"图像预处理失败: {e}")
            return img

    def ocr_with_timeout(self, processed_img, timeout=3):
        """使用超时机制执行OCR，避免使用进程池"""
        # 使用线程锁防止并发调用
        if not self.ocr_lock.acquire(blocking=False):
            logging.info("OCR已在进行中，跳过本次识别")
            return None
            
        try:
            # 准备图像数据
            buf = io.BytesIO()
            Image.fromarray(processed_img).save(buf, format='PNG')
            img_bytes = buf.getvalue()
            
            # 根据环境选择OCR策略
            if getattr(self, 'is_packaged', False):
                # 打包环境使用直接调用
                try:
                    return direct_ocr(img_bytes)
                except Exception as e:
                    logging.error(f"直接OCR调用失败: {e}")
                    return None
            else:
                # 开发环境使用线程超时
                # 初始化结果变量和事件
                result = [None]  # 使用列表存储结果，便于线程间共享
                ocr_done = threading.Event()
                
                # 定义OCR线程
                def ocr_thread():
                    try:
                        # 直接在线程中执行OCR，不使用进程池
                        ocr_result = direct_ocr(img_bytes)
                        result[0] = ocr_result
                        ocr_done.set()
                    except Exception as e:
                        logging.error(f"OCR线程异常: {e}")
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
            return None
        finally:
            # 确保释放锁
            self.ocr_lock.release()

    def find_best_match(self, text):
        """统一识别怪物或事件，返回('monster'/'event', 名称)或(None, None)"""
        if not text:
            return None, None
            
        def clean_text(s):
            if not isinstance(s, str):
                return ""
            # 保留字母和空格，移除其他字符
            s = re.sub(r'[^a-zA-Z\s]', ' ', s)
            # 合并多个空格为单个空格并转小写
            return ' '.join(s.split()).lower()
            
        # 只保留长度>=3的行
        lines = [clean_text(line.strip()) for line in str(text).split('\n') if len(clean_text(line.strip())) >= 3]
        logging.info(f"OCR文本行: {lines}")
        
        best_type = None
        best_name = None
        best_ratio = 0.0
        
        # 记录所有匹配结果用于调试
        all_matches = []
        
        for monster_name in self.monster_data:
            monster_clean = clean_text(monster_name)
            for line in lines:
                # 完全匹配
                if line == monster_clean:
                    logging.info(f"找到完全匹配的怪物: {monster_name}")
                    return 'monster', monster_name
                    
                # 包含匹配（检查单词级别的匹配）
                monster_words = set(monster_clean.split())
                line_words = set(line.split())
                common_words = monster_words & line_words
                
                if len(common_words) > 0:
                    # 如果有共同单词，计算相似度
                    ratio = difflib.SequenceMatcher(None, line, monster_clean).ratio()
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
                        
        for event in self.events:
            event_clean = clean_text(event['name'])
            for line in lines:
                if line == event_clean:
                    logging.info(f"找到完全匹配的事件: {event['name']}")
                    return 'event', event['name']
                    
                # 对事件也使用相同的单词级别匹配
                event_words = set(event_clean.split())
                line_words = set(line.split())
                common_words = event_words & line_words
                
                if len(common_words) > 0:
                    ratio = difflib.SequenceMatcher(None, line, event_clean).ratio()
                    all_matches.append({
                        'type': 'event',
                        'name': event['name'],
                        'line': line,
                        'ratio': ratio,
                        'common_words': list(common_words)
                    })
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_type = 'event'
                        best_name = event['name']
        
        # 输出所有匹配结果用于调试
        logging.info("所有匹配结果:")
        for match in sorted(all_matches, key=lambda x: x['ratio'], reverse=True)[:5]:
            logging.info(f"- {match['type']}: {match['name']}")
            logging.info(f"  行: {match['line']}")
            logging.info(f"  相似度: {match['ratio']:.2f}")
            logging.info(f"  共同单词: {match['common_words']}")
        
        # 降低匹配阈值，但要求至少有一个共同单词
        if best_ratio > 0.6:
            logging.info(f"找到最佳匹配: {best_type} - {best_name} (相似度: {best_ratio:.2f})")
            return best_type, best_name
            
        logging.info("未找到足够相似的匹配")
        return None, None

    def get_text_at_cursor(self):
        """获取鼠标指向位置的文字"""
        try:
            # 获取游戏窗口
            hwnd, window_rect = self.get_game_window()
            if not hwnd or not window_rect:
                logging.warning("未找到游戏窗口")
                return None

            # 获取鼠标位置
            cursor_x, cursor_y = win32gui.GetCursorPos()
            
            # 计算鼠标相对于窗口的位置
            relative_x = cursor_x - window_rect[0]
            relative_y = cursor_y - window_rect[1]
            
            # 定义截图区域（以鼠标位置为左边界，其他边界为游戏窗口）
            x1 = cursor_x  # 鼠标位置作为左边界
            y1 = window_rect[1]  # 窗口上边界
            x2 = window_rect[2]  # 窗口右边界
            y2 = window_rect[3]  # 窗口下边界

            # 截取区域图像
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception as e:
                logging.error(f'截图失败: {e}')
                return None
            img_array = np.array(screenshot)
            
            # 保存调试图像
            debug_img = img_array.copy()
            # 在调试图像上画一个红色十字光标
            center_x = relative_x - (x1 - window_rect[0])
            center_y = relative_y - (y1 - window_rect[1])
            cv2.line(debug_img, (center_x-10, center_y), (center_x+10, center_y), (0,0,255), 2)
            cv2.line(debug_img, (center_x, center_y-10), (center_x, center_y+10), (0,0,255), 2)
            cv2.imwrite('debug_capture.png', cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
            
            # 预处理图像
            processed_img = self.preprocess_image(img_array)
            
            # OCR识别
            text = self.ocr_with_timeout(processed_img, timeout=3)
            logging.debug(f"OCR原始识别结果:\n{text}")
            
            # 如果识别结果为空，尝试其他PSM模式
            if not text:
                logging.debug("尝试其他PSM模式")
                psm_modes = [3, 4, 7, 11]  # 尝试不同的页面分割模式
                for psm in psm_modes:
                    text = self.ocr_with_timeout(processed_img, timeout=3)
                    if text:
                        logging.debug(f"使用PSM {psm}成功识别文本")
                        break
            
            return text if text else None
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def create_info_window(self):
        """创建信息窗口"""
        try:
            # 创建主窗口
            self.info_window = tk.Toplevel()
            self.info_window.title("The Bazaar Helper")
            self.info_window.attributes('-alpha', 0.95)  # 设置透明度
            self.info_window.overrideredirect(True)  # 无边框窗口
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
        # 只清空子元素，不destroy主Frame本身
        for widget in self.event_options_frame.winfo_children():
            widget.destroy()
        for widget in self.skills_frame.winfo_children():
            widget.destroy()
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        # 控制框架的显示/隐藏
        self.event_options_frame.pack_forget()
        self.skills_frame.pack_forget()
        self.items_frame.pack_forget()
        # 清理content_frame下的所有spacer（Frame），只destroy不是三大主Frame的spacer
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget not in [self.event_options_frame, self.skills_frame, self.items_frame]:
                widget.destroy()

    def get_local_icon_path(self, icon_url, icons_dir='icons'):
        """始终从工作目录下的icons文件夹获取图标，找不到则自动下载"""
        if not icon_url or not icon_url.startswith('http'):
            logging.warning(f"无效的图标URL: {icon_url}")
            return None

        try:
            # 清理文件名，移除查询参数
            parsed_url = urlparse(icon_url)
            filename = os.path.basename(parsed_url.path)
            # 允许@字符
            filename = re.sub(r'[^\w\-_.@]', '_', filename)

            # 只用工作目录下的 icons 文件夹
            workspace_dir = os.path.abspath(os.path.dirname(__file__))  # 当前脚本所在目录
            icons_path = os.path.join(workspace_dir, icons_dir)
            icon_file_path = os.path.join(icons_path, filename)

            logging.debug(f"查找本地图标路径: {icon_file_path}")
            if os.path.exists(icon_file_path):
                logging.debug(f"找到本地图标: {icon_file_path}")
                return icon_file_path

            # 本地没有，尝试下载
            logging.debug(f"开始下载图标: {icon_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(icon_url, headers=headers, timeout=10, verify=False)
            if resp.status_code == 200:
                os.makedirs(icons_path, exist_ok=True)
                with open(icon_file_path, 'wb') as f:
                    f.write(resp.content)
                logging.debug(f"图标下载成功: {icon_file_path}")
                return icon_file_path
            else:
                logging.warning(f"下载图标失败，状态码: {resp.status_code}")
                return None

        except Exception as e:
            logging.error(f"处理图标失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def format_monster_info(self, monster_name):
        """格式化怪物信息显示"""
        try:
            if not monster_name:
                return False
                
            if monster_name not in self.monster_data:
                logging.warning(f"未找到怪物数据: {monster_name}")
                self.clear_frames()
                # 显示未找到数据的提示
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                not_found_frame = IconFrame(self.skills_frame)
                not_found_frame.pack(fill='x', pady=0)
                not_found_frame.update_content(
                    monster_name,
                    "未找到该怪物的数据，请稍后再试。",
                    None
                )
                return True
                
            monster = self.monster_data[monster_name]
            logging.debug(f"怪物数据: {monster}")
            self.clear_frames()
            
            has_skills = False
            # 显示技能
            if monster.get('skills'):
                has_skills = True
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                for skill in monster['skills']:
                    skill_frame = IconFrame(self.skills_frame)
                    skill_frame.pack(fill='x', pady=0)
                    # 获取技能图标
                    icon_path = None
                    if skill.get('icon'):
                        icon_path = self.get_local_icon_path(skill['icon'])
                    aspect_ratio = float(skill.get('aspect_ratio', 1.0))
                    skill_frame.update_content(
                        skill.get('name', ''),
                        skill.get('description', ''),
                        icon_path,
                        aspect_ratio
                    )
                    
            # 显示物品
            if monster.get('items'):
                if has_skills:
                    # 添加分隔条
                    separator = tk.Frame(self.content_frame, height=2, bg='#3A7BBA')
                    separator.pack(fill='x', pady=5, padx=10)
                
                self.items_frame.pack(fill='x', pady=0, padx=0)
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
                        
                    # 处理物品名称（如果有多个相同物品，显示数量）
                    display_name = item_name
                    if items_count[item_name] > 1:
                        display_name = f"{item_name} x{items_count[item_name]}"
                        
                    # 获取物品图标
                    icon_path = None
                    if item.get('icon'):
                        icon_path = self.get_local_icon_path(item['icon'])
                    aspect_ratio = float(item.get('aspect_ratio', 1.0))
                    item_frame.update_content(
                        display_name,
                        item.get('description', ''),
                        icon_path,
                        aspect_ratio
                    )
                    
            # 如果既没有技能也没有物品，显示提示信息
            if not monster.get('skills') and not monster.get('items'):
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                not_found_frame = IconFrame(self.skills_frame)
                not_found_frame.pack(fill='x', pady=0)
                not_found_frame.update_content(
                    monster_name,
                    "该怪物没有技能和物品数据。",
                    None
                )
                
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
            if event_name not in self.event_data:
                logging.error(f"找不到事件选项数据: {event_name}")
                return False

            options = self.event_data[event_name]
            if not options:
                logging.error(f"事件选项数据为空: {event_name}")
                return False

            # 清除现有内容
            self.clear_frames()

            # 显示事件选项框架
            self.event_options_frame.pack(fill='x', pady=0)

            for option in options:
                icon_path = None
                if option.get('icon'):
                    icon_path = self.get_local_icon_path(option['icon'])
                option_frame = IconFrame(self.event_options_frame)
                option_frame.pack(fill='x', pady=0)
                option_frame.update_content(
                    option.get('name', ''),
                    option.get('description', ''),
                    icon_path
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

    def update_info_display(self, text, pos_x, pos_y):
        """更新信息显示（统一怪物/事件识别），每次都重建窗口"""
        try:
            # 销毁旧窗口
            self.destroy_info_window()
            
            # 创建新窗口
            self.create_info_window()
            
            logging.debug(f"开始更新信息显示，OCR文本: {text}")
            match_type, match_name = self.find_best_match(text)
            
            display_success = False
            if match_type == 'event':
                display_success = self.format_event_info(match_name)
            elif match_type == 'monster':
                display_success = self.format_monster_info(match_name)
                
            if not display_success:
                if match_type:
                    self.show_info_message(f"未找到该{match_type}的数据，请稍后再试。", None)
                else:
                    self.show_info_message("未能识别到怪物或事件名称。", None)
                return
                
            # 设置初始位置
            self.info_window.geometry(f"+{pos_x}+{pos_y}")
            
            # 更新所有挂起的空闲任务
            self.info_window.update()
            self.content_frame.update()
            self.content_frame.update_idletasks()
            
            # 调整窗口大小
            self.adjust_window_size(pos_x, pos_y)
            
            # 显示窗口并置顶
            if self.ctrl_pressed:  # 只在Ctrl键按下时显示窗口
                self.info_window.deiconify()
                self.info_window.lift()
                self.info_window.attributes('-topmost', True)
            
            logging.debug(f"{match_type}信息显示完成，位置: {pos_x}, {pos_y}")
            
        except Exception as e:
            logging.error(f"信息显示异常: {e}")
            logging.error(traceback.format_exc())

    def hide_info(self):
        """隐藏信息窗口"""
        try:
            if self.info_window:
                self.info_window.withdraw()
        except Exception as e:
            logging.error(f"隐藏信息窗口失败: {e}")

    def show_info_message(self, message, icon_url):
        # 实现显示信息消息的逻辑
        print(f"显示信息消息: {message}")

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
        """检查Tesseract OCR是否可用"""
        try:
            # 获取配置中的Tesseract路径
            tesseract_path = self.config.get_tesseract_path()
            
            # 检查文件是否存在
            if os.path.exists(tesseract_path) and os.path.isfile(tesseract_path):
                # 设置全局路径
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logging.info(f"Tesseract OCR路径设置为: {tesseract_path}")
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
                     "推荐安装版本: tesseract-ocr-w64-setup-5.5.0.20241111.exe",
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
            
            # 添加自动更新菜单项
            menu = (
                pystray.MenuItem("Help", self.show_help),
                pystray.MenuItem("Set tesseract-ocr.exe Path", self.set_ocr_path_simple),
                pystray.MenuItem("Auto Update", self.toggle_auto_update, checked=lambda item: self.helper.config.get("auto_update", True)),
                pystray.MenuItem("Check for Updates", self.check_for_updates),
                pystray.MenuItem("Show Console", self.toggle_console, checked=lambda item: self.helper.config.get("show_console", False)),
                pystray.MenuItem("Quit", self.quit_app)
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

if __name__ == "__main__":
    # 防止多次启动
    # 创建互斥锁
    mutex_name = "Global\\BazaarLens_SingleInstance"
    mutex = win32event.CreateMutex(None, False, mutex_name)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        logging.warning("程序已经在运行！")
        sys.exit(0)
    
    helper = None
    try:
        # 显示控制台窗口
        hide_console()
        
        if not is_admin():
            run_as_admin()
        else:
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
        pass
    finally:
        # 释放互斥锁和资源
        if helper:
            helper.stop()
        # 使用sys.exit代替os._exit以允许清理
        sys.exit(0) 