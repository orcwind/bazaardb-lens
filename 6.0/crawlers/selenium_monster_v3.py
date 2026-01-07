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

def is_chinese(text):
    """检查文本是否包含中文字符"""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def save_name_with_lang(data_dict, name, field_name='name'):
    """根据语言保存名称到相应字段（name 或 name_zh）"""
    if is_chinese(name):
        data_dict[f'{field_name}_zh'] = name
        # 如果已有英文名称，保留；否则也保存到 name 字段作为备用
        if field_name not in data_dict:
            data_dict[field_name] = name
    else:
        data_dict[field_name] = name
        # 如果已有中文名称，保留；否则也保存到 name_zh 字段作为备用
        if f'{field_name}_zh' not in data_dict:
            data_dict[f'{field_name}_zh'] = name

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
    """从meta描述中提取技能和物品名称（支持中英文）"""
    # 查找meta description
    meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html_content)
    if not meta_match:
        return [], []
    
    description = meta_match.group(1)
    print(f"    Meta描述: {description}")
    
    # 提取技能名称（支持中英文）
    skills = []
    # 尝试匹配中文格式：技能：xxx。或英文格式：Skills: xxx.
    skills_match = re.search(r'(?:技能|Skills):\s*([^.。]+)[。.]', description)
    if skills_match:
        skills_str = skills_match.group(1)
        skills = [s.strip() for s in re.split(r'[,，]', skills_str)]
    
    # 提取物品名称（支持中英文）
    items = []
    # 尝试匹配中文格式：物品：xxx。或英文格式：Items: xxx.
    items_match = re.search(r'(?:物品|Items):\s*([^.。]+)[。.]', description)
    if items_match:
        items_str = items_match.group(1)
        items = [i.strip() for i in re.split(r'[,，]', items_str)]
    
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


