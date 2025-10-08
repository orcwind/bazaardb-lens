"""
重试失败的怪物和图标下载
从错误日志中读取失败项并重新抓取/下载
"""

import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 导入主爬虫的函数
import sys
sys.path.append(str(Path(__file__).parent))

# 配置
OUTPUT_DIR = Path('monster_details_v3')
ICONS_DIR = OUTPUT_DIR / 'icons'
LOGS_DIR = OUTPUT_DIR / 'logs'

def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def load_error_log(log_file):
    """加载错误日志"""
    with open(log_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_monsters_json():
    """加载当前的怪物数据"""
    json_file = OUTPUT_DIR / 'monsters_v3.json'
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_monsters_json(monsters_data):
    """保存怪物数据"""
    json_file = OUTPUT_DIR / 'monsters_v3.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(monsters_data, f, ensure_ascii=False, indent=2)

def download_icon(icon_url, monster_name, card_name, card_type='skill'):
    """下载图标"""
    if not icon_url:
        print(f"        ✗ 无图标URL")
        return ""
    
    try:
        safe_monster_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
        safe_card_name = re.sub(r'[<>:"/\\|?*]', '_', card_name)
        
        filename = f"{safe_monster_name}_{safe_card_name}.webp"
        filepath = ICONS_DIR / filename
        
        if filepath.exists():
            print(f"        图标已存在: {filename}")
            return f"icons/{filename}"
        
        # 下载图标，增加重试次数和超时时间
        for attempt in range(3):
            try:
                response = requests.get(icon_url, timeout=30)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"        ✓ 下载成功: {filename}")
                return f"icons/{filename}"
            except Exception as e:
                if attempt < 2:
                    print(f"        重试 {attempt + 1}/3...")
                    time.sleep(5)
                else:
                    raise e
    
    except Exception as e:
        print(f"        ✗ 下载失败: {e}")
        return ""

def get_monster_detail_url(driver, monster_name):
    """通过搜索获取怪物的详情页URL"""
    search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
    driver.get(search_url)
    
    try:
        time.sleep(3)
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        detail_url = card_link.get_attribute('href')
        return detail_url
    except Exception as e:
        print(f"    ✗ 搜索出错: {e}")
        return None

def extract_names_from_meta(html_content):
    """从meta描述中提取技能和物品名称"""
    meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html_content)
    if not meta_match:
        return [], []
    
    description = meta_match.group(1)
    
    skills = []
    skills_match = re.search(r'Skills:\s*([^.]+)\.', description)
    if skills_match:
        skills_str = skills_match.group(1)
        skills = [s.strip() for s in skills_str.split(',')]
    
    items = []
    items_match = re.search(r'Items:\s*([^.]+)\.', description)
    if items_match:
        items_str = items_match.group(1)
        items = [i.strip() for i in items_str.split(',')]
    
    return skills, items

