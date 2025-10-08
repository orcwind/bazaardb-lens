"""
运行所有爬虫 - 顺序执行
"""

import subprocess
import sys

def run_crawler(script_name, description):
    """运行单个爬虫脚本"""
    print("\n" + "=" * 80)
    print(f"开始运行: {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False
        )
        print(f"\n✓ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} 失败: {e}")
        return False

def main():
    print("=" * 80)
    print("运行所有爬虫程序")
    print("=" * 80)
    
    crawlers = [
        ("selenium_monster_v3.py", "怪物爬虫"),
        ("selenium_event_v1.py", "事件爬虫")
    ]
    
    results = {}
    
    for script, desc in crawlers:
        success = run_crawler(script, desc)
        results[desc] = success
    
    print("\n" + "=" * 80)
    print("所有爬虫运行完成")
    print("=" * 80)
    
    print("\n结果汇总:")
    for desc, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {desc}: {status}")

if __name__ == "__main__":
    main()
