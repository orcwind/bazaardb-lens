"""
Selenium物品和技能爬虫 - 完整版
完全参考 selenium_monster_v3.py 的实现方式
功能：
1. 从 unique_items.json 和 unique_skills.json 读取名称列表
2. 访问每个物品/技能的详情页
3. 从详情页HTML中提取图标URL（使用正则表达式）
4. 从详情页获取描述和尺寸
5. 下载图标并保存到统一目录（data/icon）
6. 增量保存：每处理完一个立即保存到JSON文件
7. 支持中英文数据（自动检测语言并保存到相应字段）
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
from utils_icon import download_icon, get_icon_filename, sanitize_filename, NEW_JSON_DIR

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
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ITEMS_FILE = 'unique_items.json'
SKILLS_FILE = 'unique_skills.json'

# 全局错误日志
ERROR_LOG = {
    'failed_items': [],
    'failed_skills': [],
    'missing_detail_urls': [],
    'failed_icon_downloads': [],
    'failed_descriptions': [],
    'exceptions': []
}

def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 启用无头模式，浏览器在后台运行
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def load_card_names(file_path):
    """从文件中加载卡片名称列表（格式类似 unique_monsters.json）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return []

def get_card_detail_url(driver, card_name, category='item'):
    """通过搜索获取卡片的详情页URL（参考 get_monster_detail_url）
    返回英文版URL（不带中文编码）
    """
    search_url = f"https://bazaardb.gg/search?q={card_name.replace(' ', '+')}&c={category}s"
    driver.get(search_url)
    
    try:
        # 等待搜索结果加载
        time.sleep(3)
        
        # 查找第一个卡片链接
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        detail_url = card_link.get_attribute('href')
        
        # 如果URL包含中文编码，尝试获取英文版URL
        # 方法：从URL中提取hash，然后构建英文版URL
        url_match = re.search(r'/card/([^/]+)/', detail_url)
        if url_match:
            card_hash = url_match.group(1)
            # 构建英文版URL（使用原始card_name，将空格替换为连字符）
            en_name = card_name.replace(' ', '-')
            en_url = f"https://bazaardb.gg/card/{card_hash}/{en_name}"
            return en_url
        
        return detail_url
    except NoSuchElementException:
        return None
    except Exception as e:
        return None

def extract_icon_from_html(html_content, card_name):
    """从详情页HTML中提取图标URL（参考 extract_icons_from_html）
    
    Args:
        html_content: 详情页HTML内容
        card_name: 卡片名称（用于调试）
    
    Returns:
        图标URL或空字符串
    """
    icon_url = ""
    
    # 方法1: 从HTML中查找图标URL（类似怪物爬虫的方法）
    # 物品图标格式：item/[hash]@256.webp 或 skill/[hash]@256.webp
    icon_patterns = [
        r'https://s\.bazaardb\.gg/v0/[^/]+/(?:item|skill)/([a-f0-9]+)@256\.webp[^"]*',
        r'src="(https://s\.bazaardb\.gg/v0/[^/]+/(?:item|skill)/[^"]+\.webp[^"]*)"',
        r'src="([^"]*s\.bazaardb\.gg[^"]*\.webp[^"]*)"',
    ]
    
    for pattern in icon_patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            # 使用第一个匹配的URL
            icon_url = matches[0]
            if not icon_url.startswith('http'):
                # 如果只匹配到hash，构建完整URL
                icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/item/{icon_url}@256.webp?v=0"
            break
    
    # 方法2: 如果没找到，尝试从meta标签中提取
    if not icon_url:
        meta_pattern = r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"'
        meta_match = re.search(meta_pattern, html_content)
        if meta_match:
            icon_url = meta_match.group(1)
    
    return icon_url

def extract_card_size(html):
    """从HTML中提取卡片尺寸（参考 selenium_monster_v3.py 的 extract_card_size）
    
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
    """将卡片尺寸转换为图标长宽比（参考 selenium_monster_v3.py）
    
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

def extract_description_from_replaced_tooltips(html):
    """
    从页面中嵌入的 JSON 里提取 ReplacedTooltips（已经替换好数值的中文描述）
    只返回中文部分，按行拼接。
    """
    try:
        key = '"ReplacedTooltips":'
        start = html.find(key)
        if start == -1:
            # 调试信息：没有找到 ReplacedTooltips 字段
            print("      · 未找到 ReplacedTooltips 字段")
            return ""
        i = start + len(key)
        # 跳过空白找到 '['
        while i < len(html) and html[i].isspace():
            i += 1
        if i >= len(html) or html[i] != '[':
            return ""

        # 从 '[' 开始手动匹配整个 JSON 数组，考虑到字符串中可能包含 ']' 字符
        depth = 0
        in_string = False
        escape = False
        arr_chars = []
        while i < len(html):
            ch = html[i]
            arr_chars.append(ch)

            if escape:
                escape = False
            elif ch == '\\\\':
                escape = True
            elif ch == '"':
                in_string = not in_string
            elif not in_string:
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        break
            i += 1

        arr_text = ''.join(arr_chars)
        # 简单校验
        if not arr_text.startswith('[') or not arr_text.endswith(']'):
            print("      · ReplacedTooltips 片段格式异常，开头结尾不是 []")
            return ""
        # JSON 反序列化
        tooltips = json.loads(arr_text)
        if not isinstance(tooltips, list):
            print("      · ReplacedTooltips 解析结果不是列表类型")
            return ""
        # 优先只保留中文句子
        zh_list = [s.strip() for s in tooltips if isinstance(s, str) and is_chinese(s)]
        if zh_list:
            return "\n".join(zh_list)
        # 兜底：全拼
        clean_list = [str(s).strip() for s in tooltips if str(s).strip()]
        return "\n".join(clean_list)
    except Exception as e:
        # 打印异常，便于在终端看到具体错误原因
        print(f"      · ReplacedTooltips 解析异常: {e}")
        return ""


