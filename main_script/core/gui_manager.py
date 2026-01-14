"""
GUI窗口管理模块
"""
import os
import re
import tkinter as tk
import threading
import logging
import traceback
from urllib.parse import urlparse
from ui import IconFrame, ScrollableFrame


class GUIManager:
    """GUI窗口管理器"""

    def __init__(self):
        self.info_window = None
        self.gui_update_queue = []
        self.gui_update_lock = threading.Lock()
        self.current_text = None
        self.content_frame = None
        self.scrollable_frame = None
        self.icon_frames = []  # 保存所有IconFrame的引用
        self.skills_frame = None
        self.items_frame = None
        self.event_options_frame = None

    def _is_window_valid(self):
        """检查窗口和框架是否有效"""
        try:
            if not self.info_window:
                return False
            if not self.info_window.winfo_exists():
                return False
            # 检查关键子框架是否存在
            # 这些框架在create_info_window中创建，如果它们不存在，说明窗口结构不完整
            if not self.content_frame or not self.content_frame.winfo_exists():
                return False
            if not self.scrollable_frame or not self.scrollable_frame.winfo_exists():
                return False
            # 检查主框架是否存在（它们可能在显示内容时才创建）
            # 如果框架不存在，返回True，因为主窗口和content_frame存在
            # 具体的子框架会在需要时重新创建
            return True
        except tk.TclError:
            return False

    def create_info_window(self):
        """创建信息显示窗口"""
        try:
            # 如果窗口已存在且有效，直接返回
            if self.info_window and self.skills_frame:
                try:
                    if self.info_window.winfo_exists() and self.skills_frame.winfo_exists():
                        return
                except tk.TclError:
                    pass  # 窗口无效，继续创建
            
            # 清理旧引用
            self.info_window = None
            self.skills_frame = None
            self.items_frame = None
            self.event_options_frame = None
            self.content_frame = None
            self.scrollable_frame = None

            # 创建主窗口
            self.info_window = tk.Tk()
            self.info_window.title("Bazaar Lens")
            bg_color = '#1C1810'  # 深色背景
            self.info_window.configure(bg=bg_color)

            # 设置窗口属性
            self.info_window.overrideredirect(True)  # 无边框窗口
            self.info_window.attributes('-topmost', True)  # 始终置顶
            self.info_window.attributes('-alpha', 0.95)  # 半透明

            # 创建可滚动框架
            self.scrollable_frame = ScrollableFrame(
                self.info_window, bg=bg_color)
            self.scrollable_frame.pack(fill='both', expand=True, padx=5, pady=5)

            # 获取内部框架用于添加内容
            self.content_frame = self.scrollable_frame.get_inner_frame()

            # 创建技能容器（与旧脚本保持一致）
            self.skills_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.skills_frame.pack(fill='x', expand=True)

            # 创建物品容器（与旧脚本保持一致）
            self.items_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.items_frame.pack(fill='x', expand=True)

            # 创建事件选项容器（与旧脚本保持一致）
            self.event_options_frame = tk.Frame(self.content_frame, bg=bg_color)
            self.event_options_frame.pack(fill='x', expand=True)

            # 初始隐藏窗口
            self.info_window.withdraw()

            logging.info("信息窗口创建成功")
        except Exception as e:
            logging.error(f"创建信息窗口失败: {e}")
            self.info_window = None

    def update_info_window(self, content):
        """更新信息窗口内容"""
        if not self.info_window or not self.content_frame:
            return

        try:
            # 清空现有内容
            for frame in self.icon_frames:
                try:
                    frame.destroy()
                except Exception:
                    pass
            self.icon_frames.clear()

            # 添加新内容
            if content:
                # content应该是一个列表，每个元素是一个字典，包含name, description, icon_path等
                if isinstance(content, list):
                    for item in content:
                        icon_frame = IconFrame(self.content_frame, bg='#1C1810')
                        icon_frame.pack(fill='x', padx=5, pady=5)
                        icon_frame.update_content(
                            name=item.get('name', ''),
                            description=item.get('description', ''),
                            icon_path=item.get('icon_path'),
                            aspect_ratio=item.get('aspect_ratio', 1.0)
                        )
                        self.icon_frames.append(icon_frame)
                elif isinstance(content, dict):
                    # 单个项目
                    icon_frame = IconFrame(self.content_frame, bg='#1C1810')
                    icon_frame.pack(fill='x', padx=5, pady=5)
                    icon_frame.update_content(
                        name=content.get('name', ''),
                        description=content.get('description', ''),
                        icon_path=content.get('icon_path'),
                        aspect_ratio=content.get('aspect_ratio', 1.0)
                    )
                    self.icon_frames.append(icon_frame)

            # 更新滚动区域
            if self.scrollable_frame:
                self.scrollable_frame.update_scrollregion()

        except Exception as e:
            logging.error(f"更新信息窗口内容失败: {e}")

    def start_gui_update_timer(self, is_running_callback=None):
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
                            # 如果data_matcher为None，尝试从data_loader获取
                            data_matcher = task.get('data_matcher')
                            data_loader = task.get('data_loader')
                            if not data_matcher and data_loader and hasattr(data_loader, 'matcher') and data_loader.matcher:
                                data_matcher = data_loader.matcher
                                logging.info(f"[GUI更新] 从data_loader获取matcher: {type(data_matcher).__name__}")
                            
                            self._do_show_info(
                                task['text'], task['x'], task['y'],
                                data_matcher=data_matcher,
                                data_loader=data_loader)
                        elif task_type == 'show_enchantments':
                            # 如果data_matcher为None，尝试从data_loader获取
                            data_matcher = task.get('data_matcher')
                            data_loader = task.get('data_loader')
                            if not data_matcher and data_loader and hasattr(data_loader, 'matcher') and data_loader.matcher:
                                data_matcher = data_loader.matcher
                                logging.info(f"[GUI更新] 从data_loader获取matcher: {type(data_matcher).__name__}")
                            
                            self._do_show_enchantments(
                                task['text'], task['x'], task['y'],
                                data_matcher=data_matcher,
                                data_loader=data_loader)
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
                if (is_running_callback and is_running_callback()) and self.info_window:
                    self.info_window.after(50, process_gui_updates)

        # 启动定时器
        if self.info_window:
            self.info_window.after(50, process_gui_updates)

    def _do_show_info(self, text, x, y, data_matcher=None, data_loader=None):
        """
        实际执行显示信息的操作（在主线程中调用）
        完全按照旧脚本Bazaar_Lens.py的逻辑实现
        """
        try:
            # 确保窗口已创建且有效
            if not self._is_window_valid():
                logging.warning("信息窗口无效，重新创建...")
                # 先销毁旧窗口（如果存在）
                if self.info_window:
                    try:
                        self.info_window.destroy()
                    except:
                        pass
                    self.info_window = None
                self.create_info_window()
                if not self._is_window_valid():
                    logging.error("无法创建有效的信息窗口")
                    return
            
            logging.info(f"开始更新信息显示，OCR文本: {text}")
            
            # 使用数据匹配器查找匹配的数据
            # 如果data_matcher为None，尝试从data_loader获取
            if not data_matcher and data_loader and hasattr(data_loader, 'matcher') and data_loader.matcher:
                data_matcher = data_loader.matcher
                logging.info(f"从data_loader获取matcher: {type(data_matcher).__name__}")
            
            match_type, match_name = None, None
            if text and data_matcher:
                match_type, match_name = data_matcher.find_best_match(text)
                logging.info(f"匹配结果: type={match_type}, name={match_name}")
            else:
                logging.warning(f"缺少匹配器或文本，无法匹配: text={text[:50] if text else None}, matcher={data_matcher is not None}, loader={data_loader is not None}, loader_has_matcher={hasattr(data_loader, 'matcher') if data_loader else False}, loader_matcher_value={getattr(data_loader, 'matcher', None) if data_loader else None}")
            
            display_success = False
            if match_type == 'event':
                logging.info(f"尝试显示事件: {match_name}")
                if data_loader:
                    display_success = self._format_event_info(match_name, data_loader)
                logging.info(f"format_event_info 返回: {display_success}")
            elif match_type == 'monster':
                if data_loader:
                    display_success = self._format_monster_info(match_name, data_loader)
                
            if not display_success:
                logging.warning(f"显示失败: match_type={match_type}, match_name={match_name}")
                if match_type:
                    self.show_info_message(f"未找到该{match_type}的数据，请稍后再试。", None)
                else:
                    self.show_info_message("未能识别到怪物或事件名称。", None)
                return
            
            logging.info(f"准备显示窗口，位置: {x}, {y}")
                
            # 设置初始位置
            self.info_window.geometry(f"+{x}+{y}")
            
            # 更新窗口布局
            self.info_window.update_idletasks()
            
            # 调整窗口大小
            self._do_adjust_window(x, y)
            
            # 显示窗口并置顶（如果匹配成功就显示，不依赖ctrl_pressed状态）
            if display_success:
                logging.info(f"显示窗口: {match_type} - {match_name}")
                self.info_window.deiconify()
                self.info_window.lift()
                self.info_window.attributes('-topmost', True)
            else:
                logging.warning(f"匹配成功但显示失败，不显示窗口")
            
            logging.debug(f"{match_type}信息显示完成，位置: {x}, {y}")

        except Exception as e:
            logging.error(f"显示信息窗口失败: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def _do_hide_info(self):
        """隐藏信息窗口"""
        try:
            if self.info_window:
                self.info_window.withdraw()
                self.current_text = None
        except Exception as e:
            logging.error(f"隐藏信息窗口失败: {e}")

    def _do_show_enchantments(self, text, x, y, data_matcher=None, data_loader=None):
        """
        显示附魔信息（物品附魔）
        按照旧脚本Bazaar_Lens.py的逻辑实现
        """
        try:
            if not self.info_window:
                self.create_info_window()
            if not self._is_window_valid():
                logging.warning("窗口无效，无法显示附魔信息")
                return

            self.current_text = text
            logging.info(f"开始查找物品附魔，OCR文本: {text[:50] if text else None}...")

            # 使用 data_loader.find_item_by_name 查找物品
            item_data = None
            if text and data_loader:
                item_data = data_loader.find_item_by_name(text)
            
            if not item_data:
                logging.warning(f"未找到物品: {text[:50] if text else None}")
                self.show_info_message("未能识别到物品名称。", None)
                return
            
            item_name = item_data.get('name_zh', item_data.get('name', ''))
            logging.info(f"找到物品: {item_name}")
            
            # 获取附魔信息
            enchantments = item_data.get('enchantments', [])
            if not enchantments:
                logging.warning(f"物品 {item_name} 没有附魔信息")
                self.show_info_message(f"{item_name} 没有附魔信息。", None)
                return
            
            logging.info(f"找到 {len(enchantments)} 个附魔")
            
            # 清除现有内容
            if not self._clear_frames():
                return
            
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
            
            # 附魔颜色映射
            enchant_colors = {
                '黄金': '#FFD700',
                '沉重': '#8B4513',
                '寒冰': '#00BFFF',
                '疾速': '#00FF00',
                '护盾': '#4169E1',
                '回复': '#32CD32',
                '毒性蔓延': '#9400D3',
                '炽焰': '#FF4500',
                '闪亮': '#FFFF00',
                '致命': '#DC143C',
                '光明': '#FFFACD',
                '黑曜石': '#2F4F4F',
            }
            
            # 显示每个附魔卡片
            for i, enchant in enumerate(enchantments):
                row = i // 2
                col = i % 2
                
                enchant_name = enchant.get('name', enchant.get('name_en', ''))
                enchant_desc = enchant.get('description', '')
                
                # 获取标题颜色
                title_color = enchant_colors.get(enchant_name, '#E8D4B9')
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
                
                # 附魔名称
                name_label = tk.Label(
                    card_frame,
                    text=enchant_name,
                    font=('Microsoft YaHei', 11, 'bold'),
                    bg=bg_color,
                    fg=title_color,
                    anchor='w'
                )
                name_label.pack(fill='x', padx=5, pady=(5, 2))
                
                # 附魔描述
                desc_label = tk.Label(
                    card_frame,
                    text=enchant_desc,
                    font=('Microsoft YaHei', 9),
                    bg=bg_color,
                    fg='#E8E8E8',
                    anchor='w',
                    wraplength=200,
                    justify='left'
                )
                desc_label.pack(fill='x', padx=5, pady=(0, 5))
            
            # 调整窗口位置和大小
            self._do_adjust_window(x, y)
            
            # 显示窗口
            self.info_window.deiconify()
            self.info_window.lift()
            self.info_window.attributes('-topmost', True)

        except Exception as e:
            logging.error(f"显示附魔信息失败: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def _do_adjust_window(self, x, y):
        """调整窗口位置和大小（在主线程中调用）"""
        try:
            if not self.info_window or not self.info_window.winfo_exists():
                return

            # 计算窗口位置（在鼠标右上方）
            offset_x = 20
            offset_y = -20
            pos_x = x + offset_x
            pos_y = y + offset_y

            # 获取游戏窗口大小（用于限制窗口高度）
            try:
                from .window_detector import WindowDetector
                window_detector = WindowDetector()
                _, game_rect = window_detector.get_game_window()
                if game_rect:
                    game_height = game_rect[3] - game_rect[1]
                    max_window_height = int(game_height * 0.8)
                else:
                    max_window_height = 600
            except Exception:
                max_window_height = 600

            # 固定窗口宽度
            window_width = 600

            # 更新内容框架以获取实际高度
            if self.content_frame:
                self.content_frame.update_idletasks()
                content_height = self.content_frame.winfo_reqheight() + 20
            else:
                content_height = 200

            # 根据内容高度确定窗口高度
            if content_height <= max_window_height:
                window_height = content_height
            else:
                window_height = max_window_height

            # 调整窗口位置（取消右和下边界限制，允许窗口超出屏幕）
            # 只确保窗口左上角在屏幕内
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            if pos_x < 0:
                pos_x = 0
            if pos_y < 0:
                pos_y = 0
            # 允许窗口超出屏幕右边界和下边界

            self.info_window.geometry(
                f"{window_width}x{window_height}+{pos_x}+{pos_y}")

            # 更新滚动区域
            if self.scrollable_frame:
                self.scrollable_frame.update_scrollregion()

        except Exception as e:
            logging.error(f"调整窗口大小失败: {e}")

    def _do_move_window(self, pos_x, pos_y):
        """只移动窗口位置，不调整大小（在主线程中调用）"""
        try:
            # 对于移动操作，只需要检查主窗口是否存在
            if not self.info_window:
                logging.debug("[窗口移动] info_window为None")
                return
            try:
                if not self.info_window.winfo_exists():
                    logging.debug("[窗口移动] info_window不存在")
                    return
            except tk.TclError as e:
                logging.debug(f"[窗口移动] TclError检查窗口存在: {e}")
                return

            # 获取当前窗口大小
            current_geometry = self.info_window.geometry()
            # 解析当前几何信息 (格式: "widthxheight+x+y")
            parts = current_geometry.split('+')
            if len(parts) >= 3:
                size_part = parts[0]
                current_x = int(parts[1])
                current_y = int(parts[2])
            else:
                size_part = "600x400"
                current_x = pos_x
                current_y = pos_y

            # 计算新位置（在鼠标右上方）
            offset_x = 20
            offset_y = -20
            new_x = pos_x + offset_x
            new_y = pos_y + offset_y

            # 确保不超出屏幕边界（取消右和下边界限制）
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            size_parts = size_part.split('x')
            if len(size_parts) == 2:
                window_width = int(size_parts[0])
                window_height = int(size_parts[1])
            else:
                window_width = 600
                window_height = 400

            # 只确保窗口左上角在屏幕内
            if new_x < 0:
                new_x = 0
            if new_y < 0:
                new_y = 0
            # 允许窗口超出屏幕右边界和下边界

            # 只在位置变化时更新
            if new_x != current_x or new_y != current_y:
                try:
                    self.info_window.geometry(f"{size_part}+{new_x}+{new_y}")
                    logging.debug(f"[窗口移动] 移动到位置: {new_x}, {new_y}")
                except tk.TclError as e:
                    logging.warning(f"[窗口移动] 设置几何位置失败: {e}")
                except Exception as e:
                    logging.error(f"[窗口移动] 未知错误: {e}")

        except Exception as e:
            logging.error(f"移动窗口位置失败: {e}")

    def _ensure_subframes_exist(self):
        """确保子框架存在，如果不存在则重新创建"""
        try:
            if not self._is_window_valid():
                return False
            
            bg_color = '#1C1810'
            
            # 检查并重新创建skills_frame
            if not self.skills_frame or not self.skills_frame.winfo_exists():
                self.skills_frame = tk.Frame(self.content_frame, bg=bg_color)
                logging.debug("重新创建skills_frame")
            
            # 检查并重新创建items_frame
            if not self.items_frame or not self.items_frame.winfo_exists():
                self.items_frame = tk.Frame(self.content_frame, bg=bg_color)
                logging.debug("重新创建items_frame")
            
            # 检查并重新创建event_options_frame
            if not self.event_options_frame or not self.event_options_frame.winfo_exists():
                self.event_options_frame = tk.Frame(self.content_frame, bg=bg_color)
                logging.debug("重新创建event_options_frame")
            
            return True
        except Exception as e:
            logging.error(f"确保子框架存在失败: {e}")
            return False
    
    def _clear_frames(self):
        """清空所有内容框架（与旧脚本保持一致）"""
        try:
            if not self._is_window_valid():
                logging.debug("窗口无效，跳过清空框架")
                return False
            
            # 检查并确保子框架存在，如果不存在则重新创建
            self._ensure_subframes_exist()
            
            # 只清空子元素，不destroy主Frame本身
            if self.skills_frame and self.skills_frame.winfo_exists():
                for widget in self.skills_frame.winfo_children():
                    try:
                        widget.destroy()
                    except tk.TclError:
                        pass  # 忽略已销毁的组件
            
            if self.items_frame and self.items_frame.winfo_exists():
                for widget in self.items_frame.winfo_children():
                    try:
                        widget.destroy()
                    except tk.TclError:
                        pass  # 忽略已销毁的组件
            
            if self.event_options_frame and self.event_options_frame.winfo_exists():
                for widget in self.event_options_frame.winfo_children():
                    try:
                        widget.destroy()
                    except tk.TclError:
                        pass  # 忽略已销毁的组件
            
            # 控制框架的显示/隐藏
            if self.skills_frame and self.skills_frame.winfo_exists():
                self.skills_frame.pack_forget()
            if self.items_frame and self.items_frame.winfo_exists():
                self.items_frame.pack_forget()
            if self.event_options_frame and self.event_options_frame.winfo_exists():
                self.event_options_frame.pack_forget()
            
            # 清理content_frame下的所有spacer（Frame），只destroy不是主Frame的spacer
            if self.content_frame and self.content_frame.winfo_exists():
                for widget in self.content_frame.winfo_children():
                    try:
                        if isinstance(widget, tk.Frame) and widget not in [self.event_options_frame, self.skills_frame, self.items_frame]:
                            widget.destroy()
                    except tk.TclError:
                        pass  # 忽略已销毁的组件
            
            return True
        except tk.TclError as e:
            logging.warning(f"清空框架时窗口已失效: {e}")
            return False
        except Exception as e:
            logging.error(f"清空框架失败: {e}")
            return False

    def get_monster_icon_path(self, icon_filename, icon_type='skill'):
        """获取怪物相关的图标路径（技能/物品/怪物）- 与旧脚本保持一致"""
        # icon_type: 'skill', 'item', 'monster'
        try:
            # 获取项目根目录
            current_file = os.path.abspath(__file__)  # core/gui_manager.py
            core_dir = os.path.dirname(current_file)  # core目录
            main_script_dir = os.path.dirname(core_dir)  # main_script目录
            project_root = os.path.dirname(main_script_dir)  # 项目根目录
            
            # 新目录结构：data/icon/skill/, data/icon/item/, data/icon/monster/
            icon_dir = os.path.join(project_root, 'data', 'icon', icon_type)
            
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
        """从多个可能的图标路径查找图标，找不到则自动下载（与旧脚本保持一致）"""
        # 如果是相对路径，直接返回
        if icon_url and not icon_url.startswith('http'):
            # 获取项目根目录
            current_file = os.path.abspath(__file__)  # core/gui_manager.py
            core_dir = os.path.dirname(current_file)  # core目录
            main_script_dir = os.path.dirname(core_dir)  # main_script目录
            project_root = os.path.dirname(main_script_dir)  # 项目根目录
            
            # 如果是事件图标，尝试在事件文件夹中查找
            if event_name_en:
                # 处理文件夹名称中的特殊字符（如单引号）
                event_name_en_clean = event_name_en.replace("'", "").replace("'", "")
                # 尝试在事件文件夹中查找
                event_icon_paths = [
                    os.path.join(project_root, '6.0', 'crawlers', 'event_details_final', 'icons', event_name_en_clean),
                    os.path.join(project_root, 'data', 'icon', 'event', event_name_en_clean),
                ]
                for event_icon_path in event_icon_paths:
                    if os.path.exists(event_icon_path):
                        # 尝试查找选项图标
                        option_icon_path = os.path.join(event_icon_path, icon_url)
                        if os.path.exists(option_icon_path):
                            return option_icon_path
                        # 如果icon_url是完整路径，直接使用
                        if os.path.exists(icon_url):
                            return icon_url
            
            # 优先查找6.0文件夹下的图标
            icon_paths = [
                os.path.join(project_root, '6.0', 'crawlers', 'monster_details_v3', 'icons'),
                os.path.join(project_root, '6.0', 'crawlers', 'event_details_final', 'icons'),
                os.path.join(project_root, icons_dir)
            ]
            for icon_path in icon_paths:
                full_path = os.path.join(icon_path, icon_url)
                if os.path.exists(full_path):
                    return full_path
            return None

        if not icon_url or not icon_url.startswith('http'):
            logging.warning(f"无效的图标URL: {icon_url}")
            return None

        try:
            import requests
            # 清理文件名，移除查询参数
            parsed_url = urlparse(icon_url)
            filename = os.path.basename(parsed_url.path)
            # 允许@字符
            filename = re.sub(r'[^\w\-_.@]', '_', filename)

            # 获取项目根目录
            current_file = os.path.abspath(__file__)  # core/gui_manager.py
            core_dir = os.path.dirname(current_file)  # core目录
            main_script_dir = os.path.dirname(core_dir)  # main_script目录
            project_root = os.path.dirname(main_script_dir)  # 项目根目录

            # 尝试多个可能的图标路径
            icon_paths = [
                os.path.join(project_root, '6.0', 'crawlers', 'monster_details_v3', 'icons'),
                os.path.join(project_root, '6.0', 'crawlers', 'event_details_final', 'icons'),
                os.path.join(project_root, icons_dir)
            ]
            
            for icons_path in icon_paths:
                icon_file_path = os.path.join(icons_path, filename)
                if os.path.exists(icon_file_path):
                    logging.debug(f"找到本地图标: {icon_file_path}")
                    return icon_file_path
            
            # 如果都没找到，使用第一个路径进行下载
            icons_path = icon_paths[0]
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

    def _format_monster_info(self, monster_name, data_loader):
        """格式化怪物信息显示（显示技能和物品，与旧脚本保持一致）"""
        try:
            if not monster_name:
                logging.warning("怪物名称为空，无法显示信息")
                return False
            
            # 检查窗口有效性
            if not self._is_window_valid():
                logging.warning("窗口无效，无法显示怪物信息")
                return False
                
            logging.info(f"开始格式化怪物信息: {monster_name}")
            monster_data = data_loader.get_monster_data(monster_name)
            if not monster_data:
                logging.warning(f"未找到怪物数据: {monster_name}")
                # 确保子框架存在
                if not self._ensure_subframes_exist():
                    logging.warning("无法确保子框架存在，无法显示未找到消息")
                    return False
                if self.skills_frame and self.skills_frame.winfo_exists():
                    self.skills_frame.pack(fill='x', pady=0, padx=0)
                    not_found_frame = IconFrame(self.skills_frame)
                    not_found_frame.pack(fill='x', pady=0)
                    not_found_frame.update_content(
                        monster_name,
                        "未找到该怪物的数据，请稍后再试。",
                        None
                    )
                return True
                
            logging.info(f"找到怪物数据: {monster_name}, 技能数: {len(monster_data.get('skills', []))}, 物品数: {len(monster_data.get('items', []))}")
            if not self._clear_frames():
                return False
            
            # 确保子框架存在
            if not self._ensure_subframes_exist():
                logging.warning("无法确保子框架存在，无法显示怪物信息")
                return False
            
            has_skills = False
            # 显示技能
            if monster_data.get('skills'):
                has_skills = True
                if self.skills_frame and self.skills_frame.winfo_exists():
                    self.skills_frame.pack(fill='x', pady=0, padx=0)
                    for skill in monster_data['skills']:
                        skill_frame = IconFrame(self.skills_frame)
                        skill_frame.pack(fill='x', pady=0)
                        
                        # 获取技能名称和描述（优先使用中文）
                        skill_name_en = skill.get('name', '')
                        skill_name_zh = skill.get('name_zh', skill_name_en)
                        skill_description = ''
                        
                        # 从skills_data中获取描述信息
                        if skill_name_en in data_loader.skills_data:
                            skill_info = data_loader.skills_data[skill_name_en]
                            skill_description = skill_info.get('description_zh', '')
                            skill_icon = skill_info.get('icon', '')
                            skill_aspect_ratio = float(skill_info.get('aspect_ratio', 1.0))
                        else:
                            skill_description = skill.get('description', '')
                            skill_icon = skill.get('icon', '')
                            skill_aspect_ratio = float(skill.get('aspect_ratio', 1.0))
                        
                        # 获取技能图标（优先使用新目录结构）
                        icon_path = None
                        if skill_icon:
                            # 新格式：skill/Above_the_Clouds.webp 或直接文件名
                            icon_path = self.get_monster_icon_path(skill_icon, 'skill')
                        elif skill.get('icon'):
                            icon_path = self.get_monster_icon_path(skill['icon'], 'skill')
                        elif skill.get('icon_url'):
                            icon_path = self.get_local_icon_path(skill['icon_url'])
                        
                        skill_frame.update_content(
                            skill_name_zh,
                            skill_description,
                            icon_path,
                            skill_aspect_ratio
                        )
                    
            # 显示物品
            if monster_data.get('items'):
                if has_skills and self.content_frame and self.content_frame.winfo_exists():
                    # 添加分隔条
                    separator = tk.Frame(self.content_frame, height=2, bg='#3A7BBA')
                    separator.pack(fill='x', pady=5, padx=10)
                
                if self.items_frame and self.items_frame.winfo_exists():
                    self.items_frame.pack(fill='x', pady=0, padx=0)
                    # 统计相同物品的数量
                    items_count = {}
                    items_info = {}
                    for item in monster_data['items']:
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
                        if item_name in data_loader.items_data:
                            item_info = data_loader.items_data[item_name]
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
                            icon_path = self.get_monster_icon_path(item['icon'], 'item')
                        elif item.get('icon_url'):
                            icon_path = self.get_local_icon_path(item['icon_url'])
                        
                        item_frame.update_content(
                            display_name,
                            item_description,
                            icon_path,
                            item_aspect_ratio
                        )
                    
            # 如果既没有技能也没有物品，显示提示信息
            if not monster_data.get('skills') and not monster_data.get('items'):
                if self.skills_frame and self.skills_frame.winfo_exists():
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

    def _format_event_info(self, event_name, data_loader):
        """格式化事件信息显示（与旧脚本保持一致）"""
        try:
            # 检查窗口有效性
            if not self._is_window_valid():
                logging.warning("窗口无效，无法显示事件信息")
                return False
            
            logging.info(f"尝试格式化事件信息: {event_name}")
            event_data = data_loader.get_event_data(event_name)
            if not event_data:
                logging.error(f"找不到事件选项数据: {event_name}")
                self._show_unmatched_text(event_name)
                return False
            
            if not isinstance(event_data, list) or not event_data:
                logging.error(f"事件选项数据为空: {event_name}")
                self._show_unmatched_text(event_name)
                return False
            
            logging.info(f"找到 {len(event_data)} 个事件选项")
            
            # 清除现有内容
            if not self._clear_frames():
                return False
            
            # 确保子框架存在
            if not self._ensure_subframes_exist():
                logging.warning("无法确保子框架存在，无法显示事件信息")
                return False
            
            # 显示事件选项框架
            if self.event_options_frame and self.event_options_frame.winfo_exists():
                self.event_options_frame.pack(fill='x', pady=0)
            
            # 获取事件的英文名称（用于查找图标文件夹）
            event_name_en = data_loader.event_name_map.get(event_name, '')
            # 处理文件夹名称中的特殊字符（如单引号）
            if event_name_en:
                # 移除单引号，因为文件夹名可能没有单引号
                event_name_en_clean = event_name_en.replace("'", "").replace("'", "")
            else:
                event_name_en_clean = ''
            
            logging.debug(f"事件: {event_name}, 英文名: {event_name_en}, 清理后: {event_name_en_clean}")
            
            if self.event_options_frame and self.event_options_frame.winfo_exists():
                for option in event_data:
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
            
            if not event_data:
                if self.event_options_frame and self.event_options_frame.winfo_exists():
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
            logging.error(f"格式化事件信息失败: {e}")
            logging.error(traceback.format_exc())
            return False

    def show_info_message(self, message, icon_url):
        """
        显示信息消息
        完全按照旧脚本Bazaar_Lens.py的逻辑实现
        """
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

    def destroy_info_window(self):
        """销毁信息窗口"""
        if self.info_window:
            try:
                self.info_window.destroy()
                self.info_window = None
            except Exception as e:
                logging.error(f"销毁信息窗口失败: {e}")
