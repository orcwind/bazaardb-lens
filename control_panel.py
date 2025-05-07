import tkinter as tk
from tkinter import ttk
import sys
import os
import subprocess
from PIL import Image, ImageTk

class ControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("The Bazaar Helper 控制面板")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # 设置窗口图标
        if os.path.exists("icons/app_icon.webp"):
            icon = Image.open("icons/app_icon.webp")
            photo = ImageTk.PhotoImage(icon)
            self.root.iconphoto(True, photo)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame,
            text="The Bazaar Helper",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # 说明文本
        instructions = """
使用说明：
1. 在游戏中将鼠标悬停在怪物或事件上
2. 按住Alt键查看详细信息
3. 松开Alt键关闭信息窗口

如果程序无响应：
点击下方"重启程序"按钮

快捷键：
Alt - 显示/隐藏信息
Ctrl+Q - 退出程序
"""
        text_frame = ttk.LabelFrame(main_frame, text="使用说明", padding="10")
        text_frame.pack(fill=tk.X, pady=(0, 10))
        
        instructions_label = ttk.Label(
            text_frame,
            text=instructions,
            justify=tk.LEFT,
            wraplength=350
        )
        instructions_label.pack()
        
        # 联系方式
        contact_frame = ttk.LabelFrame(main_frame, text="联系方式", padding="10")
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
        status_frame = ttk.LabelFrame(main_frame, text="程序状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            text="程序运行中...",
            foreground="green"
        )
        self.status_label.pack()
        
        # 重启按钮
        self.restart_button = ttk.Button(
            main_frame,
            text="重启程序",
            command=self.restart_program,
            style="Accent.TButton"
        )
        self.restart_button.pack(pady=10)
        
        # 设置按钮样式
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11))
        
        # 绑定快捷键
        self.root.bind("<Control-q>", lambda e: self.quit_program())
        
        # 保持在顶层
        self.root.attributes("-topmost", True)
    
    def restart_program(self):
        """重启程序"""
        try:
            self.status_label.config(text="正在重启程序...", foreground="orange")
            self.restart_button.state(["disabled"])
            self.root.update()
            
            # 获取当前脚本路径
            script_path = os.path.join(os.path.dirname(__file__), "bazaar_helper.py")
            
            # 启动新进程
            subprocess.Popen([sys.executable, script_path])
            
            # 退出当前程序
            self.quit_program()
            
        except Exception as e:
            self.status_label.config(text=f"重启失败: {e}", foreground="red")
            self.restart_button.state(["!disabled"])
    
    def quit_program(self):
        """退出程序"""
        try:
            # 结束所有Python进程（除了当前控制面板）
            current_pid = os.getpid()
            for proc in os.popen('tasklist').readlines():
                if "python.exe" in proc.lower():
                    pid = int(proc.split()[1])
                    if pid != current_pid:
                        os.system(f'taskkill /PID {pid} /F')
        except Exception as e:
            print(f"退出时出错: {e}")
        finally:
            self.root.quit()
            os._exit(0)
    
    def run(self):
        """运行控制面板"""
        # 启动主程序
        script_path = os.path.join(os.path.dirname(__file__), "bazaar_helper.py")
        subprocess.Popen([sys.executable, script_path])
        
        # 运行控制面板
        self.root.mainloop()

if __name__ == "__main__":
    panel = ControlPanel()
    panel.run() 