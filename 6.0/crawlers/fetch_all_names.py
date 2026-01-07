"""
统一脚本：获取所有物品、技能、怪物、事件的名称清单
使用Selenium直接从网站提取
"""

import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """设置Chrome驱动，强制使用英文语言"""
    options = webdriver.ChromeOptions()
    # 暂时不使用无头模式，避免连接问题
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 强制设置语言为英文
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    options.add_argument('--accept-lang=en-US,en')
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(options=options)

def extract_names_from_pagecards(html, item_type='Item'):
    """
    从页面HTML中提取所有名称（从pageCards JSON中）
    
    Args:
        html: 页面HTML内容
        item_type: 'Item', 'Skill', 'CombatEncounter', 'EventEncounter'
    
    Returns:
        名称列表（英文名称）
    """
    names = []
    search_pos = 0
    
    while True:
        # 查找 initialData
        init_pos = html.find('initialData', search_pos)
        if init_pos == -1:
            break
        
        # 在 initialData 区域内查找 pageCards
        search_area_start = init_pos
        search_area_end = min(len(html), init_pos + 200000)
        search_area = html[search_area_start:search_area_end]
        
        pagecards_key = 'pageCards'
        key_pos_in_area = search_area.find(pagecards_key)
        
        if key_pos_in_area != -1:
            # 找到 pageCards，提取数组
            key_pos = search_area_start + key_pos_in_area
            bracket_start = html.find('[', key_pos)
            
            if bracket_start != -1:
                # 手动匹配完整的JSON数组
                depth = 0
                in_string = False
                escape = False
                bracket_end = -1
                
                for i in range(bracket_start, len(html)):
                    ch = html[i]
                    
                    if escape:
                        escape = False
                        continue
                    
                    if ch == '\\':
                        escape = True
                        continue
                    
                    if ch == '"':
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if ch == '[':
                            depth += 1
                        elif ch == ']':
                            depth -= 1
                            if depth == 0:
                                bracket_end = i
                                break
                
                if bracket_end != -1:
                    # 提取并解析JSON数组
                    json_str = html[bracket_start:bracket_end + 1]
                    try:
                        # 尝试直接解析
                        cards_data = json.loads(json_str)
                    except:
                        # 如果失败，尝试解码转义
                        try:
                            import ast
                            decoded_str = ast.literal_eval(f'"{json_str}"')
                            cards_data = json.loads(decoded_str)
                        except:
                            cards_data = None
                    
                    if cards_data and isinstance(cards_data, list):
                        # 提取符合类型的卡片名称
                        for card in cards_data:
                            if isinstance(card, dict):
                                card_type = card.get('Type', '')
                                if card_type == item_type:
                                    # 优先使用 _originalTitleText（英文名）
                                    name = card.get('_originalTitleText', '')
                                    if not name:
                                        # 如果没有，尝试从 Title.Text 提取（可能是中文）
                                        title = card.get('Title', {})
                                        if isinstance(title, dict):
                                            name = title.get('Text', '')
                                    
                                    if name and name not in names:
                                        names.append(name)
        
        # 继续搜索下一个 initialData
        search_pos = init_pos + 1
    
    return names

def fetch_items_names(driver):
    """获取所有物品名称"""
    print("\n" + "=" * 80)
    print("获取物品名称...")
    print("=" * 80)
    
    url = "https://bazaardb.gg/search?c=items"
    print(f"访问: {url}")
    driver.get(url)
    time.sleep(5)
    
    # 滚动加载所有内容
    print("滚动页面加载所有物品...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < 50:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more')]")
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(3)
            except:
                break
        last_height = new_height
        scroll_count += 1
    
    time.sleep(3)
    
    html = driver.page_source
    names = extract_names_from_pagecards(html, 'Item')
    
    print(f"✓ 找到 {len(names)} 个物品")
    return sorted(names)

def fetch_skills_names(driver):
    """获取所有技能名称"""
    print("\n" + "=" * 80)
    print("获取技能名称...")
    print("=" * 80)
    
    url = "https://bazaardb.gg/search?c=skills"
    print(f"访问: {url}")
    driver.get(url)
    time.sleep(5)
    
    # 滚动加载所有内容
    print("滚动页面加载所有技能...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < 50:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more')]")
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(3)
            except:
                break
        last_height = new_height
        scroll_count += 1
    
    time.sleep(3)
    
    html = driver.page_source
    names = extract_names_from_pagecards(html, 'Skill')
    
    print(f"✓ 找到 {len(names)} 个技能")
    return sorted(names)

def fetch_monsters_names(driver):
    """获取所有怪物名称"""
    print("\n" + "=" * 80)
    print("获取怪物名称...")
    print("=" * 80)
    
    url = "https://bazaardb.gg/search?c=monsters"
    print(f"访问: {url}")
    driver.get(url)
    time.sleep(5)
    
    # 滚动加载所有内容
    print("滚动页面加载所有怪物...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < 50:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more')]")
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(3)
            except:
                break
        last_height = new_height
        scroll_count += 1
    
    time.sleep(3)
    
    html = driver.page_source
    names = extract_names_from_pagecards(html, 'CombatEncounter')
    
    print(f"✓ 找到 {len(names)} 个怪物")
    return sorted(names)

def fetch_events_names(driver):
    """获取所有事件名称"""
    print("\n" + "=" * 80)
    print("获取事件名称...")
    print("=" * 80)
    
    url = "https://bazaardb.gg/search?c=events"
    print(f"访问: {url}")
    driver.get(url)
    time.sleep(5)
    
    # 滚动加载所有内容
    print("滚动页面加载所有事件...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < 50:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more')]")
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(3)
            except:
                break
        last_height = new_height
        scroll_count += 1
    
    time.sleep(3)
    
    html = driver.page_source
    names = extract_names_from_pagecards(html, 'EventEncounter')
    
    print(f"✓ 找到 {len(names)} 个事件")
    return sorted(names)

def save_names_to_file(names, filename):
    """保存名称列表到文件（每行一个）"""
    with open(filename, 'w', encoding='utf-8') as f:
        for name in names:
            f.write(f'"{name}"\n')
    print(f"✓ 已保存到: {filename}")

def main():
    print("=" * 80)
    print("获取所有物品、技能、怪物、事件名称清单")
    print("=" * 80)
    
    driver = setup_driver()
    
    try:
        # 获取所有名称
        items = fetch_items_names(driver)
        skills = fetch_skills_names(driver)
        monsters = fetch_monsters_names(driver)
        events = fetch_events_names(driver)
        
        # 保存到文件
        print("\n" + "=" * 80)
        print("保存名称清单...")
        print("=" * 80)
        
        save_names_to_file(items, 'unique_items.json')
        save_names_to_file(skills, 'unique_skills.json')
        save_names_to_file(monsters, 'unique_monsters.json')
        save_names_to_file(events, 'unique_events.json')
        
        # 打印统计
        print("\n" + "=" * 80)
        print("统计信息:")
        print("=" * 80)
        print(f"物品: {len(items)} 个")
        print(f"技能: {len(skills)} 个")
        print(f"怪物: {len(monsters)} 个")
        print(f"事件: {len(events)} 个")
        print("=" * 80)
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")

if __name__ == "__main__":
    main()

