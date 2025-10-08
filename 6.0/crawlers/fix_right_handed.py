"""
修复 Right-Handed 技能的图标
手动访问页面获取图标URL
"""

import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver

OUTPUT_DIR = Path('monster_details_v3')
ICONS_DIR = OUTPUT_DIR / 'icons'

def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def download_icon(icon_url, monster_name, card_name):
    """下载图标"""
    try:
        safe_monster_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
        safe_card_name = re.sub(r'[<>:"/\\|?*]', '_', card_name)
        
        filename = f"{safe_monster_name}_{safe_card_name}.webp"
        filepath = ICONS_DIR / filename
        
        if filepath.exists():
            print(f"  图标已存在: {filename}")
            return f"icons/{filename}"
        
        response = requests.get(icon_url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"  ✓ 下载成功: {filename}")
        return f"icons/{filename}"
    
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return ""

def fix_right_handed_skill():
    """修复 Right-Handed 技能"""
    print("=" * 80)
    print("修复 Right-Handed 技能的图标")
    print("=" * 80)
    
    # 读取现有数据
    json_file = OUTPUT_DIR / 'monsters_v3.json'
    with open(json_file, 'r', encoding='utf-8') as f:
        monsters_data = json.load(f)
    
    # Right-Handed 技能的URL
    skill_url = "https://bazaardb.gg/card/1gsw3h6do8eog70mopd8pxy3v/Right-Handed"
    
    driver = setup_driver()
    
    try:
        print(f"\n访问技能页面: {skill_url}")
        driver.get(skill_url)
        time.sleep(5)
        
        html_content = driver.page_source
        
        # 提取图标URL
        # 查找skill图标
        skill_icon_match = re.search(r'https://s\.bazaardb\.gg/v0/[^/]+/skill/([a-f0-9]+)@256\.webp', html_content)
        
        if skill_icon_match:
            skill_hash = skill_icon_match.group(1)
            icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/skill/{skill_hash}@256.webp?v=0"
            print(f"  ✓ 找到图标URL: {icon_url}")
        else:
            print(f"  ✗ 未找到图标URL")
            print(f"  尝试使用默认skill URL模式...")
            # 从页面中查找任何skill相关的图标
            all_skill_icons = re.findall(r'https://s\.bazaardb\.gg/v0/z5\.0\.0/skill/[a-f0-9]+@256\.webp\?v=\d+', html_content)
            if all_skill_icons:
                icon_url = all_skill_icons[0]
                print(f"  ✓ 使用找到的URL: {icon_url}")
            else:
                print(f"  ✗ 完全未找到图标")
                return
        
        # 提取描述
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html_content, re.DOTALL)
        description = ""
        
        if desc_matches:
            for description_html in desc_matches:
                desc = re.sub(r'<[^>]+>', '', description_html)
                desc = desc.replace('&nbsp;', ' ').replace('&amp;', '&')
                desc = desc.strip()
                
                if (len(desc) > 10 and 
                    'Offered by' not in desc and 
                    'Dropped by' not in desc):
                    description = desc
                    break
        
        if not description:
            # 从网页内容提取
            description = "Your rightmost Weapon has +20 » +30 » +40 » +50 Damage."
        
        print(f"  ✓ 描述: {description}")
        
        # 需要更新的怪物列表
        monsters_to_update = ['Ferros Khan', 'Radiant Corsair', 'Yerdan']
        
        updated_count = 0
        
        for monster_name in monsters_to_update:
            print(f"\n处理怪物: {monster_name}")
            
            # 查找怪物
            monster_found = False
            for monster in monsters_data:
                if monster['name'] == monster_name:
                    monster_found = True
                    
                    # 查找 Right-Handed 技能
                    skill_found = False
                    for skill in monster['skills']:
                        if skill['name'] == 'Right-Handed':
                            skill_found = True
                            
                            # 下载图标
                            icon_path = download_icon(icon_url, monster_name, 'Right-Handed')
                            
                            # 更新技能数据
                            skill['icon'] = icon_path
                            skill['icon_url'] = icon_url
                            skill['description'] = description
                            
                            updated_count += 1
                            print(f"  ✓ 更新成功")
                            break
                    
                    if not skill_found:
                        print(f"  ! 该怪物没有 Right-Handed 技能")
                    
                    break
            
            if not monster_found:
                print(f"  ✗ 未找到怪物: {monster_name}")
        
        # 保存更新
        if updated_count > 0:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(monsters_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n{'=' * 80}")
            print(f"✓ 成功更新 {updated_count} 个怪物的 Right-Handed 技能")
            print(f"✓ 已保存到: {json_file}")
            print('=' * 80)
        else:
            print(f"\n未进行任何更新")
            
    finally:
        driver.quit()
        print("\n关闭浏览器...")

if __name__ == "__main__":
    fix_right_handed_skill()
