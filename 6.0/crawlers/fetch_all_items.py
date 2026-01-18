#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 https://bazaardb.gg/search?c=items 获取所有物品的完整信息

1. 从搜索页获取所有物品清单
2. 逐个访问物品详情页，提取完整信息
3. 下载图标
4. 保存为 items.json 格式

用法:
    python fetch_all_items.py
"""

import argparse
import json
import re
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


BASE_DIR = Path(__file__).resolve().parents[2]
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
ITEMS_DB_JSON = BASE_DIR / 'data' / 'Json' / 'items_db.json'
ICONS_DIR = BASE_DIR / 'data' / 'icon' / 'item'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN = 1.0
RETRIES = 3
SCROLL_PAUSE_TIME = 2.0
MAX_SCROLL_ATTEMPTS = 30


def safe_filename(name):
    """生成安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    name = re.sub(r'\s+', '_', name).strip('_')
    return name[:150]


def setup_driver(headless=True):
    """设置 Chrome 驱动"""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


def scroll_to_load_all(driver, max_attempts=MAX_SCROLL_ATTEMPTS):
    """滚动页面直到加载所有物品"""
    print("📜 开始滚动页面加载所有物品...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    no_change_count = 0
    last_item_count = 0
    
    while scroll_attempts < max_attempts:
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)  # 等待加载
        
        # 检查当前物品数量
        try:
            current_item_count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
            if current_item_count == last_item_count:
                no_change_count += 1
                if no_change_count >= 3:  # 连续3次没有新物品，认为加载完成
                    print(f"✓ 已加载所有内容（滚动 {scroll_attempts + 1} 次，共 {current_item_count} 个物品）")
                    break
            else:
                no_change_count = 0
                last_item_count = current_item_count
        except:
            pass
        
        # 检查页面高度变化
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:
                print(f"✓ 已加载所有内容（滚动 {scroll_attempts + 1} 次）")
                break
        else:
            last_height = new_height
        
        scroll_attempts += 1
        if scroll_attempts % 5 == 0:
            try:
                count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
                print(f"  滚动中... ({scroll_attempts}/{max_attempts}) - 已找到 {count} 个物品")
            except:
                print(f"  滚动中... ({scroll_attempts}/{max_attempts})")
    
    if scroll_attempts >= max_attempts:
        print(f"⚠ 达到最大滚动次数 ({max_attempts})")
        try:
            # 尝试点击"Load more"按钮（如果有）
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more') or contains(text(), '加载更多')]")
                if load_more.is_displayed():
                    print("  💡 发现 'Load more' 按钮，尝试点击...")
                    driver.execute_script("arguments[0].click();", load_more)
                    time.sleep(2)
                    # 继续滚动
                    scroll_to_load_all(driver, max_attempts=10)
            except:
                pass
            
            final_count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
            print(f"⚠ 最终找到 {final_count} 个链接（预期提取 899 个唯一物品）")
        except:
            pass