def get_card_description(driver, card_url, card_type='item'):
    """访问卡片详情页获取描述和尺寸
    
    使用Selenium直接定位元素，提取：
    - 冷却时间：从 div._bF 结构提取
    - 效果描述：从卡片主区域内的 div._bK > div._bL > div._b8 > div._cb 提取
    - 排除附魔区域（在 "Enchantments" 标题之后的所有内容）
    """
    try:
        driver.get(card_url)
        time.sleep(3)  # 等待页面加载
        
        html = driver.page_source
        
        # 提取尺寸信息
        size = extract_card_size(html)
        
        # 优先使用嵌入 JSON 里的 ReplacedTooltips（已经是干净的中文描述）
        desc_from_json = extract_description_from_replaced_tooltips(html)
        if desc_from_json:
            return desc_from_json, size
        else:
            print("      · ReplacedTooltips 中未提取到描述，回退到旧逻辑")

        # 判断当前页面语言
        is_chinese_page = '/zh-CN' in card_url
        
        description = ""
        desc_parts = []
        
        try:
            # ---------- 第一步：提取冷却时间 ----------
            # 查找包含冷却时间的 div._bF 结构
            cooldown_elements = driver.find_elements(By.CSS_SELECTOR, 'div._bF')
            for cooldown_elem in cooldown_elements:
                try:
                    cooldown_text = cooldown_elem.text.strip()
                    if cooldown_text and ('秒' in cooldown_text or 'sec' in cooldown_text.lower()):
                        # 提取数字：格式如 "7.0 » 6.0 秒" 或 "7.0/6.0 sec"
                        numbers = re.findall(r'([0-9\.]+)', cooldown_text)
                        if len(numbers) >= 2:
                            cd1, cd2 = numbers[0], numbers[1]
                            if is_chinese_page:
                                desc_parts.append(f"{cd1} » {cd2} 秒")
                            else:
                                desc_parts.append(f"Every {cd1}/{cd2} sec")
                            break
                except:
                    continue
            
            # ---------- 第二步：找到主区域的结束位置（附魔区域之前） ----------
            # 查找 "Enchantments" 标题，主区域在这之前
            enchantments_elements = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Enchantments') or contains(text(), '附魔')]")
            main_section_end_y = None
            if enchantments_elements:
                try:
                    main_section_end_y = enchantments_elements[0].location['y']
                except:
                    pass
            
            # ---------- 第三步：提取效果描述（从 div._bK > div._bL > div._b8 > div._cb） ----------
            # 查找所有 div._cb 元素（效果描述容器）
            cb_elements = driver.find_elements(By.CSS_SELECTOR, 'div._cb')
            
            valid_effects = []
            for cb_elem in cb_elements:
                try:
                    # 检查是否在附魔区域之后
                    if main_section_end_y is not None:
                        elem_y = cb_elem.location.get('y', 0)
                        if elem_y > main_section_end_y:
                            continue
                    
                    # 获取文本内容
                    effect_text = cb_elem.text.strip()
                    
                    # 过滤掉明显不是描述的文本
                    if not effect_text or len(effect_text) < 3:
                        continue
                    
                    # 过滤技术字段
                    technical_keywords = [
                        'ApplyAmount', 'CooldownMax', 'ChargeTargets',
                        'Custom_', 'FlatCooldownReduction', 'When this item is used',
                        'ShieldApplyAmount', 'HealAmount', 'PoisonApplyAmount',
                        'DamageAmount', 'ChargeAmount'
                    ]
                    if any(tk in effect_text for tk in technical_keywords):
                        continue
                    
                    # 过滤元数据
                    meta_keywords = ['Offered by', 'Dropped by', 'Found in',
                                    'TYPES', 'TAGS', 'COST', 'VALUE', 'HISTORY',
                                    'See', 'enchantments', 'hidden abilities', 'merchants']
                    if any(mk in effect_text for mk in meta_keywords):
                        continue
                    
                    # 过滤掉只包含数字或符号的文本
                    if re.match(r'^[\d\s»/\.]+$', effect_text):
                        continue
                    
                    # 语言检查
                    if is_chinese_page:
                        # 中文页：只保留包含中文的文本
                        if is_chinese(effect_text):
                            valid_effects.append(effect_text)
                    else:
                        # 英文页：只保留英文文本，排除中文
                        if not is_chinese(effect_text) and len(effect_text) > 10:
                            valid_effects.append(effect_text)
                            
                except Exception as e:
                    continue
            
            # 合并效果描述
            if valid_effects:
                if is_chinese_page:
                    desc_parts.extend(valid_effects)
                else:
                    # 英文页：通常只有1-2个效果描述
                    desc_parts.extend(valid_effects[:2])
            
            # 组合最终描述
            if desc_parts:
                if is_chinese_page:
                    description = '\n'.join(desc_parts)
                else:
                    description = ': '.join(desc_parts) if len(desc_parts) > 1 else desc_parts[0]
                    
        except Exception as e:
            # 如果Selenium定位失败，回退到meta description
            pass
        
        # ---------- 第四步：如果还没找到，使用 meta description 作为兜底 ----------
        if not description:
            meta_match = re.search(
                r'<meta[^>]+name="description"[^>]+content="([^"]+)"',
                html
            )
            if not meta_match:
                meta_match = re.search(
                    r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"',
                    html
                )
            
            if meta_match:
                meta_desc = meta_match.group(1)
                # 反转义
                for k, v in [
                    ('&nbsp;', ' '), ('&amp;', '&'), ('&lt;', '<'),
                    ('&gt;', '>'), ('&#x27;', "'"), ('&quot;', '"')
                ]:
                    meta_desc = meta_desc.replace(k, v)
                
                # 提取冷却和效果部分
                # 格式：Every [7.0/6.0] sec.: 造成200伤害 Passive: ...
                m = re.search(r'Every\s*\[([0-9\.]+)/([0-9\.]+)\]\s*sec\.:\s*(.*?)(?:\s+Passive:|\.\s+Patch)', meta_desc)
                if m:
                    cd1, cd2, rest = m.groups()
                    # 清理 "Passive:" 和 "Patch" 信息
                    rest = re.sub(r'\s*Passive:\s*', '', rest)
                    rest = re.sub(r'\s*Patch\s+[0-9\.]+.*', '', rest).strip()
                    
                    if is_chinese_page:
                        # 只保留中文部分
                        chinese_parts = [p.strip() for p in re.split(r'[。\.]', rest) 
                                        if p.strip() and is_chinese(p)]
                        if chinese_parts:
                            description = f"{cd1} » {cd2} 秒\n" + '。'.join(chinese_parts) + '。'
                    else:
                        # 只保留英文部分
                        eng_parts = [p.strip() for p in re.split(r'[\.]', rest)
                                    if p.strip() and not is_chinese(p) and len(p) > 10]
                        if eng_parts:
                            description = f"Every {cd1}/{cd2} sec: " + '. '.join(eng_parts)
        
        return description, size
    except Exception as e:
        print(f"      ✗ 获取卡片信息失败: {e}")
        return "", None

