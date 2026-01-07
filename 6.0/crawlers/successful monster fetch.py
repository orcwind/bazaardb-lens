@ -0,0 +1,522 @@
"""
Selenium怪物爬虫 V3 - 完整版（处理所有怪物）
功能：
1. 从meta描述提取技能和物品名称
2. 从HTML中提取图标URL
3. 访问详情页获取描述
4. 下载图标并保存到本地（命名格式：怪物名_技能/物品名.webp）
5. 增量保存：每处理完一个怪物立即保存到JSON文件
"""

import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置
OUTPUT_DIR = Path('monster_details_v3')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR = OUTPUT_DIR / 'icons'
ICONS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = OUTPUT_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MONSTERS_FILE = 'unique_monsters.json'

# 全局错误日志
ERROR_LOG = {
    'failed_monsters': [],           # 完全失败的怪物
    'missing_detail_urls': [],       # 未找到详情页的怪物
    'missing_skills': [],            # 未找到技能的怪物
    'missing_items': [],             # 未找到物品的怪物
    'failed_skill_downloads': [],    # 技能图标下载失败
    'failed_item_downloads': [],     # 物品图标下载失败
    'failed_descriptions': [],       # 描述获取失败
    'exceptions': []                 # 其他异常
}


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def load_monster_names(file_path):
    """从文件中加载怪物名称列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return []


def download_icon(icon_url, monster_name, card_name, card_type='skill'):
    """下载图标并返回本地路径
    
    Args:
        icon_url: 图标URL
        monster_name: 怪物名称
        card_name: 技能/物品名称
        card_type: 'skill' 或 'item'
    
    Returns:
        本地图标路径（相对于输出目录）或空字符串（如果下载失败）
    """
    if not icon_url:
        error_entry = {
            'monster': monster_name,
            'card': card_name,
            'type': card_type,
            'reason': 'No icon URL provided'
        }
        if card_type == 'skill':
            ERROR_LOG['failed_skill_downloads'].append(error_entry)
        else:
            ERROR_LOG['failed_item_downloads'].append(error_entry)
        return ""
    
    try:
        # 清理文件名中的非法字符
        safe_monster_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
        safe_card_name = re.sub(r'[<>:"/\\|?*]', '_', card_name)
        
        # 构建文件名: 怪物名_技能名.webp
        filename = f"{safe_monster_name}_{safe_card_name}.webp"
        filepath = ICONS_DIR / filename
        
        # 如果文件已存在，跳过下载
        if filepath.exists():
            print(f"        图标已存在: {filename}")
            return f"icons/{filename}"
        
        # 下载图标
        response = requests.get(icon_url, timeout=10)
        response.raise_for_status()
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"        ✓ 下载图标: {filename}")
        return f"icons/{filename}"
    
    except Exception as e:
        print(f"        ✗ 下载图标失败: {e}")
        error_entry = {
            'monster': monster_name,
            'card': card_name,
            'type': card_type,
            'url': icon_url,
            'reason': str(e)
        }
        if card_type == 'skill':
            ERROR_LOG['failed_skill_downloads'].append(error_entry)
        else:
            ERROR_LOG['failed_item_downloads'].append(error_entry)
        return ""


def get_monster_detail_url(driver, monster_name):
    """通过搜索获取怪物的详情页URL"""
    search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
    driver.get(search_url)
    
    try:
        # 等待搜索结果加载
        time.sleep(3)
        
        # 查找第一个卡片链接
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        detail_url = card_link.get_attribute('href')
        print(f"    ✓ 找到: {detail_url}")
        return detail_url
    except NoSuchElementException:
        print(f"    ✗ 未找到怪物: {monster_name}")
        return None
    except Exception as e:
        print(f"    ✗ 搜索出错: {e}")
        return None


def extract_names_from_meta(html_content):
    """从meta描述中提取技能和物品名称"""
    # 查找meta description
    meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html_content)
    if not meta_match:
        return [], []
    
    description = meta_match.group(1)
    print(f"    Meta描述: {description}")
    
    # 提取技能名称
    skills = []
    skills_match = re.search(r'Skills:\s*([^.]+)\.', description)
    if skills_match:
        skills_str = skills_match.group(1)
        skills = [s.strip() for s in skills_str.split(',')]
    
    # 提取物品名称
    items = []
    items_match = re.search(r'Items:\s*([^.]+)\.', description)
    if items_match:
        items_str = items_match.group(1)
        items = [i.strip() for i in items_str.split(',')]
    
    return skills, items


def extract_icons_from_html(html_content):
    """从HTML中提取图标URL映射（从img标签提取）"""
    icons = {
        'skills': {},
        'items': {}
    }
    
    # 方法：从HTML中查找skill和item的图标URL
    # 技能图标格式：skill/[hash]@256.webp
    skill_icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/skill/([a-f0-9]+)@256\.webp[^"]*', html_content)
    if skill_icon_matches:
        # 去重（同一个技能可能出现多次）
        unique_skill_hashes = list(dict.fromkeys(skill_icon_matches))
        for skill_hash in unique_skill_hashes:
            skill_icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/skill/{skill_hash}@256.webp?v=0"
            # 暂时用hash作为key，后面会通过名称匹配
            icons['skills'][skill_hash] = skill_icon_url
            print(f"      找到技能图标: {skill_icon_url[:70]}...")
    
    # 物品图标格式：item/[hash]@256.webp
    item_icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/item/([a-f0-9]+)@256\.webp[^"]*', html_content)
    if item_icon_matches:
        # 去重
        unique_item_hashes = list(dict.fromkeys(item_icon_matches))
        for item_hash in unique_item_hashes:
            item_icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/item/{item_hash}@256.webp?v=0"
            icons['items'][item_hash] = item_icon_url
            print(f"      找到物品图标: {item_icon_url[:70]}...")
    
    print(f"    ✓ 找到 {len(icons['skills'])} 个技能图标, {len(icons['items'])} 个物品图标")
    
    return icons


def get_card_description(driver, card_url, card_type='skill'):
    """访问卡片详情页获取描述"""
    try:
        driver.get(card_url)
        time.sleep(3)  # 等待页面加载
        
        html = driver.page_source
        
        # 从页面中查找所有 <div class="_bM"> 中的描述文本
        # 这些描述包含实际的技能/物品效果
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        
        if desc_matches:
            # 收集所有有效的描述
            valid_descriptions = []
            
            for description_html in desc_matches:
                # 清理HTML标签和注释
                description = re.sub(r'<[^>]+>', '', description_html)
                description = re.sub(r'<!--\s*-->', '', description)
                # 清理HTML实体
                description = description.replace('&nbsp;', ' ')
                description = description.replace('&amp;', '&')
                description = description.replace('&lt;', '<')
                description = description.replace('&gt;', '>')
                description = description.replace('&#x27;', "'")
                description = description.strip()
                
                # 过滤掉无效描述
                if (len(description) > 10 and 
                    'Offered by' not in description and 
                    'Dropped by' not in description and
                    'Found in' not in description):
                    valid_descriptions.append(description)
            
            # 合并所有有效描述，用句号分隔
            if valid_descriptions:
                return '. '.join(valid_descriptions)
        
        return ""
    except Exception as e:
        print(f"      ✗ 获取描述失败: {e}")
        return ""


def extract_monster_details(driver, monster_name, detail_url):
    """从详情页提取怪物信息"""
    print(f"\n  [2/4] 访问怪物详情页...")
    driver.get(detail_url)
    time.sleep(5)
    
    html_content = driver.page_source
    
    # 步骤1: 从meta描述提取技能和物品名称
    print(f"\n  [3/4] 从meta描述提取名称...")
    skill_names, item_names = extract_names_from_meta(html_content)
    print(f"    ✓ 技能: {skill_names}")
    print(f"    ✓ 物品: {item_names}")
    
    # 记录没有技能或物品的怪物
    if not skill_names:
        ERROR_LOG['missing_skills'].append({
            'monster': monster_name,
            'url': detail_url
        })
    if not item_names:
        ERROR_LOG['missing_items'].append({
            'monster': monster_name,
            'url': detail_url
        })
    
    # 步骤2: 从HTML提取图标URL
    print(f"\n  [4/4] 从HTML提取图标...")
    icons = extract_icons_from_html(html_content)
    
    monster_data = {
        "name": monster_name,
        "url": detail_url,
        "skills": [],
        "items": []
    }
    
    # 处理技能
    print(f"\n  处理技能详情...")
    skill_icon_urls = list(icons['skills'].values())  # 按顺序获取图标URL
    
    for idx, skill_name in enumerate(skill_names):
        print(f"    [{skill_name}]")
        
        # 构建技能URL（需要从HTML中查找完整URL）
        skill_url_match = re.search(rf'href="(/card/[^"]+/{re.escape(skill_name.replace(" ", "-"))})"', html_content)
        if skill_url_match:
            skill_url = f"https://bazaardb.gg{skill_url_match.group(1)}"
            
            # 按顺序匹配图标URL
            skill_icon_url = skill_icon_urls[idx] if idx < len(skill_icon_urls) else ''
            
            # 下载图标
            skill_icon_path = download_icon(skill_icon_url, monster_name, skill_name, 'skill')
            
            # 获取描述
            description = get_card_description(driver, skill_url, 'skill')
            
            monster_data["skills"].append({
                "name": skill_name,
                "url": skill_url,
                "icon": skill_icon_path,
                "icon_url": skill_icon_url,
                "description": description
            })
            print(f"      ✓ 描述: {description[:50]}...")
        else:
            print(f"      ✗ 未找到URL")
    
    # 处理物品（去重）
    print(f"\n  处理物品详情...")
    unique_items = list(dict.fromkeys(item_names))  # 保持顺序的去重
    item_icon_urls = list(icons['items'].values())  # 按顺序获取图标URL
    
    if len(unique_items) < len(item_names):
        print(f"    去重: {len(item_names)} -> {len(unique_items)} 个唯一物品")
    
    for idx, item_name in enumerate(unique_items):
        print(f"    [{item_name}]")
        
        # 构建物品URL
        item_url_match = re.search(rf'href="(/card/[^"]+/{re.escape(item_name.replace(" ", "-"))})"', html_content)
        if item_url_match:
            item_url = f"https://bazaardb.gg{item_url_match.group(1)}"
            
            # 按顺序匹配图标URL
            item_icon_url = item_icon_urls[idx] if idx < len(item_icon_urls) else ''
            
            # 下载图标
            item_icon_path = download_icon(item_icon_url, monster_name, item_name, 'item')
            
            # 获取描述
            description = get_card_description(driver, item_url, 'item')
            
            monster_data["items"].append({
                "name": item_name,
                "url": item_url,
                "icon": item_icon_path,
                "icon_url": item_icon_url,
                "description": description
            })
            print(f"      ✓ 描述: {description[:50]}...")
        else:
            print(f"      ✗ 未找到URL")
    
    return monster_data


def save_monsters_to_json(monsters_list, output_file):
    """保存怪物数据到JSON文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(monsters_list, f, ensure_ascii=False, indent=2)


