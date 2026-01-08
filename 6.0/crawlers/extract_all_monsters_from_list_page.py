"""从怪物总列表页面批量提取所有怪物数据"""
import sys
import json
import re
import time
from pathlib import Path
from html import unescape

sys.path.insert(0, str(Path(__file__).parent))
from selenium_items_skills import setup_driver
from selenium.webdriver.common.by import By

def extract_all_monsters_from_list_page(driver):
    """从怪物总列表页面提取所有怪物的完整JSON数据
    
    Returns:
        怪物数据列表（字典列表）
    """
    try:
        url = "https://bazaardb.gg/search?c=monsters"
        print(f"访问怪物总列表页面: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 滚动加载所有内容
        print("滚动页面加载所有怪物...")
        no_change_count = 0
        max_no_change = 3
        scroll_count = 0
        max_scrolls = 50
        
        while scroll_count < max_scrolls:
            # 尝试点击"Load more"按钮
            try:
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load more') or contains(text(), '加载更多')]")
                for btn in load_more_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        break
            except:
                pass
            
            # 滚动到底部
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    print(f"  连续 {max_no_change} 次无新内容，停止滚动")
                    break
            else:
                no_change_count = 0
            
            scroll_count += 1
            if scroll_count % 10 == 0:
                print(f"  已滚动 {scroll_count} 次...")
        
        print("  等待内容加载完成...")
        time.sleep(5)
        
        # 从页面HTML中提取所有怪物的完整JSON数据
        html = driver.page_source
        print(f"  HTML长度: {len(html)} 字符")
        
        # 提取所有包含 _originalTitleText 的 CombatEncounter 对象
        all_monsters = []
        
        # 方法1: 搜索所有 "Type":"CombatEncounter" 附近的 _originalTitleText
        # 使用宽泛的搜索范围（5000字符内）
        pattern = r'"Type"\s*:\s*"CombatEncounter"[^}]{0,5000}?"_originalTitleText"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        
        print(f"  找到 {len(matches)} 个可能的怪物匹配")
        
        # 对于每个匹配，提取完整的JSON对象
        processed_names = set()
        for match in matches:
            clean_name = unescape(match).strip()
            if clean_name in processed_names:
                continue
            
            # 找到这个 _originalTitleText 的位置
            title_pattern = rf'"Type"\s*:\s*"CombatEncounter"[^}}]{{0,5000}}?"_originalTitleText"\s*:\s*"{re.escape(match)}"'
            title_match = re.search(title_pattern, html, re.DOTALL)
            
            if title_match:
                match_start = title_match.start()
                # 向前查找对象的开始 {
                obj_start = html.rfind('{', max(0, match_start - 10000), match_start)
                if obj_start != -1:
                    # 向后查找对象的结束 }
                    depth = 0
                    in_string = False
                    escape = False
                    obj_end = -1
                    
                    for i in range(obj_start, min(len(html), obj_start + 50000)):
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
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    obj_end = i
                                    break
                    
                    if obj_end != -1:
                        json_str = html[obj_start:obj_end + 1]
                        try:
                            card_data = json.loads(json_str)
                            if card_data.get('Type') == 'CombatEncounter':
                                original_title = card_data.get('_originalTitleText', '')
                                if original_title and original_title not in processed_names:
                                    all_monsters.append(card_data)
                                    processed_names.add(original_title)
                        except:
                            pass
        
        print(f"  ✓ 成功提取 {len(all_monsters)} 个怪物的完整数据")
        return all_monsters
        
    except Exception as e:
        print(f"  ✗ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    driver = setup_driver()
    try:
        monsters = extract_all_monsters_from_list_page(driver)
        print(f"\n总共提取到 {len(monsters)} 个怪物")
        if monsters:
            print(f"前3个怪物名称:")
            for i, m in enumerate(monsters[:3], 1):
                print(f"  {i}. {m.get('_originalTitleText', 'N/A')}")
    finally:
        driver.quit()

