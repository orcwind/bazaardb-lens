#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
以 items_db.json 为基础，补充 items.json 缺失的物品及信息

从网站抓取缺失物品的详细信息（描述、图标、品质等）并补充到 items.json

用法:
    python supplement_items.py
"""

import json
import re
import time
import requests
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
ITEMS_DB_JSON = BASE_DIR / 'data' / 'Json' / 'items_db.json'
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
ICONS_DIR = BASE_DIR / 'data' / 'icon' / 'item'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN = 1.0
RETRIES = 3


def safe_filename(name):
    """生成安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    name = re.sub(r'\s+', '_', name).strip('_')
    return name[:150]


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


def find_item_detail_url(item_name):
    """通过搜索找到物品详情页 URL"""
    search_url = f"https://bazaardb.gg/search?q={quote(item_name)}&c=items"
    try:
        html = fetch_url(search_url)
        # 查找第一个 /card/ 链接
        match = re.search(r'href="(/card/[^"]+)"', html)
        if match:
            return f"https://bazaardb.gg{match.group(1)}"
    except Exception:
        pass
    return None


def extract_item_details(html_content, item_name):
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
    
    # 提取中文名称
    # 方法1: 从 h1 查找（如果包含中文）
    h1 = soup.find('h1')
    if h1:
        h1_text = h1.text.strip()
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
    
    # 提取描述
    # 查找所有 _bq 类的 div（通常是描述文本）
    desc_divs = soup.find_all('div', class_=lambda x: x and '_bq' in str(x) if x else False)
    descriptions = []
    for div in desc_divs:
        text = div.get_text(strip=True)
        # 过滤掉太短的文本和明显的导航/标题文本
        if text and len(text) > 15 and not text.startswith(('All', 'Items', 'Skills', 'Monsters')):
            # 如果包含数字或中文，更可能是描述
            if re.search(r'[\d\u4e00-\u9fff]', text):
                descriptions.append(text)
    
    # 通常第一个较长的描述是物品描述
    if descriptions:
        result['description_zh'] = descriptions[0]
    
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
    
    # 提取 URL
    canonical = soup.find('link', {'rel': 'canonical'})
    if canonical:
        result['url'] = canonical.get('href', '')
    else:
        og_url = soup.find('meta', {'property': 'og:url'})
        if og_url:
            result['url'] = og_url.get('content', '')
    
    # 提取附魔信息
    enchantments_list = []
    # 查找所有包含附魔名称的文本块
    # 附魔通常在特定的 div 结构中
    enchant_keywords = ['黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '炽焰', 
                       '闪亮', '致命', '辉耀', '黑曜石', 'Golden', 'Heavy', 'Icy', 'Turbo']
    
    # 查找包含附魔关键词的 div
    for div in soup.find_all('div'):
        text = div.get_text(strip=True)
        if any(keyword in text for keyword in enchant_keywords):
            # 检查是否包含附魔的完整描述（通常有换行或特殊格式）
            if len(text) > 20 and ('\n' in text or '。' in text or '，' in text):
                enchantments_list.append(text)
    
    if enchantments_list:
        result['enchantments'] = '\n\n'.join(enchantments_list)
    
    # 提取长宽比
    # 查找 aspect-ratio 相关的样式
    aspect_patterns = [
        r'aspect-ratio["\']?\s*:\s*([0-9.]+)',
        r'aspectRatio["\']?\s*:\s*([0-9.]+)',
    ]
    for pattern in aspect_patterns:
        match = re.search(pattern, html_content)
        if match:
            try:
                aspect = float(match.group(1))
                if 0.5 <= aspect <= 2.0:  # 合理的范围
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
        # 从 URL 提取文件名或使用物品名称
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


