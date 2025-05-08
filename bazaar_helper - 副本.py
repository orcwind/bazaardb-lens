# 标准库导入
import os
import sys
import json
import logging
import traceback
import re
import difflib
from urllib.parse import urlparse

# 第三方库导入
import keyboard
import win32gui
import requests
import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import win32con
import win32api
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageDraw, ImageFont
import pytesseract
import time
from tkinter import ttk
import ctypes
from ctypes import wintypes
import win32com.client
import threading
import concurrent.futures
import io
import tempfile
import subprocess
import pystray
import webbrowser

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG 级别以获取更多信息
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bazaar_helper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # 添加控制台输出
    ]
)

# 顶层定义ocr_task，确保无缩进
def ocr_task(img_bytes):
    from PIL import Image
    import pytesseract
    import io
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        img = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(
            img,
            config='--psm 6 --oem 3 -l eng'
        ).strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

def check_dependencies():
    """检查必要的依赖和文件"""
    try:
        # 检查 Tesseract
        if not os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
            logging.error("错误：未安装 Tesseract-OCR")
            return False
            
        # 检查字体文件
        if not os.path.exists(os.path.join(os.environ['WINDIR'], 'Fonts', 'msyh.ttc')):
            logging.warning("警告：找不到微软雅黑字体，将使用默认字体")
            
        return True
    except Exception as e:
        logging.error(f"检查依赖时出错: {e}")
        return False

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
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{__file__}"', None, 1
        )

