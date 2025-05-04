import json
import keyboard
import pyautogui
import win32gui
import win32con
import win32api
import sys
import os
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageDraw, ImageFont
import pytesseract
import time
import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import win32com.client
import threading
import traceback
import logging
import re
import requests
from io import BytesIO
from PIL import ImageTk
from urllib.parse import urlparse
import difflib
import concurrent.futures
import io

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bazaar_helper.log', 'w', encoding='utf-8'),  # 使用 'w' 模式，每次运行清空日志
        logging.StreamHandler(sys.stdout)  # 同时输出到控制台
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
        self.configure(bg='#2C1810')
        
        # 创建左侧图标容器，固定宽度144，高度96
        self.icon_container = tk.Frame(self, bg='#2C1810', width=144, height=96)
        self.icon_container.pack_propagate(False)
        self.icon_container.pack(side='left', padx=1, pady=1)
        
        # 创建图标标签
        self.icon_label = tk.Label(self.icon_container, bg='#2C1810')
        self.icon_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 创建右侧文本容器
        self.text_container = tk.Frame(self, bg='#2C1810')
        self.text_container.pack(side='left', fill='both', expand=True, pady=1)
        
        # 新增：名称标签
        self.name_label = tk.Label(
            self.text_container,
            font=('Segoe UI', 14, 'bold'),
            fg='#FFFFFF',
            bg='#2C1810',
            anchor='w'
        )
        self.name_label.pack(fill='x', anchor='w')
        
        # 创建描述标签，左对齐
        self.desc_label = tk.Label(
            self.text_container,
            font=('Segoe UI', 13),
            fg='#E8C088',  # 使用金色
            bg='#2C1810',
            justify='left',
            anchor='w',
            wraplength=400  # 文本换行宽度
        )
        self.desc_label.pack(fill='both', expand=True, anchor='w')
    
    def update_content(self, name, description, icon_path=None, icon_type='event', aspect_ratio=1.0):
        """更新内容"""
        # 判断类型，设置背景色
        if icon_type == 'skill':
            bg_color = '#232323'
        else:
            bg_color = '#2C1810'
        self.configure(bg=bg_color)
        self.icon_container.configure(bg=bg_color)
        self.text_container.configure(bg=bg_color)
        self.desc_label.configure(bg=bg_color)
        self.name_label.configure(bg=bg_color)
        # 新增：设置名称
        self.name_label.config(text=name)
        # 更新描述
        self.desc_label.config(text=description, anchor='w', justify='left')
        
        # 处理图标
        if icon_path and os.path.exists(icon_path):
            try:
                # 图标容器固定为144x96
                self.icon_container.configure(width=144, height=96)
                self.icon_container.pack_propagate(False)
                # 计算宽度
                try:
                    ar = float(aspect_ratio)
                    if ar <= 0:
                        ar = 1.0
                except Exception:
                    ar = 1.0
                target_height = 96
                target_width = max(1, int(target_height * ar))
                # 加载并调整图标大小
                img = Image.open(icon_path)
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.icon_label.config(image=photo, width=target_width, height=target_height)
                self.icon_label.image = photo  # 保持引用
                # 居中显示
                self.icon_label.place(relx=0.5, rely=0.5, anchor='center', width=target_width, height=target_height)
                self.icon_container.pack(side='left', padx=1, pady=1)
            except Exception as e:
                logging.error(f"加载图标失败: {e}")
                if self.icon_container:
                    self.icon_container.pack_forget()
        else:
            # 如果没有图标，隐藏图标容器
            if self.icon_container:
                self.icon_container.pack_forget()