def save_error_log():
    """保存错误日志到文件"""
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f'error_log_{timestamp}.json'
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(ERROR_LOG, f, ensure_ascii=False, indent=2)
    
    return log_file


def load_existing_monsters(output_file):
    """加载已处理的怪物数据（如果存在）"""
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def main():
    """主函数"""
    print("=" * 80)
    print("Selenium怪物爬虫 V3 - 处理所有怪物（增量保存）")
    print("=" * 80)

    monster_names = load_monster_names(MONSTERS_FILE)
    if not monster_names:
        print("没有怪物名称可供处理。")
        return

    output_file = OUTPUT_DIR / 'monsters_v3.json'
    
    # 加载已处理的怪物
    all_monsters = load_existing_monsters(output_file)
    processed_names = {m['name'] for m in all_monsters}
    
    # 过滤出未处理的怪物
    remaining_monsters = [name for name in monster_names if name not in processed_names]
    
    print(f"\n总怪物数: {len(monster_names)}")
    print(f"已处理: {len(processed_names)}")
    print(f"待处理: {len(remaining_monsters)}")
    
    if not remaining_monsters:
        print("\n✓ 所有怪物已处理完成！")
        return
    
    print(f"\n将继续处理剩余的 {len(remaining_monsters)} 个怪物...")
    
    driver = setup_driver()
    total_skills = 0
    total_items = 0

    try:
        for i, monster_name in enumerate(remaining_monsters, 1):
            print(f"\n{'=' * 80}")
            print(f"[{i}/{len(remaining_monsters)}] 处理: {monster_name}")
            print(f"总进度: [{len(all_monsters) + i}/{len(monster_names)}]")
            print('=' * 80)

            try:
                # 步骤1: 获取详情页URL
                print(f"\n  [1/4] 搜索怪物...")
                detail_url = get_monster_detail_url(driver, monster_name)
                
                if detail_url:
                    print(f"    ✓ 找到: {detail_url}")
                    
                    # 步骤2-4: 提取详细信息
                    monster_details = extract_monster_details(driver, monster_name, detail_url)
                    all_monsters.append(monster_details)
                    
                    # 立即保存到JSON文件
                    save_monsters_to_json(all_monsters, output_file)
                    
                    total_skills += len(monster_details['skills'])
                    total_items += len(monster_details['items'])
                    
                    print(f"\n  摘要:")
                    print(f"    技能数: {len(monster_details['skills'])}")
                    print(f"    物品数: {len(monster_details['items'])}")
                    print(f"    ✓ 已保存到: {output_file}")
                else:
                    print(f"    ✗ 未找到详情页")
                    ERROR_LOG['missing_detail_urls'].append({
                        'monster': monster_name,
                        'search_url': f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
                    })
                    
            except Exception as e:
                print(f"\n  ✗ 处理出错: {e}")
                print(f"  继续处理下一个怪物...")
                ERROR_LOG['failed_monsters'].append({
                    'monster': monster_name,
                    'error': str(e)
                })
                ERROR_LOG['exceptions'].append({
                    'monster': monster_name,
                    'error': str(e),
                    'type': type(e).__name__
                })
                continue

    finally:
        # 最终保存
        save_monsters_to_json(all_monsters, output_file)
        
        # 保存错误日志
        log_file = save_error_log()
        
        print(f"\n{'=' * 80}")
        print("处理完成！")
        print('=' * 80)
        print(f"\n✓ 成功处理 {len(all_monsters)} 个怪物")
        print(f"✓ 结果已保存到: {output_file}")
        print(f"✓ 错误日志已保存到: {log_file}")
        
        print(f"\n本次运行统计:")
        print(f"  新增技能数: {total_skills}")
        print(f"  新增物品数: {total_items}")
        
        # 计算总统计
        all_skills = sum(len(m['skills']) for m in all_monsters)
        all_items = sum(len(m['items']) for m in all_monsters)
        print(f"\n总统计:")
        print(f"  总怪物数: {len(all_monsters)}")
        print(f"  总技能数: {all_skills}")
        print(f"  总物品数: {all_items}")
        
        # 显示错误统计
        print(f"\n错误统计:")
        print(f"  未找到详情页: {len(ERROR_LOG['missing_detail_urls'])}")
        print(f"  无技能的怪物: {len(ERROR_LOG['missing_skills'])}")
        print(f"  无物品的怪物: {len(ERROR_LOG['missing_items'])}")
        print(f"  技能图标下载失败: {len(ERROR_LOG['failed_skill_downloads'])}")
        print(f"  物品图标下载失败: {len(ERROR_LOG['failed_item_downloads'])}")
        print(f"  描述获取失败: {len(ERROR_LOG['failed_descriptions'])}")
        print(f"  完全失败的怪物: {len(ERROR_LOG['failed_monsters'])}")
        print(f"  其他异常: {len(ERROR_LOG['exceptions'])}")

        driver.quit()
        print("\n关闭浏览器...")


if __name__ == "__main__":
    main()