def extract_item_from_search_page(driver, item_card_element):
    """从搜索页面的物品卡片元素中提取信息
    
    Args:
        driver: Selenium WebDriver
        item_card_element: 物品卡片的WebElement
    
    Returns:
        物品数据字典，包含 name, name_zh, description_zh, icon, aspect_ratio, url
    """
    try:
        item_data = {}
        
        # 1. 提取名称（中文）
        try:
            name_elem = item_card_element.find_element(By.CSS_SELECTOR, 'h3, h2, [class*="title"], [class*="name"]')
            name_zh = name_elem.text.strip()
            if name_zh:
                item_data['name_zh'] = name_zh
        except:
            pass
        
        # 2. 提取URL
        try:
            link_elem = item_card_element.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
            item_url = link_elem.get_attribute('href')
            item_data['url'] = item_url
            
            # 从URL提取英文名称
            url_match = re.search(r'/card/[^/]+/([^/\?]+)', item_url)
            if url_match:
                from urllib.parse import unquote
                url_name = unquote(url_match.group(1))
                if not is_chinese(url_name):
                    item_data['name'] = url_name.replace('-', ' ').title()
        except:
            pass
        
        # 3. 提取图标URL
        try:
            img_elem = item_card_element.find_element(By.CSS_SELECTOR, 'img[src*="bazaardb.gg"], img[src*="item"], img[src*="skill"]')
            icon_url = img_elem.get_attribute('src')
            if icon_url:
                # 下载图标
                icon_filename = download_icon(icon_url, item_data.get('name_zh', ''), item_data.get('name', ''))
                if icon_filename:
                    item_data['icon'] = icon_filename
        except:
            pass
        
        # 4. 提取描述（从卡片文本中）
        try:
            # 获取卡片的所有文本
            card_text = item_card_element.text
            
            # 提取冷却时间和效果描述
            desc_lines = []
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            
            # 查找冷却时间行（包含"秒"或"SEC"）
            for i, line in enumerate(lines):
                if '秒' in line or 'SEC' in line.upper():
                    desc_lines.append(line)
                    # 继续提取后面的效果描述（直到遇到附魔标题）
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j]
                        # 如果遇到附魔标题，停止
                        if any(kw in next_line for kw in ['enchantments', '附魔', '12 enchantments', '11 enchantments']):
                            break
                        # 如果遇到元数据，停止
                        if any(kw in next_line for kw in ['TYPES', 'TAGS', 'COST', 'VALUE']):
                            break
                        # 如果是有效描述，添加
                        if len(next_line) > 5 and is_chinese(next_line):
                            desc_lines.append(next_line)
                    break
            
            if desc_lines:
                item_data['description_zh'] = '\n'.join(desc_lines)
        except:
            pass
        
        # 5. 提取尺寸信息（从卡片类名或属性中）
        try:
            # 查找包含尺寸信息的类名或属性
            card_html = item_card_element.get_attribute('outerHTML')
            if 'Large' in card_html or 'large' in card_html.lower():
                item_data['aspect_ratio'] = 1.5
            elif 'Small' in card_html or 'small' in card_html.lower():
                item_data['aspect_ratio'] = 0.5
            else:
                item_data['aspect_ratio'] = 1.0  # 默认Medium
        except:
            item_data['aspect_ratio'] = 1.0
        
        return item_data
        
    except Exception as e:
        print(f"      ✗ 从搜索页面提取失败: {e}")
        return None

