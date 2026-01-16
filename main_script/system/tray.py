"""
系统托盘模块
"""
import pystray
import logging
import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw
import datetime


def safe_flush():
    """安全地刷新输出流（打包后可能没有控制台）"""
    try:
        if sys.stdout is not None:
            sys.stdout.flush()
    except:
        pass
    try:
        if sys.stderr is not None:
            sys.stderr.flush()
    except:
        pass


def get_resource_path(relative_path):
    """获取资源的绝对路径，兼容开发和 PyInstaller 打包环境"""
    # 1. 打包环境：PyInstaller 会把资源解压到 _MEIPASS 根目录
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        # 2. 开发环境：从当前文件回溯到项目根目录
        # 当前文件: project/main_script/system/tray.py
        # 项目根目录: project/
        base_path = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__))))

    result_path = os.path.join(base_path, relative_path)
    exists = os.path.exists(result_path)
    logging.info(
        f"[SystemTray] DEBUG PATH: base_path={base_path}, relative_path={relative_path}, "
        f"result_path={result_path}, exists={exists}"
    )

    # 3. 兜底：如果上面的路径不存在，再尝试当前工作目录
    if not exists:
        cwd_fallback = os.path.join(os.getcwd(), relative_path)
        logging.info(
            f"[SystemTray] DEBUG PATH: primary not found, try cwd fallback: {cwd_fallback}, "
            f"exists={os.path.exists(cwd_fallback)}"
        )
        if os.path.exists(cwd_fallback):
            result_path = cwd_fallback

    return result_path