def extract_item_links(driver):
    """从页面提取所有物品链接"""
    print("🔍 正在提取物品链接...")
    items = []
    
    try:
        # 等待页面加载完成
        time.sleep(2)
        
        # 使用 JavaScript 直接提取链接（改进版本 - 提取所有唯一链接）
        js_code = """
        var items = [];
        var seenUrls = new Set();
        var elements = document.querySelectorAll('a[href*="/card/"]');
        
        console.log('Total elements found:', elements.length);
        
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var href = el.getAttribute('href');
            if (!href) continue;
            
            // 确保 URL 完整
            if (!href.startsWith('http')) {
                href = 'https://bazaardb.gg' + (href.startsWith('/') ? href : '/' + href);
            }
            
            // 规范化 URL（移除查询参数和锚点，用于去重）
            var urlParts = href.split('?');
            var baseUrl = urlParts[0].split('#')[0];
            // 移除末尾斜杠
            baseUrl = baseUrl.replace(/\\/$/, '');
            
            // 跳过重复的 URL
            if (seenUrls.has(baseUrl)) continue;
            
            // 检查是否是物品页面
            // URL格式: /card/{id}/{name}
            // 搜索页 c=items 应该只包含物品，但为保险起见，检查URL格式
            if (baseUrl.includes('/card/')) {
                var parts = baseUrl.split('/card/');
                if (parts.length > 1) {
                    var cardPart = parts[1];
                    // 排除明确是技能或怪物的路径
                    if (!cardPart.includes('/skill') && !cardPart.includes('/monster')) {
                        // 提取物品名称（优先从 h3）
                        var name = '';
                        var h3 = el.querySelector('h3');
                        if (h3) {
                            name = h3.textContent.trim();
                        } else {
                            // 从链接文本提取
                            name = el.textContent.trim().replace(/\\s+/g, ' ');
                        }
                        
                        // 如果还是找不到名称，从 URL 中提取
                        if (!name || name.length < 2) {
                            var nameParts = cardPart.split('/');
                            if (nameParts.length >= 2) {
                                var lastPart = nameParts[nameParts.length - 1];
                                try {
                                    name = decodeURIComponent(lastPart);
                                } catch(e) {
                                    name = lastPart;
                                }
                                name = name.replace(/-/g, ' ').trim();
                            }
                        }
                        
                        // 只要URL符合格式且有名称，就添加（不过滤名称内容）
                        if (name && name.length >= 1) {
                            items.push({
                                name: name,
                                url: baseUrl
                            });
                            seenUrls.add(baseUrl);
                        }
                    }
                }
            }
        }
        return items;
        """
        
        items_list = driver.execute_script(js_code)
        print(f"  ✓ JavaScript 方法提取到 {len(items_list)} 个物品链接")
        
        # 再次去重（按 URL，确保唯一性）
        seen_urls = set()
        unique_items = []
        for item in items_list:
            # 规范化 URL
            clean_url = item['url'].rstrip('/')
            # 提取URL的唯一标识部分（ID+名称部分）
            url_key = clean_url
            if '/card/' in clean_url:
                # 提取 /card/{id}/{name} 部分作为唯一标识
                match = re.search(r'/card/([^/]+/[^/]+)', clean_url)
                if match:
                    url_key = match.group(1)
            
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                item['url'] = clean_url
                unique_items.append(item)
            else:
                # 如果URL重复，但名称不同，可能需要合并或选择更好的名称
                pass
        
        items = unique_items
        
    except Exception as e:
        print(f"  ⚠ JavaScript 方法失败: {e}")
    
    # 如果数量不足，尝试 DOM 方法
    if len(items) < 100:
        try:
            print("  📋 使用方法2: DOM 提取...")
            card_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
            seen_urls = {item['url'] for item in items}
            
            for link in card_links:
                try:
                    href = link.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    
                    if not href.startswith('http'):
                        href = urljoin('https://bazaardb.gg', href)
                    
                    # 提取名称
                    name = None
                    try:
                        h3 = link.find_element(By.TAG_NAME, 'h3')
                        name = h3.text.strip()
                    except (NoSuchElementException, Exception):
                        try:
                            name = link.text.strip()
                        except Exception:
                            pass
                    
                    # 从 URL 提取
                    if not name:
                        url_parts = href.split('/')
                        if len(url_parts) >= 2:
                            name = unquote(url_parts[-1].split('?')[0].split('#')[0]).replace('-', ' ')
                    
                    if name and href:
                        items.append({
                            'name': name,
                            'url': href
                        })
                        seen_urls.add(href)
                
                except Exception:
                    continue
        
        except Exception as e:
            print(f"  ⚠ DOM 方法失败: {e}")
    
    # 最终去重
    seen_urls = set()
    final_items = []
    for item in items:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            final_items.append(item)
    
    print(f"✓ 最终提取到 {len(final_items)} 个唯一物品链接")
    return final_items