class IconFrame(tk.Frame):
    """用于显示图标和文本的框架"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # 获取父容器的背景色，如果没有指定则使用默认的浅蓝色
        parent_bg = parent.cget('bg') if parent else '#E6F0FF'
        self.configure(bg=parent_bg, bd=0, highlightthickness=0)
        
        # 创建左侧图标容器，固定宽度
        self.icon_container = tk.Frame(self, bg=parent_bg, width=144, height=96, bd=0, highlightthickness=0)
        self.icon_container.pack_propagate(False)
        self.icon_container.pack(side='left', padx=0, pady=0)
        
        # 创建图标标签
        self.icon_label = tk.Label(self.icon_container, bg=parent_bg, bd=0, highlightthickness=0)
        self.icon_label.pack(expand=True)
        
        # 创建右侧文本容器
        self.text_frame = tk.Frame(self, bg=parent_bg, bd=0, highlightthickness=0)
        self.text_frame.pack(side='left', fill='both', expand=True, padx=0, pady=0)
        
        # 创建名称标签
        self.name_label = tk.Label(
            self.text_frame,
            font=('Segoe UI', 14, 'bold'),
            fg='#000000',  # 深色背景使用白色文字
            bg=parent_bg,
            anchor='w',
            justify='left',
            bd=0,
            highlightthickness=0
        )
        self.name_label.pack(fill='x', anchor='w', pady=0)
        
        # 创建描述标签
        self.desc_label = tk.Label(
            self.text_frame,
            font=('Segoe UI', 13),
            fg='#333333',  # 浅色背景使用深灰色文字
            bg=parent_bg,
            anchor='w',
            wraplength=400,
            justify='left',
            bd=0,
            highlightthickness=0
        )
        self.desc_label.pack(fill='both', expand=True, anchor='w')
        
        # 保存当前图像
        self.current_photo = None
        self._photo_refs = []  # 用于保存所有PhotoImage对象的引用

    def update_content(self, name, description, icon_path=None, aspect_ratio=1.0):
        try:
            # 获取当前背景色
            bg_color = self.cget('bg')
            
            # 名称左对齐
            if name:
                self.name_label.config(text=name, anchor='w', justify='left', bg=bg_color)
                self.name_label.pack(fill='x', anchor='w', pady=0)
            else:
                self.name_label.pack_forget()
            
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

class SystemTray:
    def __init__(self, helper):
        self.helper = helper
        self.create_tray_icon()
        
    def create_tray_icon(self):
        # 创建托盘图标菜单
        menu = (
            pystray.MenuItem("说明", self.show_info),
            pystray.MenuItem("关闭", self.quit_app)
        )
        
        # 加载图标
        try:
            icon_image = Image.open("Bazaar_Lens.ico")
        except Exception as e:
            logging.error(f"加载图标失败: {e}")
            # 创建一个默认的图标
            icon_image = Image.new('RGB', (64, 64), color='#1A0F0A')
            
        # 创建系统托盘图标
        self.icon = pystray.Icon(
            "BazaarHelper",
            icon_image,
            "Bazaar Helper",
            menu
        )
        
    def run(self):
        self.icon.run()
        
    def quit_app(self, icon, item):
        """退出应用程序"""
        try:
            logging.info("正在退出系统托盘...")
            # 先停止图标
            icon.stop()
            # 停止主程序
            if self.helper:
                self.helper.stop()
            # 确保程序完全退出
            logging.info("程序退出")
            os._exit(0)
        except Exception as e:
            logging.error(f"退出程序时出错: {e}")
            os._exit(1)  # 强制退出
        
    def show_info(self, icon, item):
        # 创建说明窗口
        info_window = tk.Toplevel()
        info_window.title("Bazaar Helper 说明")
        info_window.geometry("400x200")
        
        # 设置窗口图标
        try:
            info_window.iconbitmap("Bazaar_Lens.ico")
        except Exception as e:
            logging.error(f"设置窗口图标失败: {e}")
            
        # 窗口置顶
        info_window.attributes('-topmost', True)
        
        # 创建文本框
        text = tk.Text(info_window, wrap=tk.WORD, font=('Segoe UI', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 读取说明文件内容
        try:
            with open('Info.txt', 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = "无法读取说明文件"
            logging.error(f"读取说明文件失败: {e}")
            
        # 显示内容
        text.insert('1.0', content)
        text.config(state='disabled')  # 设置为只读
        
        # 居中显示窗口
        info_window.update_idletasks()
        width = info_window.winfo_width()
        height = info_window.winfo_height()
        x = (info_window.winfo_screenwidth() // 2) - (width // 2)
        y = (info_window.winfo_screenheight() // 2) - (height // 2)
        info_window.geometry(f'{width}x{height}+{x}+{y}')

class BazaarHelper:
    def __init__(self):
        """初始化BazaarHelper"""
        # 创建并隐藏根窗口
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏根窗口
        
        self.alt_pressed = False
        self.last_check_time = time.time()
        self.check_interval = 0.1  # 缩短检查间隔到0.1秒
        self.is_running = True
        self.info_window = None
        self.current_text = None
        self.monster_data = {}
        self.event_data = {}
        
        # 加载数据
        self.load_monster_data()
        self.load_event_data()
        
        # 创建信息窗口
        self.create_info_window()
        
        # 创建系统托盘
        self.system_tray = SystemTray(self)
        
        # 启动保活线程
        self.keep_alive_thread = threading.Thread(target=self.keep_alive, daemon=True)
        self.keep_alive_thread.start()
        
        # 启动系统托盘线程
        self.tray_thread = threading.Thread(target=self.system_tray.run, daemon=True)
        self.tray_thread.start()

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        try:
            hwnd = win32gui.FindWindow(None, "The Bazaar")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 11")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 12")
                
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                return hwnd, rect
            return None, None
            
        except Exception as e:
            logging.error(f"获取游戏窗口失败: {e}")
            return None, None

    def keep_alive(self):
        """保活机制，检查Alt键状态和程序响应"""
        VK_MENU = 0x12  # Alt键的虚拟键码
        
        while self.is_running:
            try:
                # 检查Alt键状态
                alt_state = win32api.GetAsyncKeyState(VK_MENU)
                is_alt_pressed = (alt_state & 0x8000) != 0
                
                # Alt键状态发生变化
                if is_alt_pressed != self.alt_pressed:
                    self.alt_pressed = is_alt_pressed
                    if is_alt_pressed:
                        # Alt键被按下，获取并显示信息
                        text = self.get_text_at_cursor()
                        if text:
                            x, y = pyautogui.position()
                            self.update_info_display(text, x, y)
                    else:
                        # Alt键释放，隐藏信息
                        self.hide_info()
                
                time.sleep(0.01)  # 短暂休眠
                
            except Exception as e:
                logging.error(f"保活线程异常: {e}")
                time.sleep(0.1)
                continue

    def get_text_at_cursor(self):
        """获取鼠标指向位置的文字"""
        try:
            # 获取游戏窗口
            hwnd, window_rect = self.get_game_window()
            if not hwnd or not window_rect:
                return None

            # 获取鼠标位置
            cursor_x, cursor_y = win32gui.GetCursorPos()
            
            # 计算截图区域
            x1 = cursor_x
            y1 = window_rect[1]
            x2 = window_rect[2]
            y2 = window_rect[3]

            # 截取区域图像
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception as e:
                logging.error(f'截图失败: {e}')
                return None
                
            img_array = np.array(screenshot)
            processed_img = self.preprocess_image(img_array)
            
            # OCR识别
            text = self.ocr_with_timeout(processed_img)
            return text if text else None
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            return None

    def ocr_with_timeout(self, processed_img):
        """OCR识别"""
        try:
            buf = io.BytesIO()
            Image.fromarray(processed_img).save(buf, format='PNG')
            img_bytes = buf.getvalue()
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(ocr_task, img_bytes)
                try:
                    return future.result(timeout=1.0)
                except Exception as e:
                    logging.error(f"OCR识别失败: {e}")
                    return None
                    
        except Exception as e:
            logging.error(f"OCR处理失败: {e}")
            return None

    def create_info_window(self):
        """创建信息窗口"""
        try:
            # 创建主窗口
            self.info_window = tk.Toplevel(self.root)  # 使用root作为父窗口
            self.info_window.withdraw()  # 先隐藏窗口
            
            # 设置为无边框、透明、置顶的窗口
            self.info_window.overrideredirect(True)  # 无边框窗口
            self.info_window.attributes('-alpha', 0.95)  # 设置透明度
            self.info_window.attributes('-topmost', True)  # 保持在顶层
            
            # Windows系统特定设置，确保窗口不在任务栏显示
            if sys.platform == 'win32':
                # 设置扩展样式
                hwnd = self.info_window.winfo_id()
                exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                exstyle |= win32con.WS_EX_TOOLWINDOW  # 添加工具窗口样式
                exstyle &= ~win32con.WS_EX_APPWINDOW  # 移除应用程序窗口样式
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)
            
            # 设置窗口背景色
            self.info_window.configure(bg='#E6F0FF')  # 默认浅蓝色背景
            
            # 创建主容器（无边框）
            self.content_frame = tk.Frame(self.info_window, bg='#E6F0FF', bd=0, highlightthickness=0)
            self.content_frame.pack(fill='both', expand=True, padx=0, pady=0)
            
            # 创建事件选项容器（浅蓝色，无边框）
            self.event_options_frame = tk.Frame(self.content_frame, bg='#E6F0FF', bd=0, highlightthickness=0)
            self.event_options_frame.pack(fill='x', expand=True)
            
            # 创建技能容器（浅蓝色，无边框）
            self.skills_frame = tk.Frame(self.content_frame, bg='#E6F0FF', bd=0, highlightthickness=0)
            self.skills_frame.pack(fill='x', expand=True)
            
            # 创建物品容器（深褐色，无边框）
            self.items_frame = tk.Frame(self.content_frame, bg='#1A0F0A', bd=0, highlightthickness=0)
            self.items_frame.pack(fill='x', expand=True)
            
            # 更新所有挂起的空闲任务
            self.info_window.update_idletasks()
            
            logging.info("信息窗口创建成功")
            
        except Exception as e:
            logging.error(f"创建信息窗口失败: {e}")
            if self.info_window:
                self.info_window.destroy()
                self.info_window = None

    def handle_minimize(self):
        """处理窗口最小化事件"""
        try:
            self.hide_info()
        except Exception as e:
            logging.error(f"处理最小化事件失败: {e}")

    def adjust_window_size(self, pos_x, pos_y):
        """调整窗口大小"""
        try:
            # 获取当前时间
            current_time = time.time()
            
            # 如果距离上次调整时间不足0.1秒，则跳过
            if hasattr(self, '_last_adjust_time') and current_time - self._last_adjust_time < 0.1:
                return
                
            # 更新最后调整时间
            self._last_adjust_time = current_time
            
            # 获取游戏窗口大小
            _, game_rect = self.get_game_window()
            if not game_rect:
                return
                
            # 计算最大窗口高度（游戏窗口高度的80%）
            game_height = game_rect[3] - game_rect[1]
            max_window_height = int(game_height * 0.8)
            
            # 固定窗口宽度
            window_width = 600
            
            # 获取内容实际需要的高度
            self.info_window.update_idletasks()
            content_height = self.content_frame.winfo_reqheight()
            
            # 不留底部空白，窗口高度正好包裹内容
            window_height = min(content_height + 2, max_window_height)
            
            # 调整窗口位置（确保不超出屏幕边界）
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            
            if pos_x + window_width > screen_width:
                pos_x = max(0, screen_width - window_width)
                if pos_y + window_height > screen_height:
                    pos_y = max(0, screen_height - window_height)
                    
            # 设置窗口大小和位置
            self.info_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
            
            # 降低日志级别到DEBUG
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

            logging.info(f"查找本地图标路径: {icon_file_path}")
            if os.path.exists(icon_file_path):
                logging.info(f"找到本地图标: {icon_file_path}")
                return icon_file_path

            # 本地没有，尝试下载
            logging.info(f"开始下载图标: {icon_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(icon_url, headers=headers, timeout=10, verify=False)
            if resp.status_code == 200:
                os.makedirs(icons_path, exist_ok=True)
                with open(icon_file_path, 'wb') as f:
                    f.write(resp.content)
                logging.info(f"图标下载成功: {icon_file_path}")
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
            logging.info(f"怪物数据: {monster}")
            self.clear_frames()
            
            # 显示技能
            if monster.get('skills'):
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
                    
            # 显示物品（使用深褐色背景和金色文字）
            if monster.get('items'):
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
                    item_frame.pack(fill='x', pady=0)
                    
                    # 处理物品名称（如果有多个相同物品，显示数量）
                    display_name = item_name
                    if items_count[item_name] > 1:
                        display_name += f" x{items_count[item_name]}"
                        
                    # 获取物品图标
                    icon_path = None
                    if item.get('icon'):
                        icon_path = self.get_local_icon_path(item['icon'])
                    aspect_ratio = float(item.get('aspect_ratio', 1.0))
                    
                    # 设置物品文字颜色为金色
                    item_frame.name_label.configure(fg='#FFD700')  # 金色标题
                    item_frame.desc_label.configure(fg='#DAA520')  # 金色描述文字
                    
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
        """更新信息显示（统一怪物/事件识别）"""
        try:
            # 销毁旧窗口
            self.destroy_info_window()
            
            # 创建新窗口
            self.create_info_window()
            
            logging.info(f"开始更新信息显示，OCR文本: {text}")
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
                
            # 更新所有挂起的空闲任务
            self.info_window.update_idletasks()
            
            # 调整窗口大小和位置
            self.adjust_window_size(pos_x, pos_y)
            
            # 显示窗口
            self.info_window.deiconify()
            self.info_window.lift()
            self.info_window.attributes('-topmost', True)
            
            logging.info(f"{match_type}信息显示完成，位置: {pos_x}, {pos_y}")
            
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
                
            # 清理所有子Frame
            if hasattr(self, 'content_frame') and self.content_frame:
                for widget in self.content_frame.winfo_children():
                    if isinstance(widget, IconFrame):
                        widget.destroy()  # 这会触发 IconFrame 的 destroy 方法
                    else:
                        widget.destroy()
                self.content_frame.destroy()
                self.content_frame = None
                
            if hasattr(self, 'event_options_frame') and self.event_options_frame:
                self.event_options_frame.destroy()
                self.event_options_frame = None
                
            if hasattr(self, 'skills_frame') and self.skills_frame:
                self.skills_frame.destroy()
                self.skills_frame = None
                
            if hasattr(self, 'items_frame') and self.items_frame:
                self.items_frame.destroy()
                self.items_frame = None
                
            # 最后销毁主窗口
            if hasattr(self, 'info_window') and self.info_window:
                self.info_window.destroy()
                self.info_window = None
                
        except Exception as e:
            logging.error(f"销毁信息窗口失败: {e}")
            logging.error(traceback.format_exc())

    def quit_app(self):
        """退出应用程序"""
        try:
            # 停止所有线程
            self.is_running = False
            
            # 停止系统托盘
            if hasattr(self, 'system_tray') and self.system_tray:
                self.system_tray.icon.stop()
            
            # 等待线程结束
            if hasattr(self, 'keep_alive_thread') and self.keep_alive_thread:
                self.keep_alive_thread.join(timeout=1)
            if hasattr(self, 'tray_thread') and self.tray_thread:
                self.tray_thread.join(timeout=1)
            
            # 销毁窗口
            if self.info_window:
                self.info_window.destroy()
            if self.root:
                self.root.destroy()
            
            # 退出前暂停
            print("程序正在退出...")
            input("按回车键继续...")
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"退出程序时出错: {e}")
            sys.exit(1)  # 使用sys.exit代替os._exit

def hide_console():
    """隐藏控制台窗口"""
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except:
        pass

if __name__ == "__main__":
    helper = None
    try:
        logging.info("程序启动...")
        if not is_admin():
            logging.info("请求管理员权限...")
            run_as_admin()
        else:
            logging.info("创建 BazaarHelper 实例...")
            helper = BazaarHelper()
            logging.info("开始运行 BazaarHelper...")
            helper.run()
    except KeyboardInterrupt:
        logging.info("收到键盘中断信号")
        pass
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        logging.error(traceback.format_exc())
    finally:
        if helper:
            logging.info("停止 helper...")
            helper.stop()
        logging.info("程序退出")
        os._exit(0) 