class SystemTray:
    def __init__(self, controller_instance):
        # 保存对 controller 的引用，用于访问主线程的 GUI
        self.controller = controller_instance
        # 直接写入文件，确保能看到输出（绕过日志缓冲）
        debug_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tray_debug.txt")
        try:
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.datetime.now()}] SystemTray.__init__ 开始\n")
                f.flush()
        except:
            pass
        
        # 强制刷新日志输出，确保日志立即显示（打包后可能没有控制台）
        safe_flush()
        
        try:
            # self.controller 已在上面赋值，这里不需要重复
            self.icon = None
            
            # 双重输出：日志 + 文件 + 直接打印
            msg = "[SystemTray] ========== 初始化开始 =========="
            print(msg)  # 直接打印到控制台
            logging.info(msg)
            try:
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(f"{msg}\n")
                    f.flush()
            except:
                pass
            
            controller_msg = f"[SystemTray] controller对象: {self.controller}"
            print(controller_msg)
            logging.info(controller_msg)
            safe_flush()
            
            self.create_tray_icon()  # 确保在初始化时调用
            
            final_msg = f"[SystemTray] 初始化完成，icon对象: {self.icon}"
            print(final_msg)
            logging.info(final_msg)
            
            type_msg = f"[SystemTray] icon类型: {type(self.icon)}"
            print(type_msg)
            logging.info(type_msg)
            
            none_msg = f"[SystemTray] icon is None: {self.icon is None}"
            print(none_msg)
            logging.info(none_msg)
            
            try:
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(f"{final_msg}\n{type_msg}\n{none_msg}\n")
                    f.flush()
            except:
                pass
            
            logging.info("[SystemTray] ========== 初始化结束 ==========")
            safe_flush()
        except Exception as e:
            error_msg = f"[SystemTray] 初始化失败: {e}"
            logging.error(error_msg)
            print(error_msg)  # 直接打印到控制台
            import traceback
            tb = traceback.format_exc()
            logging.error(tb)
            print(tb)  # 直接打印到控制台
            try:
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(f"{error_msg}\n{tb}\n")
                    f.flush()
            except:
                pass
            safe_flush()
            self.icon = None
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        import sys
        safe_flush()
        
        logging.info("[SystemTray] ========== 开始创建托盘图标 ==========")
        logging.info("[SystemTray] 正在构建图标对象...")
        
        # 1. 准备菜单
        try:
            menu = pystray.Menu(
                pystray.MenuItem("说明", self._show_help),
                pystray.MenuItem("日志", self._open_log),
                pystray.MenuItem("联系我", self._open_contact),
                pystray.MenuItem("赞助", self._open_sponsor),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._quit_application)
            )
            logging.info("[SystemTray] 菜单创建成功")
        except Exception as e:
            logging.error(f"[SystemTray] 创建菜单失败: {e}")
            # 即使菜单失败，也尝试给个基础菜单
            try:
                menu = pystray.Menu(pystray.MenuItem("退出", self._quit_application))
            except:
                menu = None
                logging.error("[SystemTray] 无法创建任何菜单")

        # 2. 加载图片逻辑
        icon_image = None
        icon_path = get_resource_path("Bazaar_Lens.ico")
        logging.info(f"[SystemTray] 尝试加载图标: {icon_path}")

        try:
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
                icon_image.load()  # 强制载入内存
                logging.info(f"[SystemTray] 成功加载图标文件: {icon_path}, 尺寸: {icon_image.size}")
                # 确认图片读取：检查尺寸是否为 (0,0)
                if icon_image.size == (0, 0):
                    logging.error("[SystemTray] 警告：图标文件尺寸为 (0,0)，可能读取失败")
                    icon_image = None
            else:
                logging.warning(f"[SystemTray] 图标文件未找到: {icon_path}")
        except Exception as e:
            logging.error(f"[SystemTray] 加载图标文件失败: {e}")
            import traceback
            logging.error(traceback.format_exc())

        # 3. 兜底方案：如果文件加载失败，创建一个简单的内存图标
        # 强制生成机制：即使图片丢了，托盘图标也会出现（显示为一个色块）
        if not icon_image or icon_image.size == (0, 0):
            logging.warning("[SystemTray] 图标文件加载失败，正在生成内存兜底图标...")
            # 创建一个 64x64 的 RGBA 图像
            icon_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon_image)
            # 画一个醒目的圆圈，确保你一眼能看到它（使用用户要求的颜色）
            draw.ellipse((4, 4, 60, 60), fill='#0078D7', outline='white', width=4)
            logging.info("[SystemTray] 内存兜底图标生成完成")
            
        # 4. 创建 pystray.Icon 实例（必须创建，即使图标文件加载失败也要有兜底图标）
        try:
            # 确保 icon_image 一定存在（如果前面都失败了，这里应该已经有兜底图标了）
            if not icon_image or icon_image.size == (0, 0):
                logging.warning("[SystemTray] icon_image 仍然无效，强制生成兜底图标...")
                icon_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(icon_image)
                draw.ellipse((4, 4, 60, 60), fill='#0078D7', outline='white', width=4)
                logging.info("[SystemTray] 强制生成的兜底图标已创建")
            
            logging.info("[SystemTray] 正在调用 pystray.Icon()...")
            logging.info(f"[SystemTray] 参数检查: icon_image类型={type(icon_image)}, icon_image尺寸={icon_image.size if icon_image else 'None'}, menu类型={type(menu)}")
            
            # 调试：检查 pystray 是否能找到后端
            try:
                from pystray import BACKENDS
                logging.info(f"[SystemTray] 可用的 pystray 后端: {BACKENDS}")
            except ImportError:
                logging.warning("[SystemTray] 无法导入 BACKENDS，可能版本不兼容")
            except AttributeError:
                logging.warning("[SystemTray] BACKENDS 属性不存在，可能版本不兼容")
            
            # 显式指定参数名，防止某些版本 pystray 签名不一致
            print("[SystemTray] 正在调用 pystray.Icon()...")
            safe_flush()
            
            temp_icon = pystray.Icon(
                name="Bazaar Lens",
                icon=icon_image,
                title="Bazaar Lens",
                menu=menu
            )
            
            # 关键：直接打印到控制台，确保能看到
            print(f"[SystemTray] pystray.Icon()调用完成，返回对象: {temp_icon}")
            print(f"[SystemTray] temp_icon类型: {type(temp_icon)}")
            print(f"[SystemTray] temp_icon is None: {temp_icon is None}")
            safe_flush()
            
            logging.info(f"[SystemTray] pystray.Icon()调用完成，返回对象: {temp_icon}")
            logging.info(f"[SystemTray] temp_icon类型: {type(temp_icon)}")
            logging.info(f"[SystemTray] temp_icon is None: {temp_icon is None}")
            
            # ！！！关键点：如果这里没有抛异常但 temp_icon 还是有问题
            if temp_icon is not None:
                self.icon = temp_icon
                logging.info(f"[SystemTray] ✅ pystray.Icon 实例赋值成功: {self.icon}")
                logging.info(f"[SystemTray] self.icon类型: {type(self.icon)}")
                logging.info(f"[SystemTray] self.icon is None: {self.icon is None}")
                print(f"[SystemTray] ✅ icon 对象已成功创建并赋值")
                safe_flush()
            else:
                # 最后的挣扎：如果默认创建失败，尝试手动指定一个简单属性
                logging.error("[SystemTray] ❌ pystray.Icon 返回 None，尝试使用最简单参数重新创建...")
                # 这里如果依然不行，说明 pystray 环境确实崩了
                # 尝试重新创建，使用最简单的参数
                try:
                    logging.info("[SystemTray] 尝试使用最简单的参数重新创建...")
                    simple_icon = pystray.Icon("Bazaar Lens", icon_image)
                    if simple_icon is not None:
                        logging.info("[SystemTray] ✅ 简单参数创建成功，使用简单版本")
                        self.icon = simple_icon
                    else:
                        logging.error("[SystemTray] ❌ 简单参数创建也返回 None，pystray 环境异常")
                        self.icon = None
                except Exception as e2:
                    logging.error(f"[SystemTray] ❌ 简单参数创建也失败: {e2}")
                    import traceback
                    logging.error(traceback.format_exc())
                    self.icon = None
                
        except Exception as e:
            logging.error(f"[SystemTray] ❌ 创建 pystray.Icon 发生严重异常: {e}")
            import traceback
            logging.error(traceback.format_exc())
            print(f"[SystemTray] ❌ 创建图标失败: {e}")
            safe_flush()
            self.icon = None
        
    def run(self):
        """启动托盘线程 - 这个方法会在独立线程中运行"""
        try:
            # 添加详细的状态检查
            logging.info(f"[SystemTray.run] ========== 托盘线程开始执行 ==========")
            logging.info(f"[SystemTray.run] 线程ID: {threading.current_thread().ident}")
            logging.info(f"[SystemTray.run] 线程名称: {threading.current_thread().name}")
            logging.info(f"[SystemTray.run] self.icon: {self.icon}")
            logging.info(f"[SystemTray.run] self.icon is None: {self.icon is None}")
            logging.info(f"[SystemTray.run] self.icon 类型: {type(self.icon)}")
            
            # 强制刷新输出
            import sys
            safe_flush()
            
            if self.icon:
                logging.info("[SystemTray.run] ✅ icon 对象存在，开始运行托盘主循环...")
                print("[SystemTray.run] ✅ icon 对象存在，开始运行托盘主循环...")
                safe_flush()
                # 关键：icon.run() 是阻塞调用，会一直运行直到 icon.stop() 被调用
                # 这必须在独立线程中运行，否则会阻塞主线程
                try:
                    self.icon.run()
                    logging.info("[SystemTray.run] ⚠️ 托盘主循环已退出（这通常不会发生，除非调用了 icon.stop()）")
                except Exception as e:
                    logging.error(f"[SystemTray.run] ❌ icon.run() 执行时发生错误: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    print(f"[SystemTray.run] ❌ icon.run() 执行时发生错误: {e}")
                    safe_flush()
            else:
                logging.error("[SystemTray.run] ❌ 无法运行：icon 对象为空")
                print("[SystemTray.run] ❌ 无法运行：icon 对象为空")
                safe_flush()
                logging.error("[SystemTray.run] 尝试重新创建图标...")
                # 尝试重新创建图标
                try:
                    self.create_tray_icon()
                    if self.icon:
                        logging.info("[SystemTray.run] ✅ 重新创建图标成功，开始运行...")
                        print("[SystemTray.run] ✅ 重新创建图标成功，开始运行...")
                        safe_flush()
                        try:
                            self.icon.run()
                        except Exception as e:
                            logging.error(f"[SystemTray.run] ❌ icon.run() 执行时发生错误: {e}")
                            import traceback
                            logging.error(traceback.format_exc())
                            print(f"[SystemTray.run] ❌ icon.run() 执行时发生错误: {e}")
                            safe_flush()
                    else:
                        logging.error("[SystemTray.run] ❌ 重新创建图标仍然失败")
                        print("[SystemTray.run] ❌ 重新创建图标仍然失败")
                        safe_flush()
                except Exception as e:
                    logging.error(f"[SystemTray.run] ❌ 重新创建图标时发生错误: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    print(f"[SystemTray.run] ❌ 重新创建图标时发生错误: {e}")
                    safe_flush()
        except Exception as e:
            logging.error(f"[SystemTray.run] ❌ 运行托盘时发生严重错误: {e}")
            import traceback
            logging.error(traceback.format_exc())
            print(f"[SystemTray.run] ❌ 运行托盘时发生严重错误: {e}")
            import sys
            safe_flush()
    
    def stop(self):
        """停止托盘"""
        if self.icon:
            self.icon.stop()
    
    def _show_help(self, icon, item):
        """显示说明窗口 - 必须在主线程中调用"""
        try:
            # 读取Help.txt文件内容
            current_file = os.path.abspath(__file__)  # system/tray.py
            system_dir = os.path.dirname(current_file)  # system目录
            main_script_dir = os.path.dirname(system_dir)  # main_script目录
            project_root = os.path.dirname(main_script_dir)  # 项目根目录
            help_path = os.path.join(project_root, "Help.txt")
            
            # 直接读取 Help.txt 内容，不添加额外标题（因为文件第一行已经是标题）
            if os.path.exists(help_path):
                try:
                    with open(help_path, 'r', encoding='utf-8') as f:
                        help_text = f.read()
                except Exception as e:
                    logging.error(f"读取Help.txt失败: {e}")
                    help_text = "无法读取说明文件"
            else:
                help_text = f"说明文件不存在: {help_path}"
            
            # 关键修复：使用主线程的 tkinter 窗口来创建新窗口
            # 通过 controller 访问 gui_manager 的主窗口
            if self.controller and hasattr(self.controller, 'gui_manager'):
                main_window = self.controller.gui_manager.info_window
                if main_window:
                    # 在主线程中调度窗口创建
                    main_window.after(0, lambda: self._create_help_window(main_window, help_text))
                else:
                    # 如果主窗口不存在，尝试直接创建（不推荐，但作为后备）
                    logging.warning("主窗口不存在，尝试在后台线程创建（可能导致错误）")
                    self._create_help_window_direct(help_text)
            else:
                # 后备方案：直接创建（可能失败）
                logging.warning("无法访问主窗口，尝试直接创建（可能导致错误）")
                self._create_help_window_direct(help_text)
            
        except Exception as e:
            logging.error(f"显示说明窗口失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def _open_log(self, icon, item):
        """打开日志文件（若存在），优先使用 logger.get_log_file_path()"""
        try:
            # 动态导入以避免初始化顺序问题
            try:
                from logger import get_log_file_path
            except Exception:
                try:
                    from main_script.logger import get_log_file_path
                except Exception:
                    get_log_file_path = None

            if get_log_file_path:
                log_path = get_log_file_path()
            else:
                # 回退到常见位置
                log_path = os.path.join(os.path.expanduser('~'), 'Documents', 'Bazaar_Lens', 'bazaar_helper.log')

            logging.info(f"[SystemTray] 打开日志文件: {log_path}")

            if os.path.exists(log_path):
                # 在 Windows 上使用 os.startfile 打开，以使用用户默认的查看器
                try:
                    if sys.platform.startswith('win'):
                        os.startfile(log_path)
                    else:
                        webbrowser.open('file://' + os.path.abspath(log_path))
                except Exception as e:
                    logging.error(f"[SystemTray] 打开日志失败: {e}")
                    # 尝试在主线程弹窗提示
                    try:
                        if self.controller and hasattr(self.controller, 'gui_manager') and self.controller.gui_manager.info_window:
                            self.controller.gui_manager.info_window.after(0, lambda: messagebox.showerror("错误", f"无法打开日志文件: {e}"))
                        else:
                            messagebox.showerror("错误", f"无法打开日志文件: {e}")
                    except Exception:
                        pass
            else:
                msg = f"日志文件不存在: {log_path}"
                logging.warning(f"[SystemTray] {msg}")
                try:
                    if self.controller and hasattr(self.controller, 'gui_manager') and self.controller.gui_manager.info_window:
                        self.controller.gui_manager.info_window.after(0, lambda: messagebox.showinfo("日志", msg))
                    else:
                        messagebox.showinfo("日志", msg)
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"[SystemTray] _open_log 异常: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def _create_help_window(self, parent_window, help_text):
        """在主线程中创建说明窗口"""
        try:
            # 创建文本窗口（使用主窗口作为父窗口）
            text_window = tk.Toplevel(parent_window)
            text_window.title("Bazaar Lens 使用说明")
            # 窗口稍大一些，适合长文阅读
            text_window.geometry("700x500")
            text_window.resizable(True, True)
            text_window.configure(bg="#1C1810")
            
            # 创建文本框和滚动条
            text_frame = tk.Frame(text_window, bg="#1C1810")
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 深色背景 + 较柔和的浅色文字，字体再大一些
            text_widget = tk.Text(
                text_frame,
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
                font=("Microsoft YaHei", 14),
                padx=12,
                pady=12,
                bg="#1C1810",
                fg="#F5F5F5",
                insertbackground="#F5F5F5",
                borderwidth=0,
                relief=tk.FLAT,
            )
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # 插入文本
            text_widget.insert('1.0', help_text)
            text_widget.config(state=tk.DISABLED)  # 只读
            
            # 添加关闭按钮
            button_frame = tk.Frame(text_window, bg="#1C1810")
            button_frame.pack(pady=10)
            close_button = tk.Button(
                button_frame,
                text="关闭",
                command=text_window.destroy,
                font=("Microsoft YaHei", 13),
                bg="#3A3122",
                fg="#F5F5F5",
                activebackground="#5A4A32",
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                padx=12,
                pady=4,
            )
            close_button.pack()
            
            # 居中显示窗口
            text_window.update_idletasks()
            width = text_window.winfo_width()
            height = text_window.winfo_height()
            x = (text_window.winfo_screenwidth() // 2) - (width // 2)
            y = (text_window.winfo_screenheight() // 2) - (height // 2)
            text_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # 设置窗口置顶
            text_window.attributes('-topmost', True)
            text_window.focus_force()
            
        except Exception as e:
            logging.error(f"创建说明窗口失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def _create_help_window_direct(self, help_text):
        """直接创建说明窗口（后备方案，可能失败）"""
        try:
            # 创建说明窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.title("Bazaar Lens 使用说明")
            
            # 创建文本窗口
            text_window = tk.Toplevel(root)
            text_window.title("Bazaar Lens 使用说明")
            text_window.geometry("700x500")
            text_window.resizable(True, True)
            text_window.configure(bg="#1C1810")
            
            # 创建文本框和滚动条
            text_frame = tk.Frame(text_window, bg="#1C1810")
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget = tk.Text(
                text_frame,
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
                font=("Microsoft YaHei", 14),
                padx=12,
                pady=12,
                bg="#1C1810",
                fg="#F5F5F5",
                insertbackground="#F5F5F5",
                borderwidth=0,
                relief=tk.FLAT,
            )
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # 插入文本
            text_widget.insert('1.0', help_text)
            text_widget.config(state=tk.DISABLED)  # 只读
            
            # 添加关闭按钮
            button_frame = tk.Frame(text_window, bg="#1C1810")
            button_frame.pack(pady=10)
            close_button = tk.Button(
                button_frame,
                text="关闭",
                command=text_window.destroy,
                font=("Microsoft YaHei", 13),
                bg="#3A3122",
                fg="#F5F5F5",
                activebackground="#5A4A32",
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                padx=12,
                pady=4,
            )
            close_button.pack()
            
            # 居中显示窗口
            text_window.update_idletasks()
            width = text_window.winfo_width()
            height = text_window.winfo_height()
            x = (text_window.winfo_screenwidth() // 2) - (width // 2)
            y = (text_window.winfo_screenheight() // 2) - (height // 2)
            text_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # 设置窗口置顶
            text_window.attributes('-topmost', True)
            text_window.focus_force()
            
        except Exception as e:
            logging.error(f"直接创建说明窗口失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def _open_contact(self, icon, item):
        """打开联系我链接"""
        try:
            url = "https://space.bilibili.com/35110142?spm_id_from=333.788.0.0"
            webbrowser.open(url)
            logging.info(f"已打开联系我链接: {url}")
        except Exception as e:
            logging.error(f"打开联系我链接失败: {e}")
            messagebox.showerror("错误", f"无法打开链接: {e}")
    
    def _open_sponsor(self, icon, item):
        """打开赞助链接"""
        try:
            url = "https://afdian.com/a/poe2lens"
            webbrowser.open(url)
            logging.info(f"已打开赞助链接: {url}")
        except Exception as e:
            logging.error(f"打开赞助链接失败: {e}")
            messagebox.showerror("错误", f"无法打开链接: {e}")
    
    def _quit_application(self, icon, item):
        """退出应用程序"""
        try:
            logging.info("收到退出请求，正在关闭程序...")
            if self.controller:
                self.controller.stop()
            if self.icon:
                self.icon.stop()
            sys.exit(0)
        except Exception as e:
            logging.error(f"退出应用程序失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
            sys.exit(1)
