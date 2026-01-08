"""
爬虫GUI界面
提供图形界面来运行各种爬虫脚本
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import sys
from pathlib import Path

class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bazaar数据爬虫工具")
        self.root.geometry("800x600")
        
        # 当前运行的进程
        self.current_process = None
        self.is_running = False
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Bazaar数据爬虫工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 爬虫选择
        ttk.Label(main_frame, text="选择爬虫:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.crawler_var = tk.StringVar(value="items_skills")
        crawler_frame = ttk.Frame(main_frame)
        crawler_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        crawlers = [
            ("物品和技能", "items_skills"),
            ("怪物数据", "monsters"),
            ("事件数据", "events"),
        ]
        
        for i, (text, value) in enumerate(crawlers):
            ttk.Radiobutton(
                crawler_frame,
                text=text,
                variable=self.crawler_var,
                value=value
            ).grid(row=0, column=i, padx=10, sticky=tk.W)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.start_button = ttk.Button(
            button_frame,
            text="开始爬取",
            command=self.start_crawler
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="停止",
            command=self.stop_crawler,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="移动图标",
            command=self.move_icons
        ).pack(side=tk.LEFT, padx=5)
        
        # 输出区域
        ttk.Label(main_frame, text="输出日志:").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        self.output_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=80,
            height=20
        )
        self.output_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 状态栏
        self.status_label = ttk.Label(main_frame, text="就绪", relief=tk.SUNKEN)
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def log(self, message):
        """添加日志消息"""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def start_crawler(self):
        """启动爬虫"""
        if self.is_running:
            messagebox.showwarning("警告", "爬虫正在运行中，请先停止")
            return
        
        crawler_type = self.crawler_var.get()
        script_map = {
            "items_skills": "selenium_items_skills.py",
            "monsters": "selenium_monster_v3.py",
            "events": "selenium_event_final.py",
        }
        
        script_name = script_map.get(crawler_type)
        if not script_name:
            messagebox.showerror("错误", "未知的爬虫类型")
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"运行中: {script_name}")
        
        # 清空输出
        self.output_text.delete(1.0, tk.END)
        self.log(f"开始运行: {script_name}")
        
        # 在新线程中运行
        thread = threading.Thread(target=self.run_crawler, args=(script_name,), daemon=True)
        thread.start()
        
    def run_crawler(self, script_name):
        """运行爬虫脚本"""
        try:
            script_path = Path(__file__).parent / script_name
            
            # 切换到脚本目录
            script_dir = Path(__file__).parent
            
            self.log(f"工作目录: {script_dir}")
            self.log("=" * 60)
            
            # 运行脚本
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.current_process = process
            
            # 实时读取输出
            for line in process.stdout:
                if not self.is_running:
                    break
                self.log(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log("\n" + "=" * 60)
                self.log("爬取完成！")
                self.status_label.config(text="完成")
            else:
                self.log("\n" + "=" * 60)
                self.log(f"爬取失败，退出码: {process.returncode}")
                self.status_label.config(text="失败")
                
        except Exception as e:
            self.log(f"\n错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.status_label.config(text="错误")
        finally:
            self.is_running = False
            self.current_process = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
    def stop_crawler(self):
        """停止爬虫"""
        if self.current_process:
            self.log("\n正在停止爬虫...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None
        
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="已停止")
        self.log("爬虫已停止")
        
    def move_icons(self):
        """运行移动图标脚本"""
        if self.is_running:
            messagebox.showwarning("警告", "请先停止正在运行的爬虫")
            return
        
        result = messagebox.askyesno("确认", "是否要移动所有图标到统一目录？\n这将更新所有JSON文件。")
        if not result:
            return
        
        try:
            script_path = Path(__file__).parent / "move_all_icons.py"
            script_dir = Path(__file__).parent
            
            self.log("=" * 60)
            self.log("开始移动图标...")
            
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in process.stdout:
                self.log(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log("\n图标移动完成！")
                messagebox.showinfo("成功", "图标移动完成！")
            else:
                self.log(f"\n图标移动失败，退出码: {process.returncode}")
                messagebox.showerror("错误", "图标移动失败")
                
        except Exception as e:
            self.log(f"\n错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("错误", f"运行失败: {e}")

def main():
    root = tk.Tk()
    app = CrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


