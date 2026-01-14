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
                    self.name_label.config(
                        text=base_name, anchor='w', justify='left', bg=bg_color)
                    self.quantity_label.config(
                        text=f"×{quantity}", bg=bg_color)  # 使用中文乘号
                    self.quantity_label.pack(side='left', padx=(5, 0))
                else:
                    self.name_label.config(
                        text=name, anchor='w', justify='left', bg=bg_color)
                    self.quantity_label.pack_forget()
                self.name_container.pack(fill='x', anchor='w', pady=0)
            else:
                self.name_container.pack_forget()

            # 描述左对齐（格式化描述）
            if description:
                formatted_description = self.format_description(description)
                self.desc_label.config(
                    text=formatted_description,
                    anchor='w',
                    justify='left',
                    bg=bg_color)
                self.desc_label.pack(fill='both', expand=True)
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

        # 创建滚动条
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # 配置Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 创建内部框架
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        self.inner_frame_id = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw")

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