def fetch_url(url, retries=RETRIES):
    """获取 URL 内容（带重试）"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise


def extract_item_details(html_content, item_name, driver=None):
    """从 HTML 中提取物品详细信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        'name': item_name,
        'name_zh': '',
        'description_zh': '',
        'icon': '',
        'aspect_ratio': 1.0,
        'url': '',
        'enchantments': ''
    }
    
    # 提取 URL
    canonical = soup.find('link', {'rel': 'canonical'})
    if canonical:
        result['url'] = canonical.get('href', '')
    else:
        og_url = soup.find('meta', {'property': 'og:url'})
        if og_url:
            result['url'] = og_url.get('content', '')
    
    # 提取中文名称
    # 方法1: 从 h1 查找
    h1 = soup.find('h1')
    if h1:
        h1_text = h1.text.strip()
        # 如果包含中文字符，可能是中文名称
        if any('\u4e00' <= c <= '\u9fff' for c in h1_text):
            result['name_zh'] = h1_text
    
    # 方法2: 从 meta description 提取
    if not result['name_zh']:
        meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
        if meta_match:
            desc = meta_match.group(1)
            # 格式可能是: "Name (name_zh). Description..." 或 "name_zh. Description..."
            match = re.search(r'[\(（]([^)）]+)[\)）]', desc)
            if match:
                result['name_zh'] = match.group(1).strip()
    
    # 提取描述 - 优先使用 Selenium 获取完整页面文本
    if driver:
        try:
            # 获取渲染后的页面所有文本
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            # 查找描述区域（通常在物品名称之后，附魔之前）
            description_lines = []
            in_description = False
            skip_keywords = ['Offered by', 'Dropped by', 'Found in', 'Level', 'Day', 'Enchantments', 'Tier', 'Size', 'Types', 'Tags']
            
            for i, line in enumerate(lines):
                # 跳过标题和导航
                if any(skip in line for skip in ['All', 'Items', 'Skills', 'Monsters', 'Heroes', 'Database', 'Privacy Policy']):
                    continue
                
                # 检查是否是描述开始（包含游戏术语且不在跳过列表中）
                if (not in_description and 
                    len(line) > 5 and 
                    any(keyword in line for keyword in ['Deal', 'Gain', 'When', 'Shield', 'Damage', 'Heal', 'Haste', 'Slow', 'Poison', 'Burn', 'Charge', 'Cooldown', 'Max Health', 'Regen', 'Freeze', 'Destroy', 'SEC', '秒', '造成', '获得', '使用', '伤害', '治疗', '护盾', '充能', '冷却'])):
                    if not any(skip in line for skip in skip_keywords):
                        in_description = True
                        description_lines.append(line)
                # 继续收集描述行
                elif in_description:
                    # 如果遇到附魔或结束标识，停止收集
                    if any(stop in line for stop in ['Enchantments', 'enchantments', 'Golden', 'Heavy', 'Icy', 'Turbo', '黄金', '沉重', '寒冰', '疾速']):
                        # 但如果只是包含这些词但不明显是附魔标题，继续收集
                        if not (line.startswith('Golden') or line.startswith('Heavy') or line.startswith('黄金') or line.startswith('沉重')):
                            description_lines.append(line)
                        else:
                            break
                    # 空行分隔不同的描述部分，保留
                    elif not line:
                        if description_lines:  # 如果已有描述行，添加空行
                            description_lines.append('')
                    # 继续收集描述文本
                    elif len(line) > 2 and len(line) < 500:
                        description_lines.append(line)
                    # 如果行太长，可能是其他内容，停止
                    elif len(line) >= 500:
                        break
            
            if description_lines:
                # 清理和合并描述
                clean_lines = []
                for line in description_lines:
                    if line.strip():
                        clean_lines.append(line.strip())
                if clean_lines:
                    result['description_zh'] = '\n'.join(clean_lines)
        
        except Exception as e:
            print(f"        警告: 从页面文本提取描述失败: {e}")
    
    # 备选方法：使用 _bM 类提取（如果 Selenium 方法失败）
    if not result['description_zh']:
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html_content, re.DOTALL)
        if desc_matches:
            valid_descriptions = []
            for desc_html in desc_matches:
                # 清理HTML标签和注释
                desc = re.sub(r'<[^>]+>', '', desc_html)
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
            
            if valid_descriptions:
                result['description_zh'] = '\n'.join(valid_descriptions)
    
    # 提取图标 URL
    icon_patterns = [
        r'https://s\.bazaardb\.gg/v0/[^/]+/item/([a-f0-9]{40})@(\d+)\.webp',
        r'https://s\.bazaardb\.gg[^"\'<>]+item[^"\'<>]+\.webp',
    ]
    for pattern in icon_patterns:
        match = re.search(pattern, html_content)
        if match:
            if len(match.groups()) == 2:
                # 格式: hash@size
                icon_hash = match.group(1)
                icon_size = match.group(2)
                result['icon_url'] = f"https://s.bazaardb.gg/v0/z10.0/item/{icon_hash}@256.webp?v=0"
            else:
                result['icon_url'] = match.group(0)
            break
    
    # 提取附魔信息 - 查找包含附魔描述的 div
    enchantments_list = []
    
    # 方法1: 查找包含 "enchantment" 或附魔关键词的区域
    enchant_sections = soup.find_all('div', class_=lambda x: x and ('enchant' in str(x).lower() or '_bM' in str(x)) if x else False)
    for section in enchant_sections:
        text = section.get_text(strip=True)
        if any(keyword in text for keyword in ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded', 'Restorative', 'Toxic', 'Fiery', 'Shiny', 'Deadly', 'Radiant', 'Obsidian', '黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '炽焰', '闪亮', '致命', '辉耀', '黑曜石']):
            if len(text) > 15:
                enchantments_list.append(text)
    
    # 方法2: 从页面文本中查找附魔信息（使用 Selenium）
    if not enchantments_list and driver:
        try:
            page_text = driver.execute_script("return document.body.innerText;")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            in_enchantment_section = False
            current_enchantment = []
            
            for line in lines:
                # 检测附魔标题
                if any(keyword in line for keyword in ['Golden', 'Heavy', 'Icy', 'Turbo', '黄金', '沉重', '寒冰', '疾速']) and len(line) < 30:
                    if current_enchantment:
                        enchantments_list.append('\n'.join(current_enchantment))
                    current_enchantment = [line]
                    in_enchantment_section = True
                elif in_enchantment_section:
                    if line and len(line) > 5:
                        current_enchantment.append(line)
                    elif not line and current_enchantment:
                        enchantments_list.append('\n'.join(current_enchantment))
                        current_enchantment = []
                        in_enchantment_section = False
            
            if current_enchantment:
                enchantments_list.append('\n'.join(current_enchantment))
        
        except Exception:
            pass
    
    if enchantments_list:
        result['enchantments'] = '\n\n'.join(enchantments_list)
    
    # 提取长宽比 - 查找卡片尺寸
    size_match = re.search(r'(Small|Medium|Large)', html_content, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).lower()
        size_map = {'small': 0.5, 'medium': 1.0, 'large': 1.5}
        result['aspect_ratio'] = size_map.get(size, 1.0)
    else:
        # 从样式提取
        aspect_patterns = [
            r'aspect-ratio["\']?\s*:\s*([0-9.]+)',
            r'aspectRatio["\']?\s*:\s*([0-9.]+)',
        ]
        for pattern in aspect_patterns:
            match = re.search(pattern, html_content)
            if match:
                try:
                    aspect = float(match.group(1))
                    if 0.5 <= aspect <= 2.0:
                        result['aspect_ratio'] = aspect
                        break
                except ValueError:
                    pass
    
    return result


