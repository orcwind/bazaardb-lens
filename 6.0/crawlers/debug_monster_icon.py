"""
调试脚本：查看monster card页面的HTML结构，找出icon URL
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# 配置路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MONSTERS_JSON = PROJECT_ROOT / "data" / "Json" / "monsters.json"

def setup_driver():
    """设置Selenium WebDriver"""
    chrome_options = webdriver.ChromeOptions()
    # 不启用headless，方便调试
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"✗ 创建WebDriver失败: {e}")
        return None

def debug_monster_page():
    """调试monster card页面"""
    # 加载第一个monster
    with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    if not monsters:
        print("没有找到monster数据")
        return
    
    monster = monsters[0]  # 第一个monster
    monster_name = monster.get('name', '')
    search_url = monster.get('url', '')
    
    print(f"调试monster: {monster_name}")
    print(f"搜索URL: {search_url}")
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        # 获取card URL
        driver.get(search_url)
        time.sleep(3)
        
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        card_url = card_link.get_attribute('href')
        print(f"\nCard URL: {card_url}")
        
        # 访问card页面
        driver.get(card_url)
        time.sleep(5)
        
        html_content = driver.page_source
        
        # 保存HTML用于调试
        debug_html = SCRIPT_DIR / "debug_monster_card.html"
        with open(debug_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nHTML已保存到: {debug_html}")
        
        # 查找所有img标签
        print("\n=== 所有img标签的src属性 ===")
        img_elements = driver.find_elements(By.TAG_NAME, 'img')
        for i, img in enumerate(img_elements[:20]):  # 只显示前20个
            src = img.get_attribute('src')
            if src:
                print(f"{i+1}. {src[:100]}")
        
        # 查找包含@256.webp的图片
        print("\n=== 包含@256.webp的图片 ===")
        for img in img_elements:
            src = img.get_attribute('src')
            if src and '@256.webp' in src:
                print(f"{src}")
        
        # 查找所有包含s.bazaardb.gg的图片
        print("\n=== 所有s.bazaardb.gg图片 ===")
        for img in img_elements:
            src = img.get_attribute('src')
            if src and 's.bazaardb.gg' in src:
                print(f"{src}")
        
        # 查找页面中最大的图片（通常是card图片）
        print("\n=== 尝试查找最大的图片（card图片） ===")
        images_with_size = []
        for img in img_elements:
            try:
                src = img.get_attribute('src')
                width = img.size.get('width', 0)
                height = img.size.get('height', 0)
                if src and width > 0 and height > 0:
                    images_with_size.append((src, width, height, width * height))
            except:
                pass
        
        # 按面积排序
        images_with_size.sort(key=lambda x: x[3], reverse=True)
        for src, w, h, area in images_with_size[:5]:
            print(f"尺寸: {w}x{h} (面积: {area}) - {src[:100]}")
        
        print("\n调试完成！")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_monster_page()

