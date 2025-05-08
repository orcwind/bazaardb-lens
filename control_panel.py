import tkinter as tk
from tkinter import ttk
import sys
import os
import subprocess
from PIL import Image, ImageTk
import win32gui
import win32con
import win32api
import threading
import ctypes

WM_NOTIFY_ICON = win32con.WM_USER + 20
WM_TASKBAR_CREATED = win32gui.RegisterWindowMessage("TaskbarCreated")

class ControlPanel:
    def __init__(self):
        self.hwnd = None
        self.icon = None
        self.tray_created = False
        
        # 创建隐藏的消息窗口
        try:
            # 确保清理所有已存在的托盘图标和窗口
            self._cleanup_existing_tray()
            
            wc = win32gui.WNDCLASS()
            hinst = wc.hInstance = win32gui.GetModuleHandle(None)
            wc.lpszClassName = "BazaarHelperTray"
            wc.lpfnWndProc = self._window_proc
            wc.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wc.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)
            
            try:
                classAtom = win32gui.RegisterClass(wc)
            except Exception:
                # 如果注册失败，先注销再重试
                try:
                    win32gui.UnregisterClass("BazaarHelperTray", hinst)
                    classAtom = win32gui.RegisterClass(wc)
                except Exception as e:
                    raise Exception(f"注册窗口类失败: {e}")
            
            style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
            self.hwnd = win32gui.CreateWindow(
                classAtom,
                "BazaarHelper",
                style,
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                0, 0,
                hinst,
                None
            )
            
            if not self.hwnd:
                raise Exception("创建窗口失败")
                
            win32gui.UpdateWindow(self.hwnd)
            
        except Exception as e:
            print(f"创建窗口失败: {e}")
            self._cleanup()
            return
        
        # 创建托盘图标
        self._create_tray()
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.withdraw()  # 初始隐藏窗口
        self.root.title("The Bazaar Helper")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # 设置窗口样式（无任务栏图标）
        self.root.attributes('-toolwindow', 1)
        
        # 读取说明文件
        self.instructions = self._load_instructions()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建界面元素
        self._create_widgets()
        
        # 绑定事件
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_window())
    
    def _cleanup_existing_tray(self):
        """清理已存在的托盘图标和窗口"""
        try:
            # 尝试查找已存在的窗口
            hwnd = win32gui.FindWindow("BazaarHelperTray", None)
            if hwnd:
                # 移除托盘图标
                try:
                    nid = (hwnd, 0)
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                except:
                    pass
                # 销毁窗口
                try:
                    win32gui.DestroyWindow(hwnd)
                except:
                    pass
            
            # 注销窗口类
            try:
                win32gui.UnregisterClass("BazaarHelperTray", win32gui.GetModuleHandle(None))
            except:
                pass
        except:
            pass
    
    def _create_tray(self):
        """创建托盘图标"""
        if not self.hwnd:
            return
            
        try:
            # 加载图标
            icon_path = "Bazaar_Lens.ico"
            if not os.path.exists(icon_path):
                icon_path = os.path.join("icons", "app_icon.ico")
            
            if os.path.exists(icon_path):
                self.icon = win32gui.LoadImage(
                    0, icon_path, win32con.IMAGE_ICON,
                    0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                )
            else:
                self.icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            
            # 添加托盘图标
            flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
            nid = (self.hwnd, 0, flags, WM_NOTIFY_ICON, self.icon, "The Bazaar Helper")
            
            # 先尝试删除旧图标
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            except:
                pass
                
            # 添加新图标
            if not win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid):
                raise Exception("添加托盘图标失败")
            
            self.tray_created = True
            
        except Exception as e:
            print(f"创建托盘图标失败: {e}")
            if self.icon:
                win32gui.DestroyIcon(self.icon)
                self.icon = None
    
    def _cleanup(self):
        """清理所有资源"""
        try:
            if self.hwnd:
                # 移除托盘图标
                if self.tray_created:
                    try:
                        nid = (self.hwnd, 0)
                        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                    except:
                        pass
                    self.tray_created = False
                    
                # 销毁图标
                if self.icon:
                    try:
                        win32gui.DestroyIcon(self.icon)
                    except:
                        pass
                    self.icon = None
                
                # 销毁窗口
                try:
                    win32gui.DestroyWindow(self.hwnd)
                except:
                    pass
                self.hwnd = None
            
            # 注销窗口类
            try:
                win32gui.UnregisterClass("BazaarHelperTray", win32gui.GetModuleHandle(None))
            except:
                pass
        except Exception as e:
            print(f"清理资源失败: {e}")
    
    def _window_proc(self, hwnd, msg, wparam, lparam):
        """处理窗口消息"""
        try:
            if msg == WM_NOTIFY_ICON:
                if lparam == win32con.WM_LBUTTONUP:
                    win32gui.PostMessage(hwnd, win32con.WM_COMMAND, 1, 0)
                    return 0
                elif lparam == win32con.WM_RBUTTONUP:
                    self._show_menu()
                    return 0
            elif msg == WM_TASKBAR_CREATED:
                self._create_tray()  # 重新创建托盘图标
                return 0
            elif msg == win32con.WM_COMMAND:
                if wparam == 1:  # 左键点击
                    self.show_window()
                    return 0
            elif msg == win32con.WM_DESTROY:
                self.quit_program()
                return 0
        except:
            pass
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    
    def _show_menu(self):
        """显示托盘菜单"""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "显示面板")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "重启插件")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 3, "退出程序")
        
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_RETURNCMD | win32con.TPM_NONOTIFY,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None
        )
        
        if cmd == 1:
            self.show_window()
        elif cmd == 2:
            self.restart_program()
        elif cmd == 3:
            self.quit_program()
    
    def _load_instructions(self):
        """加载说明文件"""
        try:
            with open('Info.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"加载说明文件失败: {e}")
            return "在怪物或事件上按住alt键，即可显示相关信息。"
    
    def _create_widgets(self):
        """创建界面元素"""
        # 标题
        title_label = ttk.Label(
            self.main_frame,
            text="The Bazaar Helper",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # 说明文本
        text_frame = ttk.LabelFrame(self.main_frame, text="使用说明", padding="10")
        text_frame.pack(fill=tk.X, pady=(0, 10))
        
        instructions_label = ttk.Label(
            text_frame,
            text=self.instructions,
            justify=tk.LEFT,
            wraplength=350
        )
        instructions_label.pack()
        
        # 联系方式
        contact_frame = ttk.LabelFrame(self.main_frame, text="联系方式", padding="10")
        contact_frame.pack(fill=tk.X, pady=(0, 10))
        
        # QQ图标和文本
        qq_frame = ttk.Frame(contact_frame)
        qq_frame.pack(fill=tk.X, pady=2)
        if os.path.exists("icons/qq.png"):
            qq_img = Image.open("icons/qq.png").resize((20, 20))
            qq_photo = ImageTk.PhotoImage(qq_img)
            qq_icon = ttk.Label(qq_frame, image=qq_photo)
            qq_icon.image = qq_photo
            qq_icon.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(qq_frame, text="QQ群: 123456789").pack(side=tk.LEFT)
        
        # Discord图标和文本
        discord_frame = ttk.Frame(contact_frame)
        discord_frame.pack(fill=tk.X, pady=2)
        if os.path.exists("icons/discord.png"):
            discord_img = Image.open("icons/discord.png").resize((20, 20))
            discord_photo = ImageTk.PhotoImage(discord_img)
            discord_icon = ttk.Label(discord_frame, image=discord_photo)
            discord_icon.image = discord_photo
            discord_icon.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(discord_frame, text="Discord: your_discord").pack(side=tk.LEFT)
        
        # 状态框架
        status_frame = ttk.LabelFrame(self.main_frame, text="程序状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            text="程序运行中...",
            foreground="green"
        )
        self.status_label.pack()
        
        # 按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 重启按钮
        self.restart_button = ttk.Button(
            button_frame,
            text="重启插件",
            command=self.restart_program
        )
        self.restart_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮
        quit_button = ttk.Button(
            button_frame,
            text="退出程序",
            command=self.quit_program
        )
        quit_button.pack(side=tk.RIGHT, padx=5)
    
    def show_window(self):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """隐藏主窗口"""
        self.root.withdraw()
    
    def restart_program(self):
        """重启程序"""
        try:
            self.status_label.config(text="正在重启程序...", foreground="orange")
            self.restart_button.state(["disabled"])
            self.root.update()
            
            script_path = os.path.join(os.path.dirname(__file__), "bazaar_helper.py")
            subprocess.Popen([sys.executable, script_path])
            
            self.status_label.config(text="程序已重启", foreground="green")
            self.restart_button.state(["!disabled"])
            
        except Exception as e:
            self.status_label.config(text=f"重启失败: {e}", foreground="red")
            self.restart_button.state(["!disabled"])
    
    def quit_program(self):
        """退出程序"""
        try:
            # 清理所有资源
            self._cleanup()
            
            # 结束所有Python进程（除了当前控制面板）
            current_pid = os.getpid()
            for proc in os.popen('tasklist').readlines():
                if "python.exe" in proc.lower():
                    try:
                        pid = int(proc.split()[1])
                        if pid != current_pid:
                            os.system(f'taskkill /PID {pid} /F')
                    except:
                        pass
            
        except Exception as e:
            print(f"退出时出错: {e}")
        finally:
            if hasattr(self, 'root') and self.root:
                self.root.quit()
            os._exit(0)
    
    def run(self):
        """运行程序"""
        # 启动主程序
        script_path = os.path.join(os.path.dirname(__file__), "bazaar_helper.py")
        subprocess.Popen([sys.executable, script_path])
        
        # 启动消息循环
        def message_loop():
            while True:
                try:
                    win32gui.PumpMessages()
                except Exception:
                    break
        
        # 在新线程中运行消息循环
        threading.Thread(target=message_loop, daemon=True).start()
        
        # 运行主窗口
        self.root.mainloop()

def hide_console():
    """隐藏控制台窗口"""
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except:
        pass

if __name__ == "__main__":
    # 隐藏控制台窗口
    hide_console()
    
    panel = ControlPanel()
    panel.run() 