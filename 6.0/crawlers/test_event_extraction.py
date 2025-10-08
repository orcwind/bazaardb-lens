"""
测试事件信息提取
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

def test_event_extraction():
    driver = setup_driver()
    
    try:
        # 测试第一个事件：A Strange Mushroom
        url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/A-Strange-Mushroom"
        print(f"访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        
        # 查看meta描述
        print("\n=== Meta描述 ===")
        meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
        if meta_match:
            print(f"内容: {meta_match.group(1)}")
        else:
            print("未找到meta描述")
        
        # 查找所有包含"choice"的文本
        print("\n=== 搜索'choice'关键词 ===")
        choice_matches = re.findall(r'.{0,50}[Cc]hoice.{0,50}', html, re.IGNORECASE)
        print(f"找到 {len(choice_matches)} 个匹配")
        for i, match in enumerate(choice_matches[:5], 1):
            print(f"  {i}. {match}")
        
        # 查找卡片链接
        print("\n=== 查找卡片链接 ===")
        card_links = re.findall(r'href="(/card/[^"]+)"', html)
        print(f"找到 {len(card_links)} 个卡片链接")
        for i, link in enumerate(card_links[:10], 1):
            print(f"  {i}. {link}")
        
        # 查找所有h3标题
        print("\n=== 查找标题 ===")
        h3_titles = re.findall(r'<h3[^>]*>.*?<span>([^<]+)</span>', html, re.DOTALL)
        print(f"找到 {len(h3_titles)} 个h3标题")
        for i, title in enumerate(h3_titles[:10], 1):
            print(f"  {i}. {title}")
        
        # 查找图标
        print("\n=== 查找图标 ===")
        icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/item/[a-f0-9]+@256\.webp[^"]*', html)
        print(f"找到 {len(icon_matches)} 个图标")
        for i, icon in enumerate(icon_matches[:5], 1):
            print(f"  {i}. {icon[:80]}...")
        
    finally:
        driver.quit()
        print("\n浏览器已关闭")

if __name__ == "__main__":
    test_event_extraction()
