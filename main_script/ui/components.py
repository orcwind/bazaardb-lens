"""
GUI组件模块
"""
import os
import io
import re
import logging
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class IconFrame(tk.Frame):
    """用于显示图标和文本的框架"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # 获取父容器的背景色，如果没有指定则使用深色主题
        parent_bg = parent.cget('bg') if parent else '#1C1810'
        self.configure(bg=parent_bg)

        # 创建左侧图标容器，固定宽度
        self.icon_container = tk.Frame(
            self, bg=parent_bg, width=144, height=96)
        self.icon_container.pack_propagate(False)
        self.icon_container.pack(side='left', padx=0, pady=0)

        # 创建图标标签
        self.icon_label = tk.Label(self.icon_container, bg=parent_bg)
        self.icon_label.pack(expand=True)

        # 创建右侧文本容器
        self.text_frame = tk.Frame(self, bg=parent_bg)
        self.text_frame.pack(
            side='left',
            fill='both',
            expand=True,
            padx=0,
            pady=0)

        # 创建名称和数量的容器
        self.name_container = tk.Frame(self.text_frame, bg=parent_bg)
        self.name_container.pack(fill='x', anchor='w', pady=0)

        # 创建名称标签
        self.name_label = tk.Label(
            self.name_container,
            font=('Segoe UI', 14, 'bold'),
            fg='#E8D4B9',  # 浅色文字（默认）
            bg=parent_bg,
            anchor='w',
            justify='left'
        )
        self.name_label.pack(side='left', anchor='w')

        # 创建品质标签容器（用于包裹品质标签，支持边框）
        self.quality_container = tk.Frame(self.name_container, bg=parent_bg, relief='flat', bd=0)
        self.quality_container.pack_forget()
        
        # 创建品质标签（用于显示品质标记，带颜色背景）
        self.quality_label = tk.Label(
            self.quality_container,
            font=('Segoe UI', 10, 'bold'),
            fg='#FFFFFF',  # 默认白色，品质出现时会被覆盖为合适颜色
            bg=parent_bg,  # 默认背景色，会根据品质动态更新
            anchor='w',
            justify='left',
            padx=4,  # 左右内边距
            pady=1   # 上下内边距
        )
        self.quality_label.pack()

        # 创建数量标签
        self.quantity_label = tk.Label(
            self.name_container,
            font=('Segoe UI', 16, 'bold'),  # 更大的字体
            fg='#FFD700',  # 金色文字（默认数量色）
            bg=parent_bg,
            anchor='w',
            justify='left'
        )
        self.quantity_label.pack(side='left', padx=(5, 0))

        # 创建描述标签（wraplength将在update_content中动态设置）
        self.desc_label = tk.Label(
            self.text_frame,
            font=('Segoe UI', 13),
            fg='#BFA98F',  # 描述默认浅色
            bg=parent_bg,
            anchor='w',
            wraplength=200,  # 初始值，会在update_content中更新
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
        lines = [line.strip()
                 for line in description.split('\n') if line.strip()]

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

    def update_content(
            self,
            name,
            description,
            icon_path=None,
            aspect_ratio=1.0):
        # 调试：在函数最开始就记录，确保被调用
        logging.info(f"[IconFrame调试] ========== update_content函数被调用 ==========")
        logging.info(f"[IconFrame调试] 参数: name='{name}', description长度={len(description) if description else 0}, icon_path={icon_path}")
        try:
            # 调试：记录调用，避免在正常运行中强制修改颜色
            logging.info(f"[IconFrame] update_content被调用: name='{name}' (长度={len(name) if name else 0})")
            # 获取当前背景色
            bg_color = self.cget('bg')

            # 处理名称和数量
            if name:
                # 先分离品质标记（格式可能是：名称：品质标记 或 名称：品质标记 x2）
                # 匹配模式：名称：品质标记（可选的 x数量）
                # 注意：使用中文冒号（：）匹配
                logging.info(f"[IconFrame] 开始解析名称: '{name}' (长度: {len(name)})")
                quality_match = re.search(r'^(.*?)：([铜银金钻传])(?:\s+x(\d+))?$', name)
                if quality_match:
                    logging.info(f"[IconFrame] 正则匹配成功: groups = {quality_match.groups()}")
                else:
                    logging.info(f"[IconFrame] 正则匹配失败，尝试检查冒号类型...")
                    # 检查是否包含中文冒号
                    if '：' in name:
                        logging.info(f"[IconFrame] 名称包含中文冒号（：）")
                    elif ':' in name:
                        logging.info(f"[IconFrame] 名称包含英文冒号（:），这可能导致匹配失败")
                    # 检查是否包含品质字符
                    for q in ['铜', '银', '金', '钻', '传']:
                        if q in name:
                            logging.info(f"[IconFrame] 名称包含品质字符: '{q}'")
                if quality_match:
                    base_name = quality_match.group(1)
                    quality_mark = quality_match.group(2)
                    quantity = quality_match.group(3)  # 可能为None
                    has_quality = True
                    # 设置品质标签的颜色（使用非常明显的测试样式，验证是否为独立元素）
                    # 测试：使用超大字体、明显边框、大内边距、测试文本
                    # 将品质颜色映射为接近附件的配色，字体统一为白色，字号比名称略小
                    quality_colors = {
                        '铜': {'bg': '#8B5A2B', 'fg': '#FFFFFF'},    # Bronze (深铜色)
                        '银': {'bg': '#6E6E6E', 'fg': '#FFFFFF'},    # Silver (深灰/银)
                        '金': {'bg': '#D4AF37', 'fg': '#FFFFFF'},    # Gold
                        '钻': {'bg': '#0E9AA7', 'fg': '#FFFFFF'},    # Diamond (青色系)
                        '传': {'bg': '#8B3E2F', 'fg': '#FFFFFF'}     # Legendary (深褐/酒红)
                    }
                    quality_color = quality_colors.get(quality_mark, {'bg': '#555555', 'fg': '#FFFFFF'})

                    # 设置品质标签样式：字体比名称略小（名称 14 -> 品质 12）
                    self.quality_label.config(
                        text=f'[{quality_mark}]',
                        bg=quality_color['bg'],
                        fg=quality_color['fg'],
                        font=('Segoe UI', 12, 'bold'),
                        anchor='center',
                        justify='center',
                        padx=6,
                        pady=2,
                        relief='solid',
                        bd=1
                    )

                    # 容器采用与标签一致的背景，容器边框保持轻量
                    self.quality_container.config(
                        relief='flat',
                        bd=0,
                        bg=quality_color['bg']
                    )
                    logging.info(f"[IconFrame] 解析出品质标签: {quality_mark}, 颜色: {quality_color['bg']}")
                    # 显示基础名称（数量在后面单独显示）
                    name_to_display = base_name
                else:
                    # 没有品质标记，隐藏品质标签
                    self.quality_container.pack_forget()
                    has_quality = False
                    logging.debug(f"[IconFrame] 未找到品质标记，隐藏品质标签: '{name}'")
                    # 尝试从名称中分离数量（格式：名称 x2）
                    quantity_match = re.search(r'^(.*?)\s+x(\d+)\s*$', name)
                    if quantity_match:
                        name_to_display = quantity_match.group(1)
                        quantity = quantity_match.group(2)
                    else:
                        name_to_display = name
                        quantity = None
                
                # 显示名称和数量（恢复默认配色）
                self.name_label.config(
                    text=name_to_display,
                    anchor='w',
                    justify='left',
                    bg=bg_color,
                    fg='#E8D4B9'
                )
                logging.info(f"[IconFrame] 名称标签已更新: text='{name_to_display}', fg='{self.name_label.cget('fg')}'")
                if quantity:
                    self.quantity_label.config(
                        text=f"×{quantity}",
                        bg=bg_color,
                        fg='#FFD700'
                    )
                    self.quantity_label.pack(side='left', padx=(5, 0))
                else:
                    self.quantity_label.pack_forget()
                
                # 如果有品质标记，现在pack品质标签（在数量后面）
                if quality_match:
                    self.quality_container.pack(side='left', padx=(5, 0))
                    quality_text = self.quality_label.cget('text')
                    quality_bg = self.quality_label.cget('bg')
                    quality_fg = self.quality_label.cget('fg')
                    container_relief = self.quality_container.cget('relief')
                    container_bd = self.quality_container.cget('bd')
                    container_bg = self.quality_container.cget('bg')
                    logging.info(f"[IconFrame] 品质标签已pack: text='{quality_text}', bg='{quality_bg}', fg='{quality_fg}'")
                    logging.info(f"[IconFrame] 品质容器状态: relief='{container_relief}', bd='{container_bd}', bg='{container_bg}'")
                else:
                    logging.info(f"[IconFrame] 无品质标记，品质标签未pack")
                
                self.name_container.pack(fill='x', anchor='w', pady=0)
                logging.info(f"[IconFrame] name_container已pack")
            else:
                self.name_container.pack_forget()

                # 描述左对齐（格式化描述）
            if description:
                formatted_description = self.format_description(description)
                
                # 动态计算wraplength：根据父容器宽度（两列模式下每列宽度）
                # 注意：这里使用默认值，实际wraplength会在窗口调整后通过_update_all_iconframes_wraplength更新
                try:
                    # 等待布局更新
                    self.update_idletasks()
                    # 获取当前框架的实际宽度
                    frame_width = self.winfo_width()
                    if frame_width > 0:
                        # 文本区域宽度 = 框架宽度 - 图标宽度(144) - 边距(20)
                        text_width = max(150, frame_width - 144 - 20)
                        # wraplength应该略小于实际宽度，确保换行
                        wraplength = max(150, text_width - 10)
                    else:
                        # 如果无法获取宽度，使用默认值（根据分辨率估算）
                        # 两列模式下，每列约300-400像素，文本区域约150-250像素
                        wraplength = 200
                except Exception:
                    wraplength = 200
                
                # 设置描述文本并恢复默认颜色
                self.desc_label.config(
                    text=formatted_description,
                    anchor='w',
                    justify='left',
                    bg=bg_color,
                    wraplength=wraplength,
                    fg='#BFA98F')
                
                self.desc_label.pack(fill='both', expand=True)
                logging.info(f"[IconFrame调试] ========== update_content完成 ==========")
            else:
                self.desc_label.pack_forget()

            # 图标处理
            icon_container_width = 144
            icon_container_height = 96
            self.icon_container.config(
                width=icon_container_width,
                height=icon_container_height,
                bg=bg_color)

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
                    img = img.resize(
                        (icon_width, icon_height), Image.Resampling.LANCZOS)

                    # 创建透明底图，保证居中
                    bg = Image.new(
                        'RGBA', (icon_container_width, icon_container_height), (0, 0, 0, 0))
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

        # 创建垂直滚动条（按需显示）
        try:
            self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
            # 先将滚动条放到右侧网格（可能会在不需要时隐藏）
            self.scrollbar.grid(row=0, column=1, sticky='ns')
            # 关联 canvas 的 yscrollcommand，使 scrollbar 可以控制 canvas
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
        except Exception:
            # 兼容性回退：确保属性存在
            self.scrollbar = None

        # 创建内部框架
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        self.inner_frame_id = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw")

        # 绑定事件
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner_frame.bind("<Configure>", self._on_frame_configure)

        # 当鼠标进入/离开 canvas 区域时，绑定/解绑滚轮事件（仅绑定到 canvas 本身，避免 bind_all 导致全局干扰）
        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        # 初始隐藏滚动条（如果存在）
        if self.scrollbar is not None:
            try:
                self.scrollbar.grid_remove()
            except Exception:
                pass
        # 标记：在处理全局滚轮时可暂时抑制 configure 行为以避免布局重置覆盖滚动
        self._suspend_configure = False
        # 本地 MouseWheel 最近一次时间戳（用于优先本地事件）
        self._local_wheel_last_ts = 0.0
        # 当启用全局滚轮时，是否优先使用本地 bind_all 事件
        self._local_wheel_primary = False

    def _on_canvas_configure(self, event):
        """当Canvas大小改变时，调整内部窗口宽度"""
        self.canvas.itemconfig(self.inner_frame_id, width=event.width)

    def _on_frame_configure(self, event):
        """当内部框架大小改变时，更新滚动区域"""
        # 更新Canvas的滚动区域
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass
        # 若处于抑制状态，仅更新 scrollregion 并退出，避免显示/隐藏滚动条等操作影响当前滚动
        try:
            if getattr(self, '_suspend_configure', False):
                return
        except Exception:
            pass
        # 根据内容高度决定是否显示滚动条（如果存在）
        try:
            if self.scrollbar is not None:
                inner_height = self.inner_frame.winfo_reqheight()
                canvas_height = self.canvas.winfo_height()
                bbox = None
                try:
                    bbox = self.canvas.bbox("all")
                except Exception:
                    pass
                logging.info(f"[ScrollableFrame] _on_frame_configure: inner_height={inner_height}, canvas_height={canvas_height}, bbox={bbox}")
                if inner_height > canvas_height:
                    try:
                        self.scrollbar.grid()
                        logging.info("[ScrollableFrame] _on_frame_configure: scrollbar shown")
                    except Exception:
                        logging.exception("[ScrollableFrame] _on_frame_configure: failed to grid scrollbar")
                else:
                    try:
                        self.scrollbar.grid_remove()
                        logging.info("[ScrollableFrame] _on_frame_configure: scrollbar hidden")
                    except Exception:
                        logging.exception("[ScrollableFrame] _on_frame_configure: failed to grid_remove scrollbar")
        except Exception:
            pass

    def _bind_mousewheel(self):
        """在鼠标进入时绑定滚轮事件（兼容 Windows/Linux/Mac）"""
        try:
            # 绑定到 canvas 自身事件，而不是全局绑定，避免鼠标移动触发全局滚动
            self.canvas.bind("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind("<Button-4>", self._on_mousewheel)
            self.canvas.bind("<Button-5>", self._on_mousewheel)
            logging.debug("[ScrollableFrame] bind mousewheel events to canvas")
        except Exception:
            logging.exception("[ScrollableFrame] _bind_mousewheel failed")

    def _unbind_mousewheel(self):
        """在鼠标离开时解绑全局滚轮事件"""
        try:
            self.canvas.unbind("<MouseWheel>")
            self.canvas.unbind("<Button-4>")
            self.canvas.unbind("<Button-5>")
            logging.debug("[ScrollableFrame] unbind mousewheel events from canvas")
        except Exception:
            logging.exception("[ScrollableFrame] _unbind_mousewheel failed")

    def enable_global_scroll(self):
        """显式启用全局滚轮绑定（用于在信息窗口显示时，即使鼠标不在窗口上也能滚动）"""
        try:
            # 恢复综合模式：启动底层 hook（RawInput/WH_MOUSE_LL）并启动轮询，同时也绑定本地 bind_all 作为回退/优先源
            # Emergency mode: do NOT start low-level hooks here — rely on bind_all only.
            # This avoids RawInput/WH_MOUSE_LL interference and lets Tkinter bind_all control scrolling.
            logging.info("[ScrollableFrame] enable_global_scroll: emergency bind_all-only mode (wheel_hook start skipped)")

            # 启动轮询任务（每50ms检查一次 wheel_hook.drain_events）
            if getattr(self, '_wheel_polling', False):
                return
            self._wheel_polling = True
            # 启动底层 hook 并启动轮询任务（优先使用本地 bind_all，但同时启用 WH_MOUSE_LL 以保证能捕获系统级滚轮）
            try:
                from main_script.system import wheel_hook
                try:
                    wheel_hook.start_hook(None)
                    logging.info("[ScrollableFrame] enable_global_scroll: wheel_hook.start_hook() invoked")
                except Exception:
                    logging.exception("[ScrollableFrame] enable_global_scroll: wheel_hook.start_hook() failed")
            except Exception:
                logging.exception("[ScrollableFrame] enable_global_scroll: unable to import wheel_hook")
            # 绑定全局鼠标滚轮到本地处理作回退（在启用全局滚轮时临时绑定）
            try:
                # bind_all 绑定到顶层窗口，确保无论焦点如何都能接收事件
                try:
                    root = self.canvas.winfo_toplevel()
                except Exception:
                    root = self.canvas
                root.bind_all("<MouseWheel>", self._on_mousewheel)
                root.bind_all("<Button-4>", self._on_mousewheel)
                root.bind_all("<Button-5>", self._on_mousewheel)
                self._global_mouse_bound = True
                logging.info("[ScrollableFrame] enable_global_scroll: bound global mousewheel (bind_all) as fallback")
            except Exception:
                logging.exception("[ScrollableFrame] enable_global_scroll: bind_all failed")
            # 优先使用本地 bind_all 事件（当有本地事件发生时短时间内忽略 hook 事件）
            self._local_wheel_primary = True
            self._local_wheel_last_ts = 0.0
            # 启动轮询以定期从 wheel_hook.drain_events 读取事件并分发到主线程处理
            try:
                def _poll_wheel_hook():
                    try:
                        from main_script.system import wheel_hook
                        try:
                            events = wheel_hook.drain_events()
                        except Exception:
                            events = []
                        if events:
                            for e in events:
                                try:
                                    # 调度到主线程的处理（保持与 _on_hook_scroll 接口一致）
                                    self.canvas.after(0, lambda val=e: self._on_hook_scroll(val))
                                except Exception:
                                    logging.exception("[ScrollableFrame] _poll_wheel_hook dispatch failed")
                    except Exception:
                        logging.exception("[ScrollableFrame] _poll_wheel_hook failed")
                    finally:
                        try:
                            if getattr(self, '_wheel_polling', False):
                                self._wheel_poll_task = self.canvas.after(50, _poll_wheel_hook)
                        except Exception:
                            pass
                # 立即启动一次轮询
                try:
                    self._wheel_poll_task = self.canvas.after(50, _poll_wheel_hook)
                except Exception:
                    # 退到直接调用以确保至少开始一次
                    try:
                        _poll_wheel_hook()
                    except Exception:
                        logging.exception("[ScrollableFrame] failed to start wheel_hook poll")
            except Exception:
                logging.exception("[ScrollableFrame] enable_global_scroll: failed to schedule wheel_hook polling")
        except Exception:
            logging.exception("[ScrollableFrame] enable_global_scroll failed")

    def disable_global_scroll(self):
        """显式禁用全局滚轮绑定"""
        try:
            # 停止轮询任务
            if getattr(self, '_wheel_polling', False):
                self._wheel_polling = False
                try:
                    if getattr(self, '_wheel_poll_task', None):
                        self.canvas.after_cancel(self._wheel_poll_task)
                        self._wheel_poll_task = None
                except Exception:
                    logging.exception("[ScrollableFrame] cancel poll task failed")
            # 停止底层 hook（如果已启动），并记录
            try:
                from main_script.system import wheel_hook
                try:
                    wheel_hook.stop_hook()
                    logging.info("[ScrollableFrame] disable_global_scroll: wheel_hook.stop_hook() called")
                except Exception:
                    try:
                        wheel_hook.stop_raw_input_listener()
                        logging.info("[ScrollableFrame] disable_global_scroll: wheel_hook.stop_raw_input_listener() called")
                    except Exception:
                        logging.exception("[ScrollableFrame] wheel_hook stop failed")
            except Exception:
                logging.debug("[ScrollableFrame] disable_global_scroll: unable to import wheel_hook (may not be started)")
            # 解除全局 bind_all 回退（若已绑定）
            try:
                if getattr(self, '_global_mouse_bound', False):
                    try:
                        root = self.canvas.winfo_toplevel()
                    except Exception:
                        root = self.canvas
                    root.unbind_all("<MouseWheel>")
                    root.unbind_all("<Button-4>")
                    root.unbind_all("<Button-5>")
                    self._global_mouse_bound = False
                    logging.info("[ScrollableFrame] disable_global_scroll: unbound global mousewheel fallback")
            except Exception:
                logging.exception("[ScrollableFrame] disable_global_scroll: unbind_all failed")
        except Exception:
            logging.exception("[ScrollableFrame] disable_global_scroll failed")

    def _on_hook_scroll(self, units):
        """被系统钩子线程调用；在主线程中调度实际滚动"""
        try:
            logging.info(f"[ScrollableFrame] _on_hook_scroll called with raw_delta={units}")
            # 如果本地 bind_all 被启用并且最近收到了本地滚轮事件，则优先使用本地事件，短时间内忽略 hook 事件
            try:
                import time as _time
                last = getattr(self, '_local_wheel_last_ts', 0)
                if getattr(self, '_local_wheel_primary', False) and ( _time.time() - last ) < 0.35:
                    logging.debug("[ScrollableFrame] _on_hook_scroll ignored due to recent local mousewheel event")
                    return
            except Exception:
                pass
            if self.canvas:
                def _do_scroll():
                    try:
                        # 进入滚动处理，暂时抑制 _on_frame_configure 的显式显示/隐藏行为
                        try:
                            self._suspend_configure = True
                        except Exception:
                            pass
                        # 定义解除抑制函数
                        def _unsuspend():
                            try:
                                self._suspend_configure = False
                            except Exception:
                                pass
                            try:
                                self.update_scrollregion()
                            except Exception:
                                pass
                        # 辅助：在无法使用 after 时直接调用
                        def _schedule_unsuspend():
                            try:
                                self.canvas.after(100, _unsuspend)
                            except Exception:
                                try:
                                    _unsuspend()
                                except Exception:
                                    pass
                        raw_delta = units
                        # 先尝试将原始 delta 转为按比例移动（每120为一档）
                        try:
                            frac_per_120 = 0.2  # 每120对应该比例步长（可调）
                            try:
                                # 反转符号以修正滚动方向：raw_delta 正数（向下）-> delta_frac 负数（向下滚动）
                                delta_frac = -float(raw_delta) / 120.0 * frac_per_120
                            except Exception:
                                delta_frac = -frac_per_120 if raw_delta > 0 else frac_per_120

                            # 最小步长阈值，避免极小 delta 无效（但不要太大）
                            if 0 < abs(delta_frac) < 0.01:
                                delta_frac = 0.01 if delta_frac > 0 else -0.01

                            # 限制单次移动幅度，防止一次跳到底
                            if delta_frac > 0.8:
                                delta_frac = 0.8
                            if delta_frac < -0.8:
                                delta_frac = -0.8

                            # 记录滚动前状态（确保读取最新视图）
                            try:
                                self.update_idletasks()
                            except Exception:
                                pass
                            try:
                                cur = self.canvas.yview()
                            except Exception:
                                cur = None
                            try:
                                bbox = self.canvas.bbox("all")
                            except Exception:
                                bbox = None
                            try:
                                canvas_h = self.canvas.winfo_height()
                            except Exception:
                                canvas_h = None
                            logging.info(f"[ScrollableFrame] pre_scroll yview={cur}, bbox={bbox}, canvas_h={canvas_h}")

                            # 计算新的视图位置：基于当前 top（cur[0]）增加或减少 delta_frac
                            try:
                                if cur and isinstance(cur, (list, tuple)):
                                    top = float(cur[0])
                                else:
                                    top = 0.0
                                new = top + delta_frac
                                # 边界约束
                                new = max(0.0, min(1.0, new))
                                # 如果 new 与 top 相等（例如处于边界），仍然尝试小幅回退以允许回弹
                                if new == top and delta_frac < 0 and top > 0.0:
                                    # 在到达底部后尝试小步上移
                                    new = max(0.0, top + max(delta_frac, -0.05))
                                self.canvas.yview_moveto(new)
                                logging.info(f"[ScrollableFrame] _on_hook_scroll performed yview_moveto new={new:.4f} (delta_frac={delta_frac:.4f}, raw={raw_delta}, old_top={top:.4f})")
                            except Exception:
                                logging.exception("[ScrollableFrame] _on_hook_scroll proportional move failed")

                            # 在返回前安排解除抑制和刷新
                            _schedule_unsuspend()
                        except Exception:
                            logging.exception("[ScrollableFrame] simplified scroll handling failed")
                    except Exception:
                        logging.exception("[ScrollableFrame] _on_hook_scroll failed")
                    finally:
                        # 确保在所有路径下都会解除抑制（延迟）
                        _schedule_unsuspend()
                self.canvas.after(0, _do_scroll)
        except Exception:
            logging.exception("_on_hook_scroll failed")

    def _on_mousewheel(self, event):
        """处理鼠标本地滚轮事件（绑定到 canvas），兼容 Windows/Mac/Linux"""
        try:
            # X11: event.num == 4 (up), 5 (down)
            # 将本地事件转换为与 hook 一致的 raw_delta（positive -> DOWN）
            if hasattr(event, 'num') and event.num in (4, 5):
                # num==4 -> up, num==5 -> down
                raw_delta = -120 if event.num == 4 else 120
            else:
                delta = getattr(event, 'delta', 0)
                try:
                    # Windows: event.delta is 120 for up, -120 for down. Normalize to hook raw: positive = DOWN
                    raw_delta = int(-delta)
                except Exception:
                    raw_delta = 0
            logging.debug(f"[ScrollableFrame] _on_mousewheel raw_delta={raw_delta}, event_delta={getattr(event,'delta',None)}")
            # 记录本地滚轮时间戳，用于优先级判断
            try:
                import time as _time
                self._local_wheel_last_ts = _time.time()
            except Exception:
                pass
            # 使用与 hook 相同的按比例移动逻辑以保持一致性
            try:
                # 计算移动比例
                frac_per_120 = 0.2
                try:
                    # 反转符号以修正滚动方向：raw_delta 正数（向下）-> delta_frac 负数（向下滚动）
                    delta_frac = -float(raw_delta) / 120.0 * frac_per_120
                except Exception:
                    delta_frac = -frac_per_120 if raw_delta > 0 else frac_per_120
                if delta_frac > 0.8:
                    delta_frac = 0.8
                if delta_frac < -0.8:
                    delta_frac = -0.8
                cur = self.canvas.yview()
                if cur and isinstance(cur, (list, tuple)):
                    new = max(0.0, min(1.0, cur[0] + delta_frac))
                    self.canvas.yview_moveto(new)
                    logging.info(f"[ScrollableFrame] _on_mousewheel performed yview_moveto new={new:.4f} (delta_frac={delta_frac:.4f}, raw={raw_delta})")
                else:
                    logging.debug("[ScrollableFrame] _on_mousewheel: no yview available")
            except Exception:
                logging.exception("[ScrollableFrame] _on_mousewheel proportional move failed")
        except Exception:
            logging.exception("[ScrollableFrame] _on_mousewheel failed")

    def update_scrollregion(self):
        """手动更新滚动区域"""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass
        # 按需显示或隐藏滚动条
        try:
            if self.scrollbar is not None:
                inner_height = self.inner_frame.winfo_reqheight()
                canvas_height = self.canvas.winfo_height()
                bbox = None
                try:
                    bbox = self.canvas.bbox("all")
                except Exception:
                    pass
                logging.info(f"[ScrollableFrame] update_scrollregion: inner_height={inner_height}, canvas_height={canvas_height}, bbox={bbox}")
                if inner_height > canvas_height:
                    try:
                        self.scrollbar.grid()
                        logging.info("[ScrollableFrame] update_scrollregion: scrollbar shown")
                    except Exception:
                        logging.exception("[ScrollableFrame] update_scrollregion: failed to grid scrollbar")
                else:
                    try:
                        self.scrollbar.grid_remove()
                        logging.info("[ScrollableFrame] update_scrollregion: scrollbar hidden")
                    except Exception:
                        logging.exception("[ScrollableFrame] update_scrollregion: failed to grid_remove scrollbar")
        except Exception:
            logging.debug("[ScrollableFrame] update_scrollregion: 获取高度信息失败")

    def get_inner_frame(self):
        """获取内部框架"""
        return self.inner_frame