def extract_card_size(html):
    """从HTML中提取卡片尺寸
    
    Returns:
        尺寸字符串 (Small/Medium/Large) 或 None
    """
    # 尝试多种正则表达式模式
    size_patterns = [
        r'<span[^>]*>\s*(Small|Medium|Large)\s*</span>',
        r'<div[^>]*>\s*(Small|Medium|Large)\s*</div>',
        r'"size"\s*:\s*"(Small|Medium|Large)"',
        r'Size["\s:]*(["\s]*)(Small|Medium|Large)',
        r'class="[^"]*"[^>]*>\s*(Small|Medium|Large)\s*<',
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            # 返回第一个捕获组（尺寸）
            groups = match.groups()
            for group in groups:
                if group and group.strip() in ['Small', 'Medium', 'Large', 'small', 'medium', 'large']:
                    return group.capitalize()
    
    return None


def size_to_aspect_ratio(size):
    """将卡片尺寸转换为图标长宽比
    
    Args:
        size: 卡片尺寸 (Small/Medium/Large/None)
    
    Returns:
        长宽比: Small=0.5 (竖长), Medium=1.0 (正方), Large=1.5 (横长)
    """
    if not size:
        return 1.0
    
    size_upper = size.upper()
    if size_upper == 'SMALL':
        return 0.5
    elif size_upper == 'MEDIUM':
        return 1.0
    elif size_upper == 'LARGE':
        return 1.5
    else:
        return 1.0


def smart_merge_skill_data(existing_skill, new_skill):
    """智能合并技能数据
    
    规则：
    1. 如果新数据为空或无效，保留原有数据
    2. 如果新数据有效，使用新数据覆盖
    3. 图标路径：如果新图标下载成功，使用新路径；否则保留原有
    
    Args:
        existing_skill: 已有的技能数据
        new_skill: 新抓取的技能数据
    
    Returns:
        合并后的技能数据
    """
    merged = existing_skill.copy()
    
    # 描述：只有新描述不为空时才覆盖
    if new_skill.get('description', '').strip():
        merged['description'] = new_skill['description']
    
    # URL：只有新URL不为空时才覆盖
    if new_skill.get('url', '').strip():
        merged['url'] = new_skill['url']
    
    # 图标URL：只有新图标URL不为空时才覆盖
    if new_skill.get('icon_url', '').strip():
        merged['icon_url'] = new_skill['icon_url']
    
    # 图标路径：只有新图标下载成功时才覆盖
    if new_skill.get('icon', '').strip() and not new_skill['icon'].startswith('icons/'):
        # 如果新图标路径不是默认路径，说明下载成功
        merged['icon'] = new_skill['icon']
    
    # 长宽比：只有新长宽比有效时才覆盖
    if new_skill.get('aspect_ratio') is not None:
        merged['aspect_ratio'] = new_skill['aspect_ratio']
    
    return merged


def smart_merge_item_data(existing_item, new_item):
    """智能合并物品数据（逻辑同技能）"""
    return smart_merge_skill_data(existing_item, new_item)


def get_card_description(driver, card_url, card_type='skill'):
    """访问卡片详情页获取描述和尺寸
    
    Returns:
        (description, size) - 描述和尺寸（Small/Medium/Large）
    """
    try:
        driver.get(card_url)
        time.sleep(3)  # 等待页面加载
        
        html = driver.page_source
        
        # 提取尺寸信息
        size = extract_card_size(html)
        
        # 方法1: 尝试从HTML源码中提取（旧方法）
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        
        description = ""
        if desc_matches:
            # 收集所有有效的描述
            valid_descriptions = []
            
            for description_html in desc_matches:
                # 清理HTML标签和注释
                desc = re.sub(r'<[^>]+>', '', description_html)
                desc = re.sub(r'<!--\s*-->', '', desc)
                # 清理HTML实体
                desc = desc.replace('&nbsp;', ' ')
                desc = desc.replace('&amp;', '&')
                desc = desc.replace('&lt;', '<')
                desc = desc.replace('&gt;', '>')
                desc = desc.replace('&#x27;', "'")
                desc = desc.strip()
                
                # 过滤掉无效描述
                if (len(desc) > 10 and 
                    'Offered by' not in desc and 
                    'Dropped by' not in desc and
                    'Found in' not in desc):
                    valid_descriptions.append(desc)
            
            # 合并所有有效描述，用句号分隔
            if valid_descriptions:
                description = '. '.join(valid_descriptions)
        
        # 方法2: 如果方法1失败，尝试从渲染后的页面文本中提取
        if not description:
            try:
                # 获取渲染后的页面所有文本
                page_text = driver.execute_script("return document.body.innerText;")
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                
                # 查找包含游戏术语的文本行（可能是描述）
                for line in lines:
                    if (len(line) > 20 and 
                        len(line) < 500 and
                        any(keyword in line for keyword in ['Deal', 'Gain', 'When', 'Shield', 'Damage', 'Heal', 'Haste', 'Slow', 'Poison', 'Burn', 'Charge', 'Cooldown', 'Max Health', 'Regen', 'Freeze'])):
                        # 过滤掉明显不是描述的行
                        if not any(skip in line for skip in ['Offered by', 'Dropped by', 'Found in', 'Level', 'Day', 'Gold', 'XP', 'Enchantment', 'Tier']):
                            description = line
                            break
            except Exception as e:
                print(f"        ⚠ 方法2提取失败: {e}")
        
        return description, size
    except Exception as e:
        print(f"      ✗ 获取卡片信息失败: {e}")
        return "", None


def extract_monster_details(driver, monster_name, detail_url, existing_monster=None):
    """从详情页提取怪物信息
    
    Args:
        driver: Selenium WebDriver
        monster_name: 怪物名称
        detail_url: 详情页URL
        existing_monster: 已有的怪物数据（用于智能覆盖）
    
    Returns:
        怪物数据字典
    """
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
        "url": detail_url,
        "skills": [],
        "items": []
    }
    # 根据语言保存怪物名称
    save_name_with_lang(monster_data, monster_name, 'name')
    
    # 处理技能
    print(f"\n  处理技能详情...")
    skill_icon_urls = list(icons['skills'].values())  # 按顺序获取图标URL
    
    # 获取已有技能数据（用于智能覆盖）
    existing_skills = {}
    if existing_monster:
        existing_skills = {skill['name']: skill for skill in existing_monster.get('skills', [])}
    
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
            
            # 获取描述和尺寸
            description, size = get_card_description(driver, skill_url, 'skill')
            
            # 智能覆盖逻辑
            skill_data = {
                "url": skill_url,
                "icon": skill_icon_path,
                "icon_url": skill_icon_url,
                "aspect_ratio": size_to_aspect_ratio(size)
            }
            # 根据语言保存名称和描述
            save_name_with_lang(skill_data, skill_name, 'name')
            save_name_with_lang(skill_data, description, 'description')
            
            # 如果已有数据，进行智能合并
            if skill_name in existing_skills:
                existing_skill = existing_skills[skill_name]
                skill_data = smart_merge_skill_data(existing_skill, skill_data)
                print(f"      🔄 智能合并已有数据")
            
            monster_data["skills"].append(skill_data)
            
            if size:
                print(f"      ✓ 描述: {description[:50]}... [{size}, 比例:{skill_data['aspect_ratio']}]")
            else:
                print(f"      ✓ 描述: {description[:50]}... [比例:{skill_data['aspect_ratio']}]")
        else:
            print(f"      ✗ 未找到URL")
            # 如果已有数据，保留
            if skill_name in existing_skills:
                monster_data["skills"].append(existing_skills[skill_name])
                print(f"      ℹ️  保留已有技能数据")
    
    # 处理物品（去重）
    print(f"\n  处理物品详情...")
    unique_items = list(dict.fromkeys(item_names))  # 保持顺序的去重
    item_icon_urls = list(icons['items'].values())  # 按顺序获取图标URL
    
    # 获取已有物品数据（用于智能覆盖）
    existing_items = {}
    if existing_monster:
        existing_items = {item['name']: item for item in existing_monster.get('items', [])}
    
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
            
            # 获取描述和尺寸
            description, size = get_card_description(driver, item_url, 'item')
            
            # 智能覆盖逻辑
            item_data = {
                "url": item_url,
                "icon": item_icon_path,
                "icon_url": item_icon_url,
                "aspect_ratio": size_to_aspect_ratio(size)
            }
            # 根据语言保存名称和描述
            save_name_with_lang(item_data, item_name, 'name')
            save_name_with_lang(item_data, description, 'description')
            
            # 如果已有数据，进行智能合并
            if item_name in existing_items:
                existing_item = existing_items[item_name]
                item_data = smart_merge_item_data(existing_item, item_data)
                print(f"      🔄 智能合并已有数据")
            
            monster_data["items"].append(item_data)
            
            if size:
                print(f"      ✓ 描述: {description[:50]}... [{size}, 比例:{item_data['aspect_ratio']}]")
            else:
                print(f"      ✓ 描述: {description[:50]}... [比例:{item_data['aspect_ratio']}]")
        else:
            print(f"      ✗ 未找到URL")
            # 如果已有数据，保留
            if item_name in existing_items:
                monster_data["items"].append(existing_items[item_name])
                print(f"      ℹ️  保留已有物品数据")
    
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


