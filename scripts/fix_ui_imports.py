#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助脚本：修复 UI 模块文件、清理缓存并验证导入。
在项目根运行： python scripts\fix_ui_imports.py
它会：
 - 备份并重写 main_script/ui/components.py 为已知良好版本
 - 删除 __pycache__ 目录
 - 输出相关文件路径与导入测试结果（便于将输出贴回给我）
"""
from __future__ import annotations
import os
import shutil
import time
import traceback
import importlib
import sys


ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
TARGET = os.path.join(ROOT, "main_script", "ui", "components.py")
BACKUP_SUFFIX = time.strftime(".bak-%Y%m%d-%H%M%S")


def backup_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    dest = path + BACKUP_SUFFIX
    shutil.copy2(path, dest)
    return dest


def write_fixed_components(path: str) -> None:
    """写入已修复的 components.py（覆盖）"""
    fixed = r'''"""GUI 组件模块（IconFrame 与 ScrollableFrame）
已重写以保证缩进与可读性，接口保持向后兼容。
"""
import io
import os
import re
import logging
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class IconFrame(tk.Frame):
    """用于显示图标和文本的框架"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        parent_bg = parent.cget("bg") if parent else "#1C1810"
        self.configure(bg=parent_bg)

        self.icon_container = tk.Frame(self, bg=parent_bg, width=144, height=96)
        self.icon_container.pack_propagate(False)
        self.icon_container.pack(side="left", padx=0, pady=0)

        self.icon_label = tk.Label(self.icon_container, bg=parent_bg)
        self.icon_label.pack(expand=True)

        self.text_frame = tk.Frame(self, bg=parent_bg)
        self.text_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        self.name_container = tk.Frame(self.text_frame, bg=parent_bg)
        self.name_container.pack(fill="x", anchor="w", pady=0)

        self.name_label = tk.Label(
            self.name_container,
            font=("Segoe UI", 14, "bold"),
            fg="#E8D4B9",
            bg=parent_bg,
            anchor="w",
            justify="left",
        )
        self.name_label.pack(side="left", anchor="w")

        self.quantity_label = tk.Label(
            self.name_container,
            font=("Segoe UI", 16, "bold"),
            fg="#FFD700",
            bg=parent_bg,
            anchor="w",
            justify="left",
        )
        self.quantity_label.pack(side="left", padx=(5, 0))

        self.desc_label = tk.Label(
            self.text_frame,
            font=("Segoe UI", 13),
            fg="#BFA98F",
            bg=parent_bg,
            anchor="w",
            wraplength=400,
            justify="left",
        )
        self.desc_label.pack(fill="both", expand=True, anchor="w")

        self._photo_refs = []

    def format_description(self, description):
        if not description:
            return ""
        description = re.sub(r"(\\d+\\.?\\d*)\\n秒\\n", r"\\1 秒 ", description)
        lines = [line.strip() for line in description.split("\\n") if line.strip()]
        if not lines:
            return ""
        formatted = []
        cur = ""
        for line in lines:
            if not cur:
                cur = line
                continue
            is_new = any(line.startswith(k) for k in ("使用", "当", "如果", "此物品"))
            if len(cur) > 60 and is_new:
                formatted.append(cur)
                cur = line
            elif len(cur) > 60:
                cur += "，" + line
            else:
                cur += "，" + line
        if cur:
            formatted.append(cur)
        return "\\n".join(formatted)

    def update_content(self, name, description, icon_path=None, aspect_ratio=1.0):
        try:
            bg_color = self.cget("bg")
            if name:
                qm = re.search(r"^(.*?)\\s*x(\\d+)\\s*$", name)
                if qm:
                    base_name, quantity = qm.group(1), qm.group(2)
                    self.name_label.config(text=base_name, anchor="w", justify="left", bg=bg_color)
                    self.quantity_label.config(text=f"×{quantity}", bg=bg_color)
                    self.quantity_label.pack(side="left", padx=(5, 0))
                else:
                    self.name_label.config(text=name, anchor="w", justify="left", bg=bg_color)
                    self.quantity_label.pack_forget()
                self.name_container.pack(fill="x", anchor="w", pady=0)
            else:
                self.name_container.pack_forget()

            if description:
                fd = self.format_description(description)
                self.desc_label.config(text=fd, anchor="w", justify="left", bg=bg_color)
                self.desc_label.pack(fill="both", expand=True)
            else:
                self.desc_label.pack_forget()

            icon_w, icon_h = 144, 96
            self.icon_container.config(width=icon_w, height=icon_h, bg=bg_color)
            if icon_path and os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path).convert("RGBA")
                    icon_height = icon_h
                    icon_width = int(icon_height * aspect_ratio)
                    icon_width = min(icon_width, icon_w)
                    img = img.resize((icon_width, icon_height), Image.Resampling.LANCZOS)
                    bg = Image.new("RGBA", (icon_w, icon_h), (0, 0, 0, 0))
                    offset_x = (icon_w - icon_width) // 2
                    bg.paste(img, (offset_x, 0), img)
                    with io.BytesIO() as out:
                        bg.save(out, format="PNG")
                        photo = ImageTk.PhotoImage(data=out.getvalue())
                        self.icon_label.configure(image=photo, bg=bg_color)
                        self._photo_refs.append(photo)
                except Exception:
                    logging.exception("加载图标失败")
                    self.clear_icon()
            else:
                self.clear_icon()
            self.icon_container.pack(side="left", padx=0, pady=0)
            self.update()
        except Exception:
            logging.exception("update_content failed")

    def clear_icon(self):
        try:
            bg_color = self.cget("bg")
            self.icon_label.configure(image="", bg=bg_color)
            self._photo_refs.clear()
        except Exception:
            logging.exception("clear_icon failed")

    def destroy(self):
        try:
            self.clear_icon()
            super().destroy()
        except Exception:
            logging.exception("destroy IconFrame failed")


