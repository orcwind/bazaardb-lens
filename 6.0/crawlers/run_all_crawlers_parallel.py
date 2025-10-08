"""
并行运行所有爬虫 - 使用多进程
"""

import subprocess
import sys
from multiprocessing import Process
import time

def run_crawler(script_name, description):
    """运行单个爬虫脚本"""
    print(f"\n[{description}] 开始运行...")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"\n[{description}] ✓ 完成")
        print(f"\n[{description}] 输出:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[{description}] ✗ 失败: {e}")
        if e.stdout:
            print(f"\n[{description}] 输出:")
            print(e.stdout)
        if e.stderr:
            print(f"\n[{description}] 错误:")
            print(e.stderr)
        return False

def main():
    print("=" * 80)
    print("并行运行所有爬虫程序")
    print("=" * 80)
    print("\n⚠️  注意：两个浏览器将同时运行，请确保系统资源充足")
    print("⚠️  如果遇到性能问题，建议使用 run_all_crawlers.py 顺序执行\n")
    
    crawlers = [
        ("selenium_monster_v3.py", "怪物爬虫"),
        ("selenium_event_v1.py", "事件爬虫")
    ]
    
    # 创建进程
    processes = []
    for script, desc in crawlers:
        p = Process(target=run_crawler, args=(script, desc))
        processes.append((p, desc))
        p.start()
        print(f"✓ {desc} 已启动 (PID: {p.pid})")
    
    print("\n等待所有爬虫完成...")
    
    # 等待所有进程完成
    for p, desc in processes:
        p.join()
        print(f"✓ {desc} 已完成")
    
    print("\n" + "=" * 80)
    print("所有爬虫运行完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