class BazaarHelper:
    def __init__(self):
        self.keyboard_listener = None  # 新增键盘监听器引用
        self.force_quit = False       # 新增强制退出标志
        try:
            logging.info("初始化OCR助手...")
            
            self.running = True
            self.showing_info = False
            self.ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)  # 全局单例线程池
            
            # 加载怪物数据
            self.load_monster_data()
            
            # 加载事件数据
            self.load_event_data()
            
            # 配置OCR
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # 创建主窗口
            self.create_info_window()
            
            # 创建图标缓存
            self.icon_cache = {}
            
            logging.info("初始化完成")
            
        except Exception as e:
            logging.error(f"初始化出错: {e}")
            raise

    def load_monster_data(self):
        """加载怪物数据"""
        try:
            with open('output/smart_all_monsters.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 将列表转换为以名称为键的字典
                self.monster_data = {monster['name']: monster for monster in data['monsters']}
            logging.info(f"成功加载怪物数据，共 {len(self.monster_data)} 个怪物")
        except Exception as e:
            logging.error(f"加载怪物数据失败: {e}")
            self.monster_data = {}

    def load_event_data(self):
        """加载事件数据"""
        try:
            # 加载事件列表
            with open('data/events/events.json', 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                logging.info(f"已加载 {len(self.events)} 个事件")
            # 加载所有事件选项
            self.event_options = {}
            all_options_path = 'data/events/all_events_options.json'
            if os.path.exists(all_options_path):
                with open(all_options_path, 'r', encoding='utf-8') as f:
                    all_options = json.load(f)
                    for event in all_options:
                        self.event_options[event['name']] = event['options']
                    logging.info(f"已加载所有事件选项（共 {len(self.event_options)} 个事件）")
            else:
                logging.warning("未找到 all_events_options.json")
        except Exception as e:
            logging.error(f"加载事件数据时出错: {e}")
            self.events = []
            self.event_options = {}

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        try:
            hwnd = win32gui.FindWindow(None, "The Bazaar")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 11")
            if not hwnd:
                hwnd = win32gui.FindWindow(None, "The Bazaar - DirectX 12")
                
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
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
        buf = io.BytesIO()
        Image.fromarray(processed_img).save(buf, format='PNG')
        img_bytes = buf.getvalue()
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(ocr_task, img_bytes)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logging.warning("OCR识别超时，已跳过本次识别。")
                return None

    def find_best_match(self, text):
        """统一识别怪物或事件，返回('monster'/'event', 名称)或(None, None)"""
        if not text:
            return None, None
        def clean_text(s):
            if not isinstance(s, str):
                return ""
            s = re.sub(r'[^a-zA-Z\s]', '', s)
            return ' '.join(s.split()).lower()
        # 只保留长度>=3的行
        lines = [clean_text(line.strip()) for line in str(text).split('\n') if len(clean_text(line.strip())) >= 3]
        print("lines:", lines)  # 调试输出
        best_type = None
        best_name = None
        best_ratio = 0.0
        for monster_name in self.monster_data:
            monster_clean = clean_text(monster_name)
            for line in lines:
                # 完全匹配
                if line == monster_clean:
                    return 'monster', monster_name
                # 包含匹配（长度接近才允许）
                if (monster_clean in line or line in monster_clean) and abs(len(line) - len(monster_clean)) < 3:
                    return 'monster', monster_name
                # 相似度匹配
                ratio = difflib.SequenceMatcher(None, line, monster_clean).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_type = 'monster'
                    best_name = monster_name
        for event in self.events:
            event_clean = clean_text(event['name'])
            for line in lines:
                if line == event_clean:
                    return 'event', event['name']
                ratio = difflib.SequenceMatcher(None, line, event_clean).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_type = 'event'
                    best_name = event['name']
        if best_ratio > 0.8:
            return best_type, best_name
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
            self.root = tk.Tk()
            self.root.withdraw()
            
            # 创建信息窗口
            self.info_window = tk.Toplevel(self.root)
            self.info_window.overrideredirect(True)  # 无边框窗口
            self.info_window.attributes('-topmost', True)  # 保持在最顶层
            self.info_window.attributes('-alpha', 0.95)  # 稍微调整透明度
            
            # 设置窗口背景色
            self.info_window.configure(bg='#2C1810')
            
            # 创建内容框架
            self.content_frame = tk.Frame(
                self.info_window,
                bg='#2C1810'  # 深褐色背景
            )
            self.content_frame.pack(fill='both', expand=True, padx=15, pady=15)
            
            # 创建子框架
            self.event_options_frame = tk.Frame(
                self.content_frame,
                bg='#2C1810'
            )
            
            self.skills_frame = tk.Frame(
                self.content_frame,
                bg='#2C1810'
            )
            
            self.items_frame = tk.Frame(
                self.content_frame,
                bg='#2C1810'
            )
            
            # 隐藏窗口
            self.info_window.withdraw()
            
            logging.info("信息窗口创建完成")
            
        except Exception as e:
            logging.error(f"创建信息窗口失败: {e}")
            raise

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
            self.info_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
            logging.info(f"窗口大小调整完成: {window_width}x{window_height}, 位置: {pos_x}, {pos_y}")
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

    def get_local_icon_path(self, url):
        """获取图标的本地路径，如无则自动下载"""
        if not url:
            return None
        from urllib.parse import urlparse
        filename = os.path.basename(urlparse(url).path)
        icon_path = os.path.join('icons', filename)
        if not os.path.exists(icon_path):
            # 自动下载图标
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    os.makedirs('icons', exist_ok=True)
                    with open(icon_path, "wb") as f:
                        f.write(resp.content)
                    logging.info(f"自动下载图标成功: {filename}")
                else:
                    logging.warning(f"自动下载图标失败: {filename}，状态码: {resp.status_code}")
            except Exception as e:
                logging.warning(f"自动下载图标异常: {filename}，错误: {e}")
        return icon_path if os.path.exists(icon_path) else None

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
            logging.debug(f"怪物原始数据: {monster}")
            self.clear_frames()
            has_skills = bool(monster['skills'])
            has_items = bool(monster['items'])
            # 先pack skills_frame
            if has_skills:
                self.skills_frame.pack(fill='x', pady=0, padx=0)
                for skill in monster['skills']:
                    skill_frame = IconFrame(self.skills_frame)
                    skill_frame.pack(fill='x', pady=1)
                    icon_path = self.get_local_icon_path(skill.get('icon'))
                    aspect_ratio = skill.get('aspect_ratio', 1.0)
                    skill_frame.update_content(
                        skill['name'],
                        skill['description'],
                        icon_path,
                        'skill',
                        aspect_ratio
                    )
            # 再pack items_frame
            if has_items:
                self.items_frame.pack(fill='x', pady=0, padx=0)
                items_count = {}
                items_info = {}
                for item in monster['items']:
                    items_count[item['name']] = items_count.get(item['name'], 0) + 1
                    if item['name'] not in items_info:
                        items_info[item['name']] = item
                item_keys = list(items_info.keys())
                for idx, item_name in enumerate(item_keys):
                    item = items_info[item_name]
                    item_frame = IconFrame(self.items_frame)
                    if len(item_keys) == 1:
                        item_frame.pack(fill='x', pady=0)
                    elif idx == 0:
                        item_frame.pack(fill='x', pady=(0, 4))
                    elif idx == len(item_keys) - 1:
                        item_frame.pack(fill='x', pady=(4, 0))
                    else:
                        item_frame.pack(fill='x', pady=(4, 4))
                    display_name = item_name
                    if items_count[item_name] > 1:
                        display_name += f" x{items_count[item_name]}"
                    icon_path = self.get_local_icon_path(item.get('icon'))
                    aspect_ratio = item.get('aspect_ratio', 1.0)
                    item_frame.update_content(
                        display_name,
                        item['description'],
                        icon_path,
                        'item',
                        aspect_ratio
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
            if event_name not in self.event_options:
                logging.error(f"找不到事件选项数据: {event_name}")
                return False

            options = self.event_options[event_name]
            if not options:
                logging.error(f"事件选项数据为空: {event_name}")
                return False

            # 清除现有内容
            self.clear_frames()

            # 显示事件选项框架
            self.event_options_frame.pack(fill='x', pady=1)

            for option in options:
                icon_path = self.get_local_icon_path(option.get('icon', ''))
                option_frame = IconFrame(self.event_options_frame)
                option_frame.pack(fill='x', pady=1)
                option_frame.update_content(
                    option.get('name', ''),
                    option.get('description', ''),
                    icon_path,
                    'event'
                )

            return True

        except Exception as e:
            logging.error(f"格式化事件信息时出错: {e}")
            logging.error(traceback.format_exc())
            return False

    def update_info_display(self, text, pos_x, pos_y):
        """更新信息显示（统一怪物/事件识别）"""
        try:
            logging.info(f"开始更新信息显示，OCR文本: {text}")
            match_type, match_name = self.find_best_match(text)
            if match_type == 'event':
                logging.info(f"找到匹配事件: {match_name}")
                if self.format_event_info(match_name):
                    self.showing_info = True
                    self.info_window.deiconify()
                    self.info_window.geometry(f"+{pos_x}+{pos_y}")
                    self.info_window.update()
                    self.content_frame.update()
                    self.adjust_window_size(pos_x, pos_y)
                    logging.info(f"事件信息显示完成，位置: {pos_x}, {pos_y}")
                    return
                else:
                    logging.warning(f"未能格式化事件 {match_name} 的信息")
            elif match_type == 'monster':
                logging.info(f"找到匹配怪物: {match_name}")
                if self.format_monster_info(match_name):
                    self.showing_info = True
                    self.info_window.deiconify()
                    self.info_window.geometry(f"+{pos_x}+{pos_y}")
                    self.info_window.update()
                    self.content_frame.update()
                    self.adjust_window_size(pos_x, pos_y)
                    logging.info(f"怪物信息显示完成，位置: {pos_x}, {pos_y}")
                    return
                else:
                    logging.warning(f"未能格式化怪物 {match_name} 的信息")
            else:
                logging.info("未找到匹配的事件或怪物，隐藏窗口")
                self.hide_info()
        except Exception as e:
            logging.error(f"更新信息显示时出错: {e}")
            logging.error(traceback.format_exc())
            self.hide_info()

    def hide_info(self):
        """隐藏信息窗口"""
        try:
            if self.info_window:
                self.info_window.withdraw()
        except Exception as e:
            logging.error(f"隐藏信息窗口失败: {e}")

    def run(self):
        """运行助手（主线程轮询Alt键状态）"""
        logging.info("开始运行OCR助手...")
        logging.info("按住Alt键识别文字")
        logging.info("按Esc键退出")
        try:
            alt_was_pressed = False
            while self.running:
                try:
                    # 检测Alt键
                    alt_is_pressed = keyboard.is_pressed('alt')
                    # 只在Alt键刚被按下时执行一次识别
                    if alt_is_pressed and not alt_was_pressed:
                        logging.debug("检测到Alt键按下，准备识别")
                        cursor_x, cursor_y = win32gui.GetCursorPos()
                        text = self.get_text_at_cursor()
                        if text:
                            logging.debug("识别到文本，更新信息显示")
                            self.update_info_display(text, cursor_x, cursor_y)
                    # 当松开Alt键时
                    elif not alt_is_pressed and alt_was_pressed:
                        logging.debug("Alt键松开，隐藏信息窗口")
                        self.hide_info()
                    # 更新Alt键状态
                    alt_was_pressed = alt_is_pressed
                    # 检测Esc键退出
                    if keyboard.is_pressed('esc'):
                        logging.info("检测到Esc键，程序退出")
                        self.running = False
                        break
                    # 确保窗口保持在最顶层
                    if self.info_window.winfo_viewable():
                        self.info_window.lift()
                        self.info_window.attributes('-topmost', True)
                    time.sleep(0.01)
                except Exception as e:
                    logging.error(f"运行时出错: {e}")
                    logging.error(traceback.format_exc())
                    time.sleep(1)
        except Exception as e:
            logging.error(f"程序运行出错: {e}")
            logging.error(traceback.format_exc())
        finally:
            logging.info("程序正在退出...")
            if self.root:
                self.root.destroy()
            logging.info("程序已退出")

    def stop(self):
        """增强的停止方法"""
        self.force_quit = True
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.root:
            self.root.quit()
        os._exit(0)  # 强制退出

if __name__ == "__main__":
    helper = None
    try:
        if not is_admin():
            run_as_admin()
        else:
            helper = BazaarHelper()
            helper.run()
    except KeyboardInterrupt:
        pass
    finally:
        if helper:
            helper.stop()
        os._exit(0) 