def download_icon(icon_url, item_name):
    """下载图标"""
    if not icon_url:
        return ''
    
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        filename = safe_filename(item_name) + '.webp'
        filepath = ICONS_DIR / filename
        
        if filepath.exists():
            return filename
        
        response = requests.get(icon_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filename
    except Exception as e:
        print(f"        警告: 下载图标失败: {e}")
        return ''


def get_items_list_from_web(driver=None, use_selenium=True):
    """从网页获取物品列表"""
    search_url = "https://bazaardb.gg/search?c=items"
    
    if use_selenium and driver:
        print(f"🌐 使用 Selenium 访问: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 滚动加载所有物品
        scroll_to_load_all(driver)
        
        # 提取物品链接
        items = extract_item_links(driver)
        return items, driver
    else:
        # 使用 requests（但可能无法加载动态内容）
        print(f"🌐 使用 requests 访问: {search_url}")
        html = fetch_url(search_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        items = []
        seen_urls = set()
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if '/card/' in href and href not in seen_urls:
                if not href.startswith('http'):
                    href = urljoin('https://bazaardb.gg', href)
                
                name = None
                h3 = a.find('h3')
                if h3:
                    name = h3.get_text(strip=True)
                else:
                    name = a.get_text(strip=True)
                
                if not name:
                    url_parts = href.split('/')
                    if len(url_parts) >= 2:
                        name = unquote(url_parts[-1].split('?')[0]).replace('-', ' ')
                
                if name:
                    items.append({
                        'name': name,
                        'url': href
                    })
                    seen_urls.add(href)
        
        return items, None


def normalize_name(name):
    """标准化名称用于比较"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def load_items_db_map():
    """加载 items_db.json 作为参考（用于获取中文名称）"""
    items_db_map = {}
    if ITEMS_DB_JSON.exists():
        try:
            with open(ITEMS_DB_JSON, 'r', encoding='utf-8') as f:
                items_db = json.load(f)
            for uuid, item_db in items_db.items():
                name = item_db.get('name', '')
                if name:
                    normalized = normalize_name(name)
                    items_db_map[normalized] = item_db
            print(f"✓ 已加载 {len(items_db_map)} 个参考物品数据")
        except Exception as e:
            print(f"⚠ 加载 items_db.json 失败: {e}")
    return items_db_map


def fetch_all_items():
    """获取所有物品的完整信息"""
    print("=" * 80)
    print("开始获取所有物品信息")
    print("=" * 80)
    
    # 确保目录存在
    ITEMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载 items_db.json 作为参考
    print("\n正在加载参考数据...")
    items_db_map = load_items_db_map()
    
    driver = None
    try:
        # 步骤1: 获取物品列表
        print("\n步骤 1/2: 从网站获取物品列表...")
        driver = setup_driver(headless=False)
        items_list, driver = get_items_list_from_web(driver, use_selenium=True)
        
        if not items_list:
            print("❌ 未找到任何物品，退出")
            return
        
        total_count = len(items_list)
        print(f"✓ 找到 {total_count} 个物品")
        print(f"📊 统计信息:")
        print(f"  - 提取的物品数: {total_count}")
        print(f"  - 网站统计应有: 899 个")
        if total_count < 899:
            print(f"  ⚠️  缺少 {899 - total_count} 个物品，可能需要增加滚动次数")
        
        # 保存列表到临时文件
        list_file = BASE_DIR / 'data' / 'Json' / 'items_list_from_web.json'
        with open(list_file, 'w', encoding='utf-8') as f:
            json.dump(items_list, f, ensure_ascii=False, indent=2)
        print(f"✓ 物品列表已保存到: {list_file}")
        
        # 测试模式：只处理前10个
        test_count = 10
        print(f"\n⚠️  测试模式：只处理前 {test_count} 个物品（共 {total_count} 个）")
        items_to_process = items_list[:test_count]
        items_list = items_to_process
        
        # 步骤2: 逐个获取物品详情（使用 Selenium 确保获取完整信息）
        print(f"\n步骤 2/2: 获取 {len(items_list)} 个物品的详细信息...")
        all_items = []
        
        for idx, item_info in enumerate(items_list, 1):
            item_name = item_info['name']
            item_url = item_info['url']
            
            print(f"\n[{idx}/{len(items_list)}] {item_name}")
            
            try:
                # 使用 Selenium 访问详情页（确保获取动态内容）
                driver.get(item_url)
                time.sleep(2)  # 等待页面加载
                
                html = driver.page_source
                
                # 提取详细信息（传入 driver 用于提取描述和附魔）
                item_data = extract_item_details(html, item_name, driver=driver)
                
                # 如果没有中文名称，从 items_db.json 中获取
                if not item_data['name_zh'] and items_db_map:
                    normalized = normalize_name(item_name)
                    item_db = items_db_map.get(normalized)
                    if item_db:
                        name_zh = item_db.get('name_zh', '')
                        if name_zh and name_zh != item_name:
                            item_data['name_zh'] = name_zh
                            print(f"  ℹ️  从 items_db.json 获取中文名: {name_zh}")
                
                # 下载图标
                if item_data.get('icon_url'):
                    icon_filename = download_icon(item_data['icon_url'], item_name)
                    if icon_filename:
                        item_data['icon'] = icon_filename
                        print(f"  ✓ 图标: {icon_filename}")
                
                # 设置 URL
                item_data['url'] = item_url
                
                # 移除临时字段
                item_data.pop('icon_url', None)
                
                all_items.append(item_data)
                print(f"  ✓ 完成 (描述: {len(item_data.get('description_zh', ''))} 字符, 附魔: {len(item_data.get('enchantments', ''))} 字符)")
                
                time.sleep(SLEEP_BETWEEN)
            
            except Exception as e:
                print(f"  ✗ 错误: {e}")
                # 即使出错，也创建基本条目
                all_items.append({
                    'name': item_name,
                    'name_zh': '',
                    'description_zh': '',
                    'icon': '',
                    'aspect_ratio': 1.0,
                    'url': item_url,
                    'enchantments': ''
                })
        
        # 按名称排序
        all_items.sort(key=lambda x: x.get('name', ''))
        
        # 保存结果
        print(f"\n正在保存结果到 {ITEMS_JSON}...")
        with open(ITEMS_JSON, 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        # 统计
        items_with_zh = sum(1 for item in all_items if item.get('name_zh'))
        items_with_desc = sum(1 for item in all_items if item.get('description_zh'))
        items_with_icon = sum(1 for item in all_items if item.get('icon'))
        items_with_enchantments = sum(1 for item in all_items if item.get('enchantments'))
        
        print("\n" + "=" * 80)
        print("获取完成")
        print("=" * 80)
        print(f"物品总数: {len(all_items)}")
        print(f"含中文名: {items_with_zh}")
        print(f"含描述: {items_with_desc}")
        print(f"含图标: {items_with_icon}")
        print(f"含附魔: {items_with_enchantments}")
        print(f"输出文件: {ITEMS_JSON}")
    
    finally:
        if driver:
            driver.quit()
            print("\n✓ 已关闭浏览器")


if __name__ == '__main__':
    fetch_all_items()
