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

        # 创建名称标签（测试：所有字体改为绿色）
        self.name_label = tk.Label(
            self.name_container,
            font=('Segoe UI', 14, 'bold'),
            fg='#00FF00',  # 测试：绿色文字
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
            fg='#00FF00',  # 测试：绿色文字
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
            fg='#00FF00',  # 测试：绿色文字
            bg=parent_bg,
            anchor='w',
            justify='left'
        )
        self.quantity_label.pack(side='left', padx=(5, 0))

        # 创建描述标签（wraplength将在update_content中动态设置）
        self.desc_label = tk.Label(
            self.text_frame,
            font=('Segoe UI', 13),
            fg='#00FF00',  # 测试：绿色文字
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
            # 强制测试：立即改变名称标签颜色，验证函数是否被调用
            logging.info(f"[IconFrame] update_content被调用: name='{name}' (长度={len(name) if name else 0})")
            # 先强制设置一个明显的颜色，确保函数被执行
            try:
                self.name_label.config(fg='#00FF00')  # 先设置为绿色，确保函数被执行
                self.name_label['fg'] = '#00FF00'
                logging.info(f"[IconFrame] 名称标签颜色已强制设置为绿色（测试）")
            except Exception as e:
                logging.error(f"[IconFrame] 设置名称标签颜色失败: {e}")
            
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
                    quality_colors = {
                        '铜': {'bg': '#FF0000', 'fg': '#FFFF00'},  # 红色背景，黄色文字（非常明显）
                        '银': {'bg': '#00FF00', 'fg': '#0000FF'},  # 绿色背景，蓝色文字（非常明显）
                        '金': {'bg': '#0000FF', 'fg': '#FF00FF'},  # 蓝色背景，紫色文字（非常明显）
                        '钻': {'bg': '#FFFF00', 'fg': '#FF0000'},  # 黄色背景，红色文字（非常明显）
                        '传': {'bg': '#FF00FF', 'fg': '#00FFFF'}   # 紫色背景，青色文字（非常明显）
                    }
                    quality_color = quality_colors.get(quality_mark, {'bg': '#FF0000', 'fg': '#FFFFFF'})
                    # 更新品质标签（使用超大字体和明显样式进行测试）
                    quality_config = {
                        'text': f'[{quality_mark}]',  # 添加方括号，更容易识别
                        'bg': quality_color['bg'],
                        'fg': quality_color['fg'],
                        'font': ('Segoe UI', 20, 'bold'),  # 超大字体（从10改为20）
                        'anchor': 'center',
                        'justify': 'center',
                        'relief': 'raised',  # 添加明显的3D边框
                        'bd': 3,  # 粗边框
                        'padx': 15,  # 超大内边距（从6改为15）
                        'pady': 8   # 超大内边距（从2改为8）
                    }
                    # 配置品质标签
                    self.quality_label.config(**quality_config)
                    # 强制更新标签背景色（确保颜色应用）
                    self.quality_label['bg'] = quality_color['bg']
                    self.quality_label['fg'] = quality_color['fg']
                    self.quality_label['font'] = ('Segoe UI', 20, 'bold')
                    self.quality_label['relief'] = 'raised'
                    self.quality_label['bd'] = 3
                    self.quality_label['padx'] = 15
                    self.quality_label['pady'] = 8
                    
                    # 如果是黄金，给容器添加边框
                    if quality_mark == '金':
                        self.quality_container.config(
                            relief='solid',
                            bd=1,
                            bg='#FFD700'  # 金色边框（通过容器背景色和bd实现）
                        )
                        # 调整标签内边距以适应边框
                        self.quality_label.config(padx=3, pady=0)
                    else:
                        self.quality_container.config(
                            relief='raised',  # 容器也添加明显边框
                            bd=3,  # 粗边框
                            bg=quality_color['bg']  # 容器背景色也设置为品质颜色
                        )
                        # 内边距已在上面设置，这里不需要重复
                    
                    # 确保标签背景色与容器一致（再次确认）
                    self.quality_label['bg'] = quality_color['bg']
                    self.quality_label['fg'] = quality_color['fg']
                    self.quality_container['bg'] = quality_color['bg']
                    # 注意：品质标签暂时不pack，等数量标签pack后再pack，以确保顺序为：名称 -> 数量 -> 品质
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
                
                # 显示名称和数量（测试：强制所有文字为绿色）
                # 强制设置为绿色，不区分是否有品质标记
                name_color = '#00FF00'  # 强制绿色
                logging.info(f"[IconFrame] 名称标签颜色强制设置为绿色")
                
                # 强制设置所有标签为绿色，多次设置确保生效
                self.name_label.config(
                    text=name_to_display, 
                    anchor='w', 
                    justify='left', 
                    bg=bg_color,
                    fg='#00FF00'  # 测试：强制绿色文字
                )
                # 强制设置颜色为绿色（多次设置）
                self.name_label['fg'] = '#00FF00'
                try:
                    self.name_label.configure(fg='#00FF00')
                except Exception:
                    pass
                # 同时强制设置品质标签和数量标签为绿色
                if quality_match:
                    self.quality_label['fg'] = '#00FF00'
                    try:
                        self.quality_label.configure(fg='#00FF00')
                    except Exception:
                        pass
                if quantity:
                    self.quantity_label['fg'] = '#00FF00'
                    try:
                        self.quantity_label.configure(fg='#00FF00')
                    except Exception:
                        pass
                logging.info(f"[IconFrame] 所有标签颜色已强制设置为绿色: name='{name_to_display}'")
                logging.info(f"[IconFrame] 名称标签已更新: text='{name_to_display}', fg='{name_color}'")
                if quantity:
                    self.quantity_label.config(
                        text=f"×{quantity}", 
                        bg=bg_color,
                        fg='#00FF00'  # 测试：强制绿色文字
                    )
                    self.quantity_label['fg'] = '#00FF00'  # 强制设置
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
                
                # 调试：记录设置前的颜色
                desc_fg_before_set = self.desc_label.cget('fg')
                logging.info(f"[IconFrame调试] 设置描述标签前颜色: {desc_fg_before_set}")
                
                # 强制设置为绿色，多次设置确保生效
                self.desc_label.config(
                    text=formatted_description,
                    anchor='w',
                    justify='left',
                    bg=bg_color,
                    wraplength=wraplength,
                    fg='#00FF00')  # 测试：强制绿色文字
                self.desc_label['fg'] = '#00FF00'  # 强制设置
                # 再次强制设置，确保生效
                try:
                    self.desc_label.configure(fg='#00FF00')
                except Exception:
                    pass
                
                # 调试：记录设置后的颜色
                desc_fg_after_set = self.desc_label.cget('fg')
                logging.info(f"[IconFrame调试] 设置描述标签后颜色: {desc_fg_after_set} (期望: #00FF00)")
                if desc_fg_after_set != '#00FF00':
                    logging.error(f"[IconFrame调试] 警告：描述标签颜色设置失败！期望#00FF00，实际{desc_fg_after_set}")
                
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

        # 当鼠标进入/离开 canvas 区域时，绑定/解绑滚轮事件（避免全局绑定导致焦点问题）
        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        # 初始隐藏滚动条（如果存在）
        if self.scrollbar is not None:
            try:
                self.scrollbar.grid_remove()
            except Exception:
                pass

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
        # 根据内容高度决定是否显示滚动条（如果存在）
        try:
            if self.scrollbar is not None:
                inner_height = self.inner_frame.winfo_reqheight()
                canvas_height = self.canvas.winfo_height()
                if inner_height > canvas_height:
                    try:
                        self.scrollbar.grid()
                    except Exception:
                        pass
                else:
                    try:
                        self.scrollbar.grid_remove()
                    except Exception:
                        pass
        except Exception:
            pass

    def _bind_mousewheel(self):
        """在鼠标进入时绑定滚轮事件（兼容 Windows/Linux/Mac）"""
        # 全局滚轮绑定已移除：此函数保留为空以兼容旧调用
        logging.debug("[ScrollableFrame] _bind_mousewheel skipped (wheel disabled)")

    def _unbind_mousewheel(self):
        """在鼠标离开时解绑全局滚轮事件"""
        # 全局滚轮绑定已移除：此函数保留为空以兼容旧调用
        logging.debug("[ScrollableFrame] _unbind_mousewheel skipped (wheel disabled)")

    def enable_global_scroll(self):
        """显式启用全局滚轮绑定（用于在信息窗口显示时，即使鼠标不在窗口上也能滚动）"""
        # 全局滚轮功能已移除，保留方法以兼容调用
        logging.debug("[ScrollableFrame] enable_global_scroll called but wheel functionality is disabled")

    def disable_global_scroll(self):
        """显式禁用全局滚轮绑定"""
        # 全局滚轮功能已移除；取消任何残留轮询任务
        try:
            if hasattr(self, '_wheel_polling') and getattr(self, '_wheel_polling', False):
                self._wheel_polling = False
                try:
                    if getattr(self, '_wheel_poll_task', None):
                        self.canvas.after_cancel(self._wheel_poll_task)
                        self._wheel_poll_task = None
                except Exception:
                    pass
        except Exception:
            pass

    def _on_hook_scroll(self, units):
        """被系统钩子线程调用；在主线程中调度实际滚动"""
        try:
            # units already computed as integer (positive = scroll down)
            if self.canvas:
                self.canvas.after(0, lambda: self.canvas.yview_scroll(units, "units"))
        except Exception:
            logging.exception("_on_hook_scroll failed")

    def _on_mousewheel(self, event):
        """滚轮事件处理已移除（不再响应滚轮）"""
        logging.debug("[ScrollableFrame] _on_mousewheel ignored (wheel disabled)")

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
                if inner_height > canvas_height:
                    try:
                        self.scrollbar.grid()
                    except Exception:
                        pass
                else:
                    try:
                        self.scrollbar.grid_remove()
                    except Exception:
                        pass
        except Exception:
            logging.debug("[ScrollableFrame] update_scrollregion: 获取高度信息失败")

    def get_inner_frame(self):
        """获取内部框架"""
        return self.inner_frame
