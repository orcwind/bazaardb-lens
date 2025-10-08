"""
测试事件页面结构 - 查看选择和描述的关系
"""

import re
import time
from selenium import webdriver

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def test_event_structure():
    driver = setup_driver()
    
    try:
        # 测试：A Strange Mushroom
        url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/A-Strange-Mushroom"
        print(f"访问: {url}\n")
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        
        # 查找h3标题（选择名称）
        print("=== 选择名称（h3标题）===")
        h3_matches = re.findall(r'<h3[^>]*>.*?<span>([^<]+)</span>', html, re.DOTALL)
        choices = [t.strip() for t in h3_matches if t.strip() not in ['Hide filters', 'Close filters', 'Reset filters']]
        
        for i, choice in enumerate(choices, 1):
            print(f"{i}. {choice}")
        
        # 查找所有描述块（_bM class）
        print("\n=== 描述块（_bM class）===")
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        print(f"找到 {len(desc_matches)} 个描述块\n")
        
        for i, desc_html in enumerate(desc_matches[:10], 1):
            # 清理HTML
            desc = re.sub(r'<[^>]+>', '', desc_html)
            desc = desc.replace('&nbsp;', ' ').replace('&#x27;', "'").strip()
            print(f"{i}. {desc[:100]}...")
        
        # 查找图标
        print("\n=== 图标URL ===")
        icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/item/[a-f0-9]+@256\.webp[^"]*', html)
        print(f"找到 {len(icon_matches)} 个图标\n")
        
        for i, icon in enumerate(icon_matches[:10], 1):
            print(f"{i}. {icon}")
        
        # 尝试找到选择和描述的对应关系
        print("\n=== 分析HTML结构 ===")
        # 查找包含h3和描述的完整块
        choice_blocks = re.findall(r'<h3[^>]*>.*?<span>([^<]+)</span>.*?<div class="_bM">(.*?)</div>', html, re.DOTALL)
        
        print(f"找到 {len(choice_blocks)} 个选择-描述配对\n")
        for i, (choice_name, desc_html) in enumerate(choice_blocks[:5], 1):
            desc = re.sub(r'<[^>]+>', '', desc_html).replace('&nbsp;', ' ').strip()
            print(f"{i}. [{choice_name}]")
            print(f"   描述: {desc[:80]}...\n")
        
    finally:
        driver.quit()
        print("浏览器已关闭")

if __name__ == "__main__":
    test_event_structure()