def extract_all_items_from_search_page(driver, category='items', include_enchantments=False):
    """从搜索页面直接提取所有物品信息（使用新的JSON提取方法）
    
    Args:
        driver: Selenium WebDriver
        category: 'items' 或 'skills'
        include_enchantments: 是否提取附魔信息（已包含在JSON中）
    
    Returns:
        物品数据列表
    """
    try:
        url = f"https://bazaardb.gg/search?c={category}"
        print(f"访问搜索页面: {url}")
        driver.get(url)
        time.sleep(5)  # 等待页面加载
        
        # 滚动加载所有内容（更激进的策略）
        print("滚动页面加载所有物品...")
        no_change_count = 0
        max_no_change = 3  # 连续3次无变化才停止
        scroll_count = 0
        max_scrolls = 100  # 最多滚动100次
        
        while scroll_count < max_scrolls:
            # 先尝试点击"Load more"按钮（如果有）
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
            
            # 检查是否有新内容加载
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    print(f"  连续 {max_no_change} 次无新内容，停止滚动")
                    break
            else:
                no_change_count = 0  # 重置计数器
            
            scroll_count += 1
            if scroll_count % 10 == 0:
                print(f"  已滚动 {scroll_count} 次...")
        
        # 等待最后的内容加载
        print("  等待内容加载完成...")
        time.sleep(5)
        
        # 从页面HTML中提取所有物品的完整JSON数据
        html = driver.page_source
        
        # 查找所有 pageCards 数据并直接提取完整信息
        all_cards_data = []
        search_pos = 0
        
        while True:
            # 查找 initialData
            init_pos = html.find('initialData', search_pos)
            if init_pos == -1:
                break
            
            # 在 initialData 区域内查找 pageCards
            search_area_start = init_pos
            search_area_end = min(len(html), init_pos + 200000)  # 在200k字符内搜索
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
                            # 直接使用这些卡片数据，避免重复访问
                            for card in cards_data:
                                if isinstance(card, dict):
                                    # 使用ID去重，而不是整个对象比较
                                    card_id = card.get('Id', '')
                                    if card_id:
                                        # 检查是否已存在
                                        existing_ids = [c.get('Id', '') for c in all_cards_data]
                                        if card_id not in existing_ids:
                                            all_cards_data.append(card)
                                    else:
                                        # 如果没有ID，使用名称去重
                                        card_name = card.get('_originalTitleText', '') or card.get('Title', {}).get('Text', '')
                                        existing_names = [c.get('_originalTitleText', '') or c.get('Title', {}).get('Text', '') for c in all_cards_data]
                                        if card_name and card_name not in existing_names:
                                            all_cards_data.append(card)
            
            # 继续搜索下一个 initialData
            search_pos = init_pos + 1
        
        print(f"  从HTML中提取到 {len(all_cards_data)} 个物品的完整数据")
        
        print(f"找到 {len(all_cards_data)} 个物品的完整数据")
        
        if not all_cards_data:
            print("  ✗ 未能从页面提取物品数据")
            return []
        
        # 直接解析所有卡片数据
        items_data = []
        for idx, card_json in enumerate(all_cards_data, 1):
            card_name = card_json.get('_originalTitleText', '')
            if not card_name:
                card_name = card_json.get('Title', {}).get('Text', f'Item_{idx}')
            
            print(f"[{idx}/{len(all_cards_data)}] {card_name}")
            
            try:
                # 解析JSON数据
                parsed_data = parse_card_json_data(card_json)
                if not parsed_data:
                    continue
                
                # 下载图标
                icon_filename = ""
                if parsed_data.get('icon_url'):
                    icon_filename = download_icon(parsed_data['icon_url'], parsed_data.get('name', card_name))
                
                # 构建卡片数据
                card_data = {
                    "name": parsed_data.get('name', card_name),
                    "name_zh": parsed_data.get('name_zh', ''),
                    "description_zh": parsed_data.get('description_zh', ''),
                    "icon": icon_filename,
                    "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
                    "url": f"https://bazaardb.gg/card/{parsed_data.get('name', card_name).replace(' ', '-')}"
                }
                
                # 添加附魔信息
                if parsed_data.get('enchantments'):
                    enchantments_text = []
                    for enchant in parsed_data['enchantments']:
                        enchant_line = enchant['name']
                        if enchant.get('description'):
                            enchant_line += f"\n{enchant['description']}"
                        enchantments_text.append(enchant_line)
                    
                    if enchantments_text:
                        card_data['enchantments'] = '\n\n'.join(enchantments_text)
                
                items_data.append(card_data)
                
                # 每10个显示一次进度
                if idx % 10 == 0:
                    print(f"  已处理 {idx}/{len(all_cards_data)} 个物品")
                
            except Exception as e:
                print(f"  ✗ 处理 {card_name} 失败: {e}")
                continue
        
        print(f"成功提取 {len(items_data)} 个物品")
        return items_data
        
    except Exception as e:
        print(f"✗ 从搜索页面提取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def extract_card_names_from_detail_page(driver, html_content, original_card_name):
    """从详情页HTML中提取中英文名称"""
    names = {'name': '', 'name_zh': ''}
    
    # 方法1: 从URL中提取名称（这是最可靠的方法）
    current_url = driver.current_url
    url_match = re.search(r'/card/[^/]+/([^/\?]+)', current_url)
    if url_match:
        url_name = url_match.group(1)
        # URL解码
        from urllib.parse import unquote
        decoded_name = unquote(url_name)
        # 移除/zh-CN等后缀
        if '/zh-CN' in decoded_name:
            decoded_name = decoded_name.replace('/zh-CN', '').strip()
        if decoded_name:
            if is_chinese(decoded_name):
                names['name_zh'] = decoded_name
            else:
                # 英文名称：将连字符替换为空格，并首字母大写
                # 例如：Beehive, Parts-Picker -> Parts Picker
                names['name'] = decoded_name.replace('-', ' ').title()
    
    # 方法2: 从页面标题中提取（<h1>或title标签）
    h1_pattern = r'<h1[^>]*>(.*?)</h1>'
    h1_match = re.search(h1_pattern, html_content, re.DOTALL)
    if h1_match:
        title_text = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        if title_text:
            if is_chinese(title_text):
                names['name_zh'] = title_text
            elif not names['name']:
                names['name'] = title_text
    
    # 方法3: 从title标签中提取（包含语言切换信息）
    title_pattern = r'<title[^>]*>(.*?)</title>'
    title_match = re.search(title_pattern, html_content, re.DOTALL)
    if title_match:
        title_text = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        # 提取标题中的物品名称（通常在"-"之前）
        if '-' in title_text:
            item_name = title_text.split('-')[0].strip()
            if item_name:
                if is_chinese(item_name):
                    if not names['name_zh']:
                        names['name_zh'] = item_name
                elif not names['name']:
                    names['name'] = item_name
    
    # 方法4: 从页面文本中提取（查找最明显的大标题）
    try:
        page_text = driver.execute_script("return document.body.innerText;")
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        for line in lines[:20]:  # 检查前20行
            if len(line) < 50 and len(line) > 1:  # 标题通常较短
                # 跳过明显不是名称的文本（包括快捷键、日期等）
                skip_patterns = ['Info', 'Merchants', 'History', 'Items', 'Skills', 'The Bazaar', 
                                'Ctrl+K', 'Ctrl+', 'Ctrl', 'Search', 'Filters', 'All >',
                                'Dec ', 'Jan ', 'Feb ', 'Mar ', 'Apr ', 'May ', 'Jun ',
                                'Jul ', 'Aug ', 'Sep ', 'Oct ', 'Nov ', '2025', '2024']
                if any(skip in line for skip in skip_patterns):
                    continue
                
                # 跳过日期格式（如 "Dec 23, 2025"）
                if re.match(r'^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$', line):
                    continue
                
                if is_chinese(line) and not names['name_zh']:
                    names['name_zh'] = line
                elif not is_chinese(line) and not names['name']:
                    # 确保不是快捷键、命令或日期
                    if (not line.startswith('Ctrl') and 'Ctrl' not in line and
                        not re.match(r'^[A-Z][a-z]{2}\s+\d', line)):  # 不是日期格式
                        names['name'] = line
                if names['name'] and names['name_zh']:
                    break
    except:
        pass
    
    # 方法5: 如果英文名称仍为空，使用原始名称（如果它是英文）
    if not names['name'] and original_card_name:
        if not is_chinese(original_card_name):
            # 确保原始名称不是快捷键
            if 'Ctrl' not in original_card_name and original_card_name != 'Ctrl+K':
                names['name'] = original_card_name
    
    return names

def extract_card_data_from_search_page(driver, card_name, category='items'):
    """
    从搜索页面提取物品/技能的完整JSON数据
    
    URL格式: https://bazaardb.gg/search?q={英文名}&c={category}
    从页面HTML中提取 initialData.pageCards[0] 的JSON数据
    
    Returns:
        dict: 包含所有卡片数据的字典，如果失败返回None
    """
    try:
        # 构建搜索URL（必须是英文名）
        search_url = f"https://bazaardb.gg/search?q={card_name.replace(' ', '+')}&c={category}"
        driver.get(search_url)
        time.sleep(3)  # 等待页面加载
        
        html = driver.page_source
        
        # 查找 initialData.pageCards 的JSON数据
        # 方法：先找到 "initialData"，然后找到其中的 "pageCards"
        initial_data_key = 'initialData'
        init_pos = html.find(initial_data_key)
        
        if init_pos == -1:
            print(f"      ✗ 未找到 initialData 关键字")
            return None
        
        # 从 initialData 位置开始查找 pageCards
        search_start = init_pos
        search_end = min(len(html), init_pos + 50000)  # 在 initialData 后50k字符内搜索
        search_area = html[search_start:search_end]
        
        # 在搜索区域内查找 pageCards
        pagecards_key = 'pageCards'
        key_pos_in_area = search_area.find(pagecards_key)
        
        if key_pos_in_area == -1:
            print(f"      ✗ 在 initialData 区域内未找到 pageCards")
            # 打印调试信息
            print(f"      · initialData 位置: {init_pos}")
            print(f"      · 搜索区域前500字符: {search_area[:500]}")
            return None
        
        # 计算在完整HTML中的位置
        key_pos = search_start + key_pos_in_area
        
        # 从 pageCards 后面找到第一个 '['
        bracket_start = html.find('[', key_pos)
        if bracket_start == -1:
            print(f"      ✗ 未找到数组开始标记")
            return None
        
        # 手动匹配括号深度
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
        
        if bracket_end == -1:
            print(f"      ✗ 无法匹配完整的JSON数组")
            return None
        
        # 提取完整的JSON数组字符串
        full_json_str = html[bracket_start:bracket_end + 1]
        
        # 调试：打印提取的JSON字符串前200字符
        print(f"      · 提取的JSON前200字符: {full_json_str[:200]}...")
        
        # 如果JSON字符串被转义了（包含 \"），需要先解码
        # 检查是否包含转义字符
        if '\\"' in full_json_str or '\\n' in full_json_str:
            # 尝试解码转义字符
            try:
                # 使用 eval 或者 ast.literal_eval 来解码（但更安全的是手动处理）
                # 先尝试直接解析
                pass
            except:
                pass
        
        # 解析JSON
        try:
            cards_data = json.loads(full_json_str)
            if not isinstance(cards_data, list) or len(cards_data) == 0:
                print(f"      ✗ pageCards 数据格式错误: 不是数组或为空")
                return None
            
            # 返回第一个卡片的数据
            print(f"      ✓ 成功提取卡片数据")
            return cards_data[0]
        except json.JSONDecodeError as e:
            print(f"      ✗ JSON解析失败: {e}")
            print(f"      JSON片段前500字符: {full_json_str[:500]}...")
            # 尝试处理转义字符
            try:
                # 如果JSON被转义，尝试解码
                import ast
                decoded_str = ast.literal_eval(f'"{full_json_str}"')
                cards_data = json.loads(decoded_str)
                if isinstance(cards_data, list) and len(cards_data) > 0:
                    print(f"      ✓ 通过转义解码成功提取")
                    return cards_data[0]
            except:
                pass
            return None
            
    except Exception as e:
        print(f"      ✗ 提取卡片数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_card_json_data(card_json):
    """
    解析从搜索页面提取的JSON数据，生成完整的卡片信息
    
    Args:
        card_json: 从 initialData.pageCards[0] 提取的JSON对象
    
    Returns:
        dict: 包含 name, name_zh, description_zh, icon_url, size, enchantments 等字段
    """
    try:
        result = {
            'name': '',
            'name_zh': '',
            'description_zh': '',
            'icon_url': '',
            'size': None,
            'enchantments': []
        }
        
        # 1. 提取名称
        if 'Title' in card_json and 'Text' in card_json['Title']:
            result['name_zh'] = card_json['Title']['Text']
        
        if '_originalTitleText' in card_json:
            result['name'] = card_json['_originalTitleText']
        
        # 2. 提取图标URL
        if 'Art' in card_json:
            result['icon_url'] = card_json['Art']
        
        # 3. 提取尺寸
        if 'Size' in card_json:
            result['size'] = card_json['Size']
        
        # 4. 提取描述（需要处理 Tooltips 和 TooltipReplacements）
        if 'Tooltips' in card_json and 'TooltipReplacements' in card_json:
            tooltips = card_json['Tooltips']
            replacements = card_json['TooltipReplacements']
            cooldown_max = card_json.get('BaseAttributes', {}).get('CooldownMax', 0)
            
            # 构建描述文本
            desc_lines = []
            
            # 添加冷却时间（如果有）
            if cooldown_max > 0:
                cooldown_sec = cooldown_max / 1000.0
                desc_lines.append(f"{cooldown_sec:.1f}")
                desc_lines.append("秒")
            
            # 处理每个Tooltip
            for tooltip in tooltips:
                if 'Content' in tooltip and 'Text' in tooltip['Content']:
                    text = tooltip['Content']['Text']
                    
                    # 替换占位符
                    # 例如: "{ability.0}" -> 从 replacements 中查找对应的值
                    for key, value_dict in replacements.items():
                        if key in text:
                            # 处理 Fixed 值
                            if 'Fixed' in value_dict:
                                text = text.replace(key, str(value_dict['Fixed']))
                            # 处理 Tier 值（Silver/Gold/Diamond）- 显示为范围
                            elif 'Silver' in value_dict:
                                silver_val = value_dict['Silver']
                                gold_val = value_dict.get('Gold', silver_val)
                                diamond_val = value_dict.get('Diamond', gold_val)
                                if silver_val == gold_val == diamond_val:
                                    text = text.replace(key, str(silver_val))
                                else:
                                    text = text.replace(key, f"{silver_val} » {gold_val} » {diamond_val}")
                    
                    # 只保留中文描述
                    if is_chinese(text) and len(text.strip()) > 3:
                        desc_lines.append(text.strip())
            
            if desc_lines:
                result['description_zh'] = '\n'.join(desc_lines)
        
        # 5. 提取附魔信息
        if 'Enchantments' in card_json:
            enchantments = card_json['Enchantments']
            
            # 检查 Enchantments 的类型（可能是 None、字符串或字典）
            if not enchantments or not isinstance(enchantments, dict):
                # 如果不是字典（可能是 None 或字符串），跳过
                pass
            else:
                # 附魔名称映射（英文 -> 中文）
                enchant_name_map = {
                    'Golden': '黄金',
                    'Heavy': '沉重',
                    'Icy': '寒冰',
                    'Turbo': '疾速',
                    'Shielded': '护盾',
                    'Restorative': '回复',
                    'Toxic': '毒性蔓延',
                    'Fiery': '炽焰',
                    'Shiny': '闪亮',
                    'Radiant': '辉耀',
                    'Deadly': '致命',
                    'Obsidian': '黑曜石'
                }
                
                for enchant_key, enchant_data in enchantments.items():
                    enchant_info = {
                        'name': enchant_name_map.get(enchant_key, enchant_key),
                        'description': ''
                    }
                    
                    # 提取附魔描述
                    if 'Localization' in enchant_data and 'Tooltips' in enchant_data['Localization']:
                        tooltips = enchant_data['Localization']['Tooltips']
                        if tooltips and len(tooltips) > 0:
                            if 'Content' in tooltips[0] and 'Text' in tooltips[0]['Content']:
                                desc_text = tooltips[0]['Content']['Text']
                                
                                # 处理占位符替换
                                if 'TooltipReplacements' in enchant_data:
                                    for key, value_dict in enchant_data['TooltipReplacements'].items():
                                        if key in desc_text:
                                            if 'Fixed' in value_dict:
                                                desc_text = desc_text.replace(key, str(value_dict['Fixed']))
                                
                                enchant_info['description'] = desc_text
                    
                    # 如果有额外的标签（如 +Weapon）
                    if 'DisplayTags' in enchant_data and enchant_data['DisplayTags']:
                        tags = ' +'.join(enchant_data['DisplayTags'])
                        if tags:
                            enchant_info['name'] += f" +{tags}"
                    
                    result['enchantments'].append(enchant_info)
        
        return result
        
    except Exception as e:
        print(f"      ✗ 解析JSON数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_card(driver, card_name, card_type='item', existing_data=None):
    """处理单个卡片（参考 extract_monster_details 的逻辑）
    
    Args:
        driver: Selenium WebDriver
        card_name: 卡片名称
        card_type: 'item' 或 'skill'
        existing_data: 已有的卡片数据（用于智能覆盖）
    
    Returns:
        卡片数据字典
    """
    try:
        # 检查driver是否有效
        try:
            driver.current_url
        except:
            print(f"      ✗ 浏览器会话已失效")
            ERROR_LOG['failed_items'].append({
                'card': card_name,
                'error': 'Browser session invalid'
            })
            return None
        
        # 步骤1: 从搜索页面提取JSON数据
        category = 'items' if card_type == 'item' else 'skills'
        card_json = extract_card_data_from_search_page(driver, card_name, category)
        
        if not card_json:
            print(f"      ✗ 未找到卡片数据")
            ERROR_LOG['missing_detail_urls'].append({
                'card': card_name,
                'type': card_type
            })
            if existing_data:
                return existing_data
            return None
        
        # 步骤2: 解析JSON数据
        parsed_data = parse_card_json_data(card_json)
        if not parsed_data:
            print(f"      ✗ 解析卡片数据失败")
            if existing_data:
                return existing_data
            return None
        
        # 步骤3: 下载图标
        icon_filename = ""
        if parsed_data.get('icon_url'):
            icon_filename = download_icon(parsed_data['icon_url'], parsed_data.get('name', card_name))
            if not icon_filename:
                print(f"      ✗ 图标下载失败")
                ERROR_LOG['failed_icon_downloads'].append({
                    'card': card_name,
                    'type': card_type,
                    'url': parsed_data.get('icon_url', ''),
                    'reason': 'Download failed'
                })
        
        # 步骤4: 构建卡片数据
        card_data = {
            "name": parsed_data.get('name', card_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename,
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": f"https://bazaardb.gg/card/{card_name.replace(' ', '-')}"  # 构建URL
        }
        
        # 步骤5: 添加附魔信息（如果有）
        if parsed_data.get('enchantments'):
            enchantments_text = []
            for enchant in parsed_data['enchantments']:
                enchant_line = enchant['name']
                if enchant.get('description'):
                    enchant_line += f"\n{enchant['description']}"
                enchantments_text.append(enchant_line)
            
            if enchantments_text:
                card_data['enchantments'] = '\n\n'.join(enchantments_text)
        
        # 步骤6: 如果已有数据，进行智能合并
        if existing_data:
            # 保留已有的手动修正
            if existing_data.get('name_zh') and not card_data.get('name_zh'):
                card_data['name_zh'] = existing_data['name_zh']
            if existing_data.get('description_zh') and not card_data.get('description_zh'):
                card_data['description_zh'] = existing_data['description_zh']
            # 保留已有的图标（如果新下载失败）
            if not icon_filename and existing_data.get('icon'):
                card_data['icon'] = existing_data['icon']
        
        # 步骤7: 检查关键字段
        if not card_data.get('description_zh'):
            print(f"      ✗ 描述提取失败")
            ERROR_LOG['failed_descriptions'].append({
                'card': card_name,
                'type': card_type
            })
        
        if not card_data.get('name') or not card_data.get('name_zh'):
            if not card_data.get('name'):
                print(f"      ✗ 英文名称提取失败")
            if not card_data.get('name_zh'):
                print(f"      ✗ 中文名称提取失败")
        
        return card_data
    
    except Exception as e:
        print(f"      ✗ 处理出错: {e}")
        ERROR_LOG['failed_items'].append({
            'card': card_name,
            'error': str(e)
        })
        return None

def save_data(data, output_file):
    """保存数据到JSON文件（统一保存到data/Json目录）"""
    # 确保输出目录存在
    NEW_JSON_DIR.mkdir(parents=True, exist_ok=True)
    output_path = NEW_JSON_DIR / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_existing_data(output_file):
    """加载已处理的卡片数据（如果存在）"""
    output_path = NEW_JSON_DIR / output_file
    if output_path.exists():
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def main():
    """主函数（参考 selenium_monster_v3.py 的 main）"""
    import sys
    
    # 测试模式：只处理前10个
    TEST_MODE = '--test' in sys.argv or '-t' in sys.argv
    TEST_LIMIT = 10
    
    # 搜索页面模式：直接从搜索页面提取（更快）
    SEARCH_PAGE_MODE = '--search-page' in sys.argv or '--sp' in sys.argv
    
    print("=" * 80)
    if TEST_MODE:
        print(f"物品和技能爬虫 - 测试模式（每个类别前{TEST_LIMIT}个）")
    elif SEARCH_PAGE_MODE:
        print("物品和技能爬虫 - 搜索页面模式（直接从搜索页面提取）")
    else:
        print("物品和技能爬虫 - 完整版（访问详情页）")
    print("=" * 80)
    
    # 启动浏览器
    driver = setup_driver()
    
    try:
        # ========== 搜索页面模式 ==========
        if SEARCH_PAGE_MODE:
            print("\n" + "=" * 80)
            print("从搜索页面提取物品信息...")
            print("=" * 80)
            
            # 提取物品
            items_data = extract_all_items_from_search_page(driver, 'items', include_enchantments=False)
            
            # 保存物品数据
            if items_data:
                # 加载已有数据并合并
                existing_items = load_existing_data('items.json')
                existing_index = {item.get('url', ''): item for item in existing_items}
                
                # 合并数据（新数据覆盖旧数据，但保留已有数据中没有的项）
                merged_items = []
                seen_urls = set()
                
                # 先添加新提取的数据
                for item in items_data:
                    url = item.get('url', '')
                    if url and url not in seen_urls:
                        merged_items.append(item)
                        seen_urls.add(url)
                
                # 再添加已有数据中没有的旧数据
                for item in existing_items:
                    url = item.get('url', '')
                    if url and url not in seen_urls:
                        merged_items.append(item)
                        seen_urls.add(url)
                
                save_data(merged_items, 'items.json')
                print(f"\n✓ 已保存 {len(merged_items)} 个物品到 items.json")
            
            print("\n" + "=" * 80)
            print("从搜索页面提取技能信息...")
            print("=" * 80)
            
            # 提取技能
            skills_data = extract_all_items_from_search_page(driver, 'skills', include_enchantments=False)
            
            # 保存技能数据
            if skills_data:
                # 加载已有数据并合并
                existing_skills = load_existing_data('skills.json')
                existing_index = {skill.get('url', ''): skill for skill in existing_skills}
                
                # 合并数据
                merged_skills = []
                seen_urls = set()
                
                for skill in skills_data:
                    url = skill.get('url', '')
                    if url and url not in seen_urls:
                        merged_skills.append(skill)
                        seen_urls.add(url)
                
                for skill in existing_skills:
                    url = skill.get('url', '')
                    if url and url not in seen_urls:
                        merged_skills.append(skill)
                        seen_urls.add(url)
                
                save_data(merged_skills, 'skills.json')
                print(f"\n✓ 已保存 {len(merged_skills)} 个技能到 skills.json")
            
            print("\n" + "=" * 80)
            print("搜索页面提取完成！")
            print("=" * 80)
            return
        
        # ========== 详情页模式（原有逻辑） ==========
        # 加载物品和技能名称
        item_names = load_card_names(ITEMS_FILE)
        skill_names = load_card_names(SKILLS_FILE)
        
        # 测试模式限制数量
        if TEST_MODE:
            item_names = item_names[:TEST_LIMIT]
            skill_names = skill_names[:TEST_LIMIT]
            print(f"\n测试模式：只处理前 {TEST_LIMIT} 个物品和 {TEST_LIMIT} 个技能")
        
        if not item_names and not skill_names:
            print("错误: 没有找到物品或技能名称")
            print(f"提示: 请先运行 fetch_items_skills_names.py 生成 {ITEMS_FILE} 和 {SKILLS_FILE}")
            return
        
        # 加载已处理的数据
        items_file = 'items.json'
        skills_file = 'skills.json'
        
        items_data = load_existing_data(items_file)
        skills_data = load_existing_data(skills_file)
        
        # 创建已有数据的索引（用于快速查找）
        items_index = {}
        for item in items_data:
            name = item.get('name_zh') or item.get('name', '')
            if name:
                items_index[name] = item
        
        skills_index = {}
        for skill in skills_data:
            name = skill.get('name_zh') or skill.get('name', '')
            if name:
                skills_index[name] = skill
        
        print(f"\n总物品数: {len(item_names)}")
        print(f"已处理物品: {len(items_index)}")
        print(f"待处理物品: {len(item_names) - len(items_index)}")
        
        print(f"\n总技能数: {len(skill_names)}")
        print(f"已处理技能: {len(skills_index)}")
        print(f"待处理技能: {len(skill_names) - len(skills_index)}")
        
        # 处理物品
        # 处理物品
        if item_names:
            print(f"\n{'=' * 80}")
            print("开始处理物品...")
            print("=" * 80)
            
            # 测试模式：强制处理前10个，即使已存在
            if TEST_MODE:
                remaining_items = item_names  # 测试模式：处理所有，不管是否已存在
                print(f"测试模式：强制处理所有 {len(remaining_items)} 个物品（即使已存在）")
            else:
                remaining_items = [name for name in item_names if name not in items_index]
            
            for idx, item_name in enumerate(remaining_items, 1):
                print(f"[{idx}/{len(remaining_items)}] {item_name}")
                
                try:
                    existing_item = items_index.get(item_name)
                    item_data = process_card(driver, item_name, 'item', existing_item)
                    
                    if item_data:
                        if existing_item:
                            # 更新已有数据
                            items_data = [i for i in items_data if (i.get('name_zh') or i.get('name', '')) != item_name]
                        items_data.append(item_data)
                        items_index[item_name] = item_data
                        
                        # 立即保存
                        save_data(items_data, items_file)
                    
                except Exception as e:
                    print(f"  ✗ 处理出错: {e}")
                    ERROR_LOG['failed_items'].append({
                        'card': item_name,
                        'error': str(e)
                    })
                    continue
        
        # 处理技能
        if skill_names:
            print(f"\n{'=' * 80}")
            print("开始处理技能...")
            print("=" * 80)
            
            # 测试模式：强制处理前10个，即使已存在
            if TEST_MODE:
                remaining_skills = skill_names  # 测试模式：处理所有，不管是否已存在
                print(f"测试模式：强制处理所有 {len(remaining_skills)} 个技能（即使已存在）")
            else:
                remaining_skills = [name for name in skill_names if name not in skills_index]
            
            for idx, skill_name in enumerate(remaining_skills, 1):
                print(f"[{idx}/{len(remaining_skills)}] {skill_name}")
                
                try:
                    existing_skill = skills_index.get(skill_name)
                    skill_data = process_card(driver, skill_name, 'skill', existing_skill)
                    
                    if skill_data:
                        if existing_skill:
                            # 更新已有数据
                            skills_data = [s for s in skills_data if (s.get('name_zh') or s.get('name', '')) != skill_name]
                        skills_data.append(skill_data)
                        skills_index[skill_name] = skill_data
                        
                        # 立即保存
                        save_data(skills_data, skills_file)
                    
                except Exception as e:
                    print(f"  ✗ 处理出错: {e}")
                    ERROR_LOG['failed_skills'].append({
                        'card': skill_name,
                        'error': str(e)
                    })
                    continue
        
        # 保存最终结果
        save_data(items_data, items_file)
        save_data(skills_data, skills_file)
        
        # 保存错误日志
        if any(ERROR_LOG.values()):
            from datetime import datetime
            log_file = LOGS_DIR / f'error_log_items_skills_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(ERROR_LOG, f, ensure_ascii=False, indent=2)
            print(f"\n错误日志已保存到: {log_file}")
        
        print(f"\n{'=' * 80}")
        print("爬取完成!")
        print('=' * 80)
        print(f"✓ 物品总数: {len(items_data)}")
        print(f"✓ 技能总数: {len(skills_data)}")
        print(f"✓ 物品数据: {NEW_JSON_DIR / items_file}")
        print(f"✓ 技能数据: {NEW_JSON_DIR / skills_file}")
        
        # 显示错误统计
        if any(ERROR_LOG.values()):
            print(f"\n错误统计:")
            print(f"  失败物品: {len(ERROR_LOG['failed_items'])}")
            print(f"  失败技能: {len(ERROR_LOG['failed_skills'])}")
            print(f"  缺少详情URL: {len(ERROR_LOG['missing_detail_urls'])}")
            print(f"  图标下载失败: {len(ERROR_LOG['failed_icon_downloads'])}")
            print(f"  描述获取失败: {len(ERROR_LOG['failed_descriptions'])}")
    
    except KeyboardInterrupt:
        print("\n\n用户中断，保存当前进度...")
        save_data(items_data, items_file)
        save_data(skills_data, skills_file)
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")

if __name__ == "__main__":
    main()