def check_missing_aspect_ratios(monsters):
    """检查缺失长宽比的项目
    
    Returns:
        需要更新的怪物列表 [(monster_index, card_list)]
    """
    monsters_need_update = []
    
    for idx, monster in enumerate(monsters):
        cards_need_update = []
        
        for skill in monster.get('skills', []):
            if 'aspect_ratio' not in skill and skill.get('url'):
                cards_need_update.append({
                    'type': 'skill',
                    'name': skill.get('name'),
                    'url': skill.get('url'),
                    'data': skill
                })
        
        for item in monster.get('items', []):
            if 'aspect_ratio' not in item and item.get('url'):
                cards_need_update.append({
                    'type': 'item',
                    'name': item.get('name'),
                    'url': item.get('url'),
                    'data': item
                })
        
        if cards_need_update:
            monsters_need_update.append((idx, monster, cards_need_update))
    
    return monsters_need_update


def update_missing_aspect_ratios(driver, all_monsters):
    """为已有怪物补充缺失的长宽比"""
    print("\n" + "="*80)
    print("检查并更新缺失的长宽比")
    print("="*80)
    
    monsters_need_update = check_missing_aspect_ratios(all_monsters)
    
    if not monsters_need_update:
        print("✓ 所有怪物已有完整的长宽比信息")
        return 0
    
    total_cards = sum(len(cards) for _, _, cards in monsters_need_update)
    print(f"\n发现 {len(monsters_need_update)} 个怪物需要更新长宽比")
    print(f"共 {total_cards} 个卡片缺失长宽比")
    
    updated_count = 0
    
    for monster_idx, monster, cards in monsters_need_update:
        monster_name = monster.get('name', 'Unknown')
        print(f"\n[更新] {monster_name} - {len(cards)} 个项目")
        
        for card in cards:
            card_name = card['name']
            card_url = card['url']
            card_data = card['data']
            
            print(f"  {card['type']}: {card_name}")
            
            try:
                # 访问详情页获取尺寸
                driver.get(card_url)
                time.sleep(2)
                html = driver.page_source
                size = extract_card_size(html)
                aspect_ratio = size_to_aspect_ratio(size)
                
                # 更新数据
                card_data['aspect_ratio'] = aspect_ratio
                
                if size:
                    print(f"    ✓ {size} → {aspect_ratio}")
                else:
                    print(f"    ⚠ 未找到尺寸，使用默认 → {aspect_ratio}")
                
                updated_count += 1
                
            except Exception as e:
                print(f"    ✗ 更新失败: {e}")
                # 使用默认值
                card_data['aspect_ratio'] = 1.0
    
    print(f"\n✓ 已更新 {updated_count} 个卡片的长宽比")
    return updated_count


def main():
    """主函数"""
    print("=" * 80)
    print("Selenium怪物爬虫 V3 - 处理所有怪物（增量保存 + 长宽比更新）")
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
    
    # 启动浏览器
    driver = setup_driver()
    total_skills = 0
    total_items = 0
    
    # 步骤1: 补充已有怪物的长宽比（如果缺失）
    if all_monsters:
        updated_aspect_count = update_missing_aspect_ratios(driver, all_monsters)
        if updated_aspect_count > 0:
            # 保存更新后的数据
            save_monsters_to_json(all_monsters, output_file)
            print(f"✓ 长宽比已更新并保存")
    
    # 步骤2: 爬取新怪物
    if not remaining_monsters:
        print("\n✓ 所有怪物已处理完成！")
        driver.quit()
        return
    
    print(f"\n将继续处理剩余的 {len(remaining_monsters)} 个怪物...")
    print("="*80)

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
                    # 检查是否已有此怪物的数据
                    existing_monster = None
                    for existing in all_monsters:
                        if existing['name'] == monster_name:
                            existing_monster = existing
                            break
                    
                    monster_details = extract_monster_details(driver, monster_name, detail_url, existing_monster)
                    
                    if existing_monster:
                        # 更新已有怪物数据
                        all_monsters = [m for m in all_monsters if m['name'] != monster_name]
                    
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