def extract_icons_from_html(html_content):
    """从HTML中提取图标URL映射"""
    icons = {'skills': {}, 'items': {}}
    
    skill_icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/skill/([a-f0-9]+)@256\.webp[^"]*', html_content)
    if skill_icon_matches:
        unique_skill_hashes = list(dict.fromkeys(skill_icon_matches))
        for skill_hash in unique_skill_hashes:
            skill_icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/skill/{skill_hash}@256.webp?v=0"
            icons['skills'][skill_hash] = skill_icon_url
    
    item_icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/item/([a-f0-9]+)@256\.webp[^"]*', html_content)
    if item_icon_matches:
        unique_item_hashes = list(dict.fromkeys(item_icon_matches))
        for item_hash in unique_item_hashes:
            item_icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/item/{item_hash}@256.webp?v=0"
            icons['items'][item_hash] = item_icon_url
    
    return icons

def get_card_description(driver, card_url):
    """访问卡片详情页获取描述"""
    try:
        driver.get(card_url)
        time.sleep(3)
        
        html = driver.page_source
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        
        if desc_matches:
            valid_descriptions = []
            
            for description_html in desc_matches:
                description = re.sub(r'<[^>]+>', '', description_html)
                description = re.sub(r'<!--\s*-->', '', description)
                description = description.replace('&nbsp;', ' ')
                description = description.replace('&amp;', '&')
                description = description.replace('&lt;', '<')
                description = description.replace('&gt;', '>')
                description = description.replace('&#x27;', "'")
                description = description.strip()
                
                if (len(description) > 10 and 
                    'Offered by' not in description and 
                    'Dropped by' not in description and
                    'Found in' not in description):
                    valid_descriptions.append(description)
            
            if valid_descriptions:
                return '. '.join(valid_descriptions)
        
        return ""
    except Exception as e:
        print(f"      ✗ 获取描述失败: {e}")
        return ""

def extract_monster_details(driver, monster_name, detail_url):
    """从详情页提取怪物信息"""
    print(f"  访问详情页...")
    driver.get(detail_url)
    time.sleep(5)
    
    html_content = driver.page_source
    
    print(f"  提取名称...")
    skill_names, item_names = extract_names_from_meta(html_content)
    print(f"    技能: {skill_names}")
    print(f"    物品: {item_names}")
    
    print(f"  提取图标...")
    icons = extract_icons_from_html(html_content)
    
    monster_data = {
        "name": monster_name,
        "url": detail_url,
        "skills": [],
        "items": []
    }
    
    # 处理技能
    print(f"  处理技能...")
    skill_icon_urls = list(icons['skills'].values())
    
    for idx, skill_name in enumerate(skill_names):
        print(f"    [{skill_name}]")
        
        skill_url_match = re.search(rf'href="(/card/[^"]+/{re.escape(skill_name.replace(" ", "-"))})"', html_content)
        if skill_url_match:
            skill_url = f"https://bazaardb.gg{skill_url_match.group(1)}"
            skill_icon_url = skill_icon_urls[idx] if idx < len(skill_icon_urls) else ''
            skill_icon_path = download_icon(skill_icon_url, monster_name, skill_name, 'skill')
            description = get_card_description(driver, skill_url)
            
            monster_data["skills"].append({
                "name": skill_name,
                "url": skill_url,
                "icon": skill_icon_path,
                "icon_url": skill_icon_url,
                "description": description
            })
            print(f"      ✓ 完成")
    
    # 处理物品
    print(f"  处理物品...")
    unique_items = list(dict.fromkeys(item_names))
    item_icon_urls = list(icons['items'].values())
    
    for idx, item_name in enumerate(unique_items):
        print(f"    [{item_name}]")
        
        item_url_match = re.search(rf'href="(/card/[^"]+/{re.escape(item_name.replace(" ", "-"))})"', html_content)
        if item_url_match:
            item_url = f"https://bazaardb.gg{item_url_match.group(1)}"
            item_icon_url = item_icon_urls[idx] if idx < len(item_icon_urls) else ''
            item_icon_path = download_icon(item_icon_url, monster_name, item_name, 'item')
            description = get_card_description(driver, item_url)
            
            monster_data["items"].append({
                "name": item_name,
                "url": item_url,
                "icon": item_icon_path,
                "icon_url": item_icon_url,
                "description": description
            })
            print(f"      ✓ 完成")
    
    return monster_data

def retry_failed_monsters(driver, error_log, monsters_data):
    """重新抓取完全失败的怪物"""
    failed_monsters = error_log.get('failed_monsters', [])
    
    if not failed_monsters:
        print("没有失败的怪物需要重试。")
        return monsters_data
    
    print(f"\n{'=' * 80}")
    print(f"重新抓取 {len(failed_monsters)} 个失败的怪物")
    print('=' * 80)
    
    success_count = 0
    
    for i, failed in enumerate(failed_monsters, 1):
        monster_name = failed['monster']
        print(f"\n[{i}/{len(failed_monsters)}] 重试: {monster_name}")
        print(f"  原错误: {failed['error']}")
        
        try:
            # 获取详情页URL
            print(f"  搜索怪物...")
            detail_url = get_monster_detail_url(driver, monster_name)
            
            if detail_url:
                print(f"    ✓ 找到: {detail_url}")
                
                # 提取详细信息
                monster_details = extract_monster_details(driver, monster_name, detail_url)
                
                # 检查是否已存在该怪物，如果存在则更新，否则添加
                existing_idx = None
                for idx, m in enumerate(monsters_data):
                    if m['name'] == monster_name:
                        existing_idx = idx
                        break
                
                if existing_idx is not None:
                    monsters_data[existing_idx] = monster_details
                    print(f"  ✓ 更新成功")
                else:
                    monsters_data.append(monster_details)
                    print(f"  ✓ 添加成功")
                
                # 立即保存
                save_monsters_json(monsters_data)
                success_count += 1
                
            else:
                print(f"  ✗ 仍然未找到详情页")
                
        except Exception as e:
            print(f"  ✗ 重试失败: {e}")
            continue
        
        # 延迟
        time.sleep(2)
    
    print(f"\n重试结果: 成功 {success_count}/{len(failed_monsters)}")
    return monsters_data

def retry_failed_icons(error_log, monsters_data):
    """重新下载失败的图标"""
    failed_skills = error_log.get('failed_skill_downloads', [])
    failed_items = error_log.get('failed_item_downloads', [])
    
    total_to_retry = len(failed_skills) + len(failed_items)
    
    if total_to_retry == 0:
        print("没有失败的图标需要重试。")
        return monsters_data
    
    print(f"\n{'=' * 80}")
    print(f"重新下载 {total_to_retry} 个失败的图标")
    print('=' * 80)
    
    success_count = 0
    
    # 重试技能图标
    if failed_skills:
        print(f"\n重试 {len(failed_skills)} 个技能图标...")
        for i, failed in enumerate(failed_skills, 1):
            monster_name = failed['monster']
            card_name = failed['card']
            icon_url = failed.get('url', '')
            
            print(f"\n[{i}/{len(failed_skills)}] {monster_name} - {card_name}")
            print(f"  原因: {failed['reason']}")
            
            if not icon_url:
                print(f"  ✗ 跳过（无URL）")
                continue
            
            # 下载图标
            icon_path = download_icon(icon_url, monster_name, card_name, 'skill')
            
            if icon_path:
                # 更新JSON中的图标路径
                for monster in monsters_data:
                    if monster['name'] == monster_name:
                        for skill in monster['skills']:
                            if skill['name'] == card_name:
                                skill['icon'] = icon_path
                                success_count += 1
                                print(f"  ✓ 更新JSON成功")
                                break
                        break
    
    # 重试物品图标
    if failed_items:
        print(f"\n重试 {len(failed_items)} 个物品图标...")
        for i, failed in enumerate(failed_items, 1):
            monster_name = failed['monster']
            card_name = failed['card']
            icon_url = failed.get('url', '')
            
            print(f"\n[{i}/{len(failed_items)}] {monster_name} - {card_name}")
            print(f"  原因: {failed['reason']}")
            
            if not icon_url:
                print(f"  ✗ 跳过（无URL）")
                continue
            
            # 下载图标
            icon_path = download_icon(icon_url, monster_name, card_name, 'item')
            
            if icon_path:
                # 更新JSON中的图标路径
                for monster in monsters_data:
                    if monster['name'] == monster_name:
                        for item in monster['items']:
                            if item['name'] == card_name:
                                item['icon'] = icon_path
                                success_count += 1
                                print(f"  ✓ 更新JSON成功")
                                break
                        break
    
    # 保存更新后的数据
    if success_count > 0:
        save_monsters_json(monsters_data)
        print(f"\n✓ 已保存更新")
    
    print(f"\n重试结果: 成功 {success_count}/{total_to_retry}")
    return monsters_data

def main():
    """主函数"""
    print("=" * 80)
    print("重试失败的怪物和图标")
    print("=" * 80)
    
    # 查找最新的错误日志
    log_files = sorted(LOGS_DIR.glob('error_log_*.json'))
    if not log_files:
        print("未找到错误日志文件。")
        return
    
    latest_log = log_files[-1]
    print(f"\n使用错误日志: {latest_log.name}")
    
    # 加载错误日志和怪物数据
    error_log = load_error_log(latest_log)
    monsters_data = load_monsters_json()
    
    print(f"\n当前状态:")
    print(f"  怪物总数: {len(monsters_data)}")
    print(f"  失败的怪物: {len(error_log.get('failed_monsters', []))}")
    print(f"  失败的技能图标: {len(error_log.get('failed_skill_downloads', []))}")
    print(f"  失败的物品图标: {len(error_log.get('failed_item_downloads', []))}")
    
    driver = None
    
    try:
        # 重试失败的怪物
        if error_log.get('failed_monsters'):
            driver = setup_driver()
            monsters_data = retry_failed_monsters(driver, error_log, monsters_data)
        
        # 重试失败的图标（不需要driver）
        if error_log.get('failed_skill_downloads') or error_log.get('failed_item_downloads'):
            monsters_data = retry_failed_icons(error_log, monsters_data)
        
        print(f"\n{'=' * 80}")
        print("重试完成！")
        print('=' * 80)
        
    finally:
        if driver:
            driver.quit()
            print("\n关闭浏览器...")

if __name__ == "__main__":
    main()
