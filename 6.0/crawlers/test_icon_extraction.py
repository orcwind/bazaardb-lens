"""
测试从实时网页提取图标URL
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

def test_icon_extraction():
    driver = setup_driver()
    
    try:
        # 访问Banannibal详情页
        url = "https://bazaardb.gg/card/1q3zi7wtui5kfes7wxor9hgla/Banannibal"
        print(f"访问: {url}")
        driver.get(url)
        time.sleep(5)  # 等待页面加载
        
        html_content = driver.page_source
        
        # 尝试多种方式查找图标URL
        print("\n=== 方法1: 查找所有webp图片 ===")
        webp_matches = re.findall(r'https://[^"\s]+\.webp[^"\s]*', html_content)
        print(f"找到 {len(webp_matches)} 个webp链接")
        for i, url in enumerate(webp_matches[:10], 1):  # 只显示前10个
            print(f"  {i}. {url[:80]}...")
        
        print("\n=== 方法2: 查找skill相关的图标 ===")
        skill_pattern = r'skill/[a-f0-9]+@\d+\.webp'
        skill_icons = re.findall(skill_pattern, html_content)
        print(f"找到 {len(skill_icons)} 个技能图标")
        for icon in skill_icons:
            print(f"  - {icon}")
        
        print("\n=== 方法3: 查找item相关的图标 ===")
        item_pattern = r'item/[a-f0-9]+@\d+\.webp'
        item_icons = re.findall(item_pattern, html_content)
        print(f"找到 {len(item_icons)} 个物品图标")
        for icon in item_icons:
            print(f"  - {icon}")
        
        print("\n=== 方法4: 查找JSON结构 ===")
        # 查找包含"skills"的JSON
        skills_json = re.search(r'"skills":\[.*?\]', html_content, re.DOTALL)
        if skills_json:
            print(f"找到skills JSON (长度: {len(skills_json.group(0))} 字符)")
            print(f"前500字符: {skills_json.group(0)[:500]}")
        else:
            print("未找到skills JSON")
        
        # 查找包含"board"的JSON
        board_json = re.search(r'"board":\[.*?\]', html_content, re.DOTALL)
        if board_json:
            print(f"\n找到board JSON (长度: {len(board_json.group(0))} 字符)")
            print(f"前500字符: {board_json.group(0)[:500]}")
        else:
            print("\n未找到board JSON")
        
    finally:
        driver.quit()
        print("\n浏览器已关闭")

if __name__ == "__main__":
    test_icon_extraction()