class ScrollableFrame(tk.Frame):
    """简化的可滚动框架（默认不启用滚轮）"""

    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop("bg", "#1C1810")
        super().__init__(parent, **kwargs)
        self.configure(bg=bg_color)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = None
        self.canvas.configure(yscrollcommand=lambda *a: None)

        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner_frame.bind("<Configure>", self._on_frame_configure)

        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        if self.scrollbar is not None:
            try:
                self.scrollbar.grid_remove()
            except Exception:
                pass

    def _on_canvas_configure(self, event):
        try:
            self.canvas.itemconfig(self.inner_frame_id, width=event.width)
        except Exception:
            logging.exception("_on_canvas_configure failed")

    def _on_frame_configure(self, event):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            if getattr(self, "scrollbar", None):
                try:
                    self.scrollbar.grid_remove()
                except Exception:
                    pass
        except Exception:
            logging.exception("_on_frame_configure failed")

    def _bind_mousewheel(self):
        logging.debug("[ScrollableFrame] _bind_mousewheel skipped (wheel disabled)")

    def _unbind_mousewheel(self):
        logging.debug("[ScrollableFrame] _unbind_mousewheel skipped (wheel disabled)")

    def enable_global_scroll(self):
        logging.debug("[ScrollableFrame] enable_global_scroll called but wheel disabled")

    def disable_global_scroll(self):
        try:
            if hasattr(self, "_wheel_polling") and getattr(self, "_wheel_polling", False):
                self._wheel_polling = False
                try:
                    if getattr(self, "_wheel_poll_task", None):
                        self.canvas.after_cancel(self._wheel_poll_task)
                        self._wheel_poll_task = None
                except Exception:
                    pass
        except Exception:
            logging.exception("disable_global_scroll failed")

    def _on_hook_scroll(self, units):
        try:
            if self.canvas:
                self.canvas.after(0, lambda: self.canvas.yview_scroll(units, "units"))
        except Exception:
            logging.exception("_on_hook_scroll failed")

    def _on_mousewheel(self, event):
        logging.debug("[ScrollableFrame] _on_mousewheel ignored (wheel disabled)")

    def update_scrollregion(self):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            if self.scrollbar is not None:
                try:
                    self.scrollbar.grid_remove()
                except Exception:
                    pass
        except Exception:
            logging.exception("update_scrollregion failed")

    def get_inner_frame(self):
        return self.inner_frame