def normalize_name(name):
    """标准化名称用于比较"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def find_missing_items():
    """找出 items.json 中缺失的物品"""
    # 加载 items_db.json
    with open(ITEMS_DB_JSON, 'r', encoding='utf-8') as f:
        items_db = json.load(f)
    
    # 加载 items.json
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    # 构建名称集合（标准化）
    items_names = {normalize_name(item['name']): item for item in items if 'name' in item}
    
    # 找出缺失的物品
    missing_items = []
    for uuid, item_db in items_db.items():
        name = item_db.get('name', '')
        if not name:
            continue
        
        normalized = normalize_name(name)
        if normalized not in items_names:
            # 过滤掉 DEBUG 和模板物品
            if '[DEBUG]' not in name and '[SMALL ITEM TEMPLATE]' not in name:
                missing_items.append({
                    'uuid': uuid,
                    'name': name,
                    'name_zh': item_db.get('name_zh', ''),
                    'item_db': item_db
                })
    
    return missing_items, items


def supplement_items():
    """补充缺失的物品"""
    print("=" * 80)
    print("开始补充缺失的物品")
    print("=" * 80)
    
    # 找出缺失的物品
    print("\n正在查找缺失的物品...")
    missing_items, existing_items = find_missing_items()
    print(f"找到 {len(missing_items)} 个缺失的物品")
    
    if not missing_items:
        print("\n✓ 没有缺失的物品！")
        return
    
    # 显示缺失的物品列表
    print("\n缺失的物品列表:")
    for idx, item in enumerate(missing_items[:10], 1):
        print(f"  {idx}. {item['name']} ({item['name_zh'] or '无中文名'})")
    if len(missing_items) > 10:
        print(f"  ... 还有 {len(missing_items) - 10} 个")
    
    # 询问是否继续
    print(f"\n是否开始抓取这 {len(missing_items)} 个物品的详细信息？")
    print("按 Enter 继续，或 Ctrl+C 取消...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n已取消")
        return
    
    # 抓取缺失物品的详细信息
    print(f"\n开始抓取物品详细信息...")
    new_items = []
    
    for idx, missing_item in enumerate(missing_items, 1):
        item_name = missing_item['name']
        print(f"\n[{idx}/{len(missing_items)}] {item_name}")
        
        try:
            # 查找详情页 URL
            detail_url = find_item_detail_url(item_name)
            if not detail_url:
                print(f"  ✗ 未找到详情页 URL")
                # 使用 items_db 中的基本信息创建条目
                item_data = {
                    'name': item_name,
                    'name_zh': missing_item['name_zh'] or '',
                    'description_zh': '',
                    'icon': '',
                    'aspect_ratio': 1.0,
                    'url': '',
                    'enchantments': ''
                }
                new_items.append(item_data)
                continue
            
            print(f"  ✓ 找到详情页: {detail_url}")
            
            # 抓取详情页
            html = fetch_url(detail_url)
            
            # 提取详细信息
            item_data = extract_item_details(html, item_name)
            
            # 如果没有中文名称，使用 items_db 中的
            if not item_data['name_zh'] and missing_item['name_zh']:
                item_data['name_zh'] = missing_item['name_zh']
            
            # 下载图标
            if item_data.get('icon_url'):
                icon_filename = download_icon(item_data['icon_url'], item_name)
                if icon_filename:
                    item_data['icon'] = icon_filename
                    print(f"  ✓ 下载图标: {icon_filename}")
            
            # 设置 URL
            item_data['url'] = detail_url
            
            new_items.append(item_data)
            print(f"  ✓ 完成")
            
            time.sleep(SLEEP_BETWEEN)
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            # 即使出错，也使用基本信息创建条目
            item_data = {
                'name': item_name,
                'name_zh': missing_item['name_zh'] or '',
                'description_zh': '',
                'icon': '',
                'aspect_ratio': 1.0,
                'url': '',
                'enchantments': ''
            }
            new_items.append(item_data)
    
    # 合并到现有列表
    print(f"\n正在保存结果...")
    all_items = existing_items + new_items
    
    # 按名称排序
    all_items.sort(key=lambda x: x.get('name', ''))
    
    # 保存
    with open(ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    # 统计
    print("\n" + "=" * 80)
    print("补充完成")
    print("=" * 80)
    print(f"原有物品: {len(existing_items)}")
    print(f"新增物品: {len(new_items)}")
    print(f"总计物品: {len(all_items)}")
    print(f"输出文件: {ITEMS_JSON}")


if __name__ == '__main__':
    supplement_items()
