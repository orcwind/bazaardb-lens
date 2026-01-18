#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二步：从已下载的 HTML 文件中解析物品信息

解析 data/html/item/ 目录下的 HTML 文件
提取：中英文名称、描述、图标、附魔、长宽比等

输出：data/Json/items.json

用法:
    python extract_items_from_html.py
"""

import json
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / 'data' / 'html' / 'item'
INDEX_HTML = BASE_DIR / 'data' / 'html' / 'items_list_page.html'
ITEMS_LIST_JSON = BASE_DIR / 'data' / 'Json' / 'items_list_from_web.json'
ITEMS_DB_JSON = BASE_DIR / 'data' / 'Json' / 'items_db.json'
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
ICONS_DIR = BASE_DIR / 'data' / 'icon' / 'item'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}
REQUEST_TIMEOUT = 15


def safe_filename(name):
    """生成安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    name = re.sub(r'\s+', '_', name).strip('_')
    return name[:150]


def normalize_name(name):
    """标准化名称用于比较"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def format_enchantments_from_db(enchantments_list):
    """将 items_db.json 中的 enchantments 数组格式转换为字符串格式"""
    if not enchantments_list:
        return ''
    
    formatted = []
    for enchant in enchantments_list:
        name = enchant.get('name', '')
        name_en = enchant.get('name_en', '')
        description = enchant.get('description', '')
        
        if name_en and name_en != name:
            enchant_text = f"{name} ({name_en})"
        else:
            enchant_text = name
        
        if description:
            enchant_text += f"\n{description}"
        
        formatted.append(enchant_text)
    
    return '\n\n'.join(formatted)


def load_items_db_map():
    """加载 items_db.json 作为参考（用于获取中文名称和附魔信息）"""
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


def extract_item_details(html_content, item_name, items_db_map):
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
        if any('\u4e00' <= c <= '\u9fff' for c in h1_text):
            result['name_zh'] = h1_text
    
    # 方法2: 从 meta description 提取
    if not result['name_zh']:
        meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
        if meta_match:
            desc = meta_match.group(1)
            match = re.search(r'[\(（]([^)）]+)[\)）]', desc)
            if match:
                result['name_zh'] = match.group(1).strip()
    
    # 方法3: 从 items_db.json 获取
    if not result['name_zh'] and items_db_map:
        normalized = normalize_name(item_name)
        item_db = items_db_map.get(normalized)
        if item_db:
            name_zh = item_db.get('name_zh', '')
            if name_zh and name_zh != item_name:
                result['name_zh'] = name_zh
    
    # 提取描述 - 使用 _bM 类
    desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html_content, re.DOTALL)
    if desc_matches:
        valid_descriptions = []
        for desc_html in desc_matches:
            # 清理HTML标签
            desc = re.sub(r'<[^>]+>', '', desc_html)
            desc = re.sub(r'<!--\s*-->', '', desc)
            # 清理HTML实体
            desc = desc.replace('&nbsp;', ' ')
            desc = desc.replace('&amp;', '&')
            desc = desc.replace('&lt;', '<')
            desc = desc.replace('&gt;', '>')
            desc = desc.replace('&#x27;', "'")
            desc = desc.strip()
            
            # 过滤无效描述
            if (len(desc) > 5 and 
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
                icon_hash = match.group(1)
                result['icon_url'] = f"https://s.bazaardb.gg/v0/z10.0/item/{icon_hash}@256.webp?v=0"
            else:
                result['icon_url'] = match.group(0)
            break
    
    # 提取附魔信息
    enchantments_list = []
    # 查找包含附魔描述的 div
    enchant_sections = soup.find_all('div', class_=lambda x: x and ('enchant' in str(x).lower() or '_bM' in str(x)) if x else False)
    for section in enchant_sections:
        text = section.get_text(strip=True)
        if any(keyword in text for keyword in ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded', 'Restorative', 'Toxic', 'Fiery', 'Shiny', 'Deadly', 'Radiant', 'Obsidian', '黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '炽焰', '闪亮', '致命', '辉耀', '黑曜石']):
            if len(text) > 15:
                enchantments_list.append(text)
    
    if enchantments_list:
        result['enchantments'] = '\n\n'.join(enchantments_list)
    
    # 提取长宽比
    size_match = re.search(r'(Small|Medium|Large)', html_content, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).lower()
        size_map = {'small': 0.5, 'medium': 1.0, 'large': 1.5}
        result['aspect_ratio'] = size_map.get(size, 1.0)
    else:
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


def fetch_description_from_detail_page(item_url):
    """从物品详情页获取描述信息（排除附魔信息）"""
    try:
        # 确保URL包含中文语言参数
        if '?lang=' not in item_url and '&lang=' not in item_url:
            separator = '&' if '?' in item_url else '?'
            item_url = f"{item_url}{separator}lang=zh"
        
        response = requests.get(item_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 附魔关键词（用于过滤）
        enchant_keywords = ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded', 'Restorative', 
                           'Toxic', 'Fiery', 'Shiny', 'Deadly', 'Radiant', 'Obsidian',
                           '黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', 
                           '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
        
        # 描述特征模式（用于识别真正的物品描述）
        description_patterns = [
            r'\d+\.\d+\s*»?\s*\d*\.?\d*\s*秒',  # 冷却时间格式：5.0秒, 9.0»7.0秒, 5.0»6.0»7.0秒
            r'\d+\s*»\s*\d+\s*»\s*\d+',  # 数值范围格式：1 » 2 » 3, 25 » 50 » 100
            r'摧毁|充能|减速|加速|伤害|护盾|治疗|冻结|剧毒|灼烧',
            r'使用.*时|每有.*时|每场战斗中',
            r'相邻|左侧|右侧|最左|最右|另.*件|为.*充能',
            r'多重触发|冷却时间|被摧毁|最左侧|最右侧'
        ]
        
        # 清理函数：移除元数据和附魔信息
        def clean_description(text):
            """清理描述文本，移除元数据和附魔信息"""
            if not text:
                return text
            
            # 移除 Types 标签（如 TypesWeapon, TypesProperty, TypesVehicle 等）
            # 匹配 Types 后跟任意字母（不区分大小写）
            text = re.sub(r'Types[A-Za-z]+\s*', '', text)
            
            # 移除 Ammo: 标签及其数值（包括 Ammo: 2 » 4 或 Ammo: 50 等格式）
            text = re.sub(r'Ammo:\s*\d+\s*(»\s*\d+)*\s*', '', text, flags=re.IGNORECASE)
            
            # 移除 "Can't be enchanted with" 相关文本（中英文）
            # 匹配：附魔名称（中文）+ Can't be enchanted with + 附魔名称（中文）或英文变体
            enchant_zh_names_pattern = '黄金|沉重|寒冰|疾速|护盾|回复|毒性蔓延|毒素|炽焰|闪亮|致命|辉耀|黑曜石'
            # 模式1：中文附魔名称 + Can't be enchanted with + 中文附魔名称
            text = re.sub(rf'({enchant_zh_names_pattern})\s*(Can\'t|can\'t|cannot)\s*be\s*enchanted\s*with\s*({enchant_zh_names_pattern})\.?\s*', '', text, flags=re.IGNORECASE)
            # 模式2：Can't be enchanted with + 中文附魔名称
            text = re.sub(rf'(Can\'t|can\'t|cannot)\s*be\s*enchanted\s*with\s*({enchant_zh_names_pattern})\.?\s*', '', text, flags=re.IGNORECASE)
            # 模式3：中文附魔名称 + 不能附魔/无法附魔/不可附魔 + 中文附魔名称（如果有）
            text = re.sub(rf'({enchant_zh_names_pattern})\s*(不能|无法|不可)\s*附魔\s*({enchant_zh_names_pattern})?\.?\s*', '', text, flags=re.IGNORECASE)
            
            # 移除单独出现的附魔中文名称（前后有空格或标点）
            # 匹配模式：空格或开头 + 附魔名称 + 空格或标点或结尾
            enchant_zh_names = ['黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '毒素', '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
            for name in enchant_zh_names:
                # 移除单独出现的附魔名称（前后是空格、标点或开头结尾）
                text = re.sub(r'(^|\s)' + re.escape(name) + r'(\s|$|\.|，|。|,|\.)', r'\1\2', text)
            
            # 规范化空格：将多个连续空格替换为单个空格
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        
        # 方法1: 优先查找 _bw、_bx、_bC 类的 div（描述文本的主要容器）
        desc_classes = ['_bw', '_bx', '_bC', '_cm']
        descriptions = []
        
        # 先尝试 _bw 或 _bx（通常包含完整的描述，包括冷却时间和条件触发）
        for class_name in ['_bw', '_bx']:
            desc_divs = soup.find_all('div', class_=lambda x: x and class_name in str(x) if x else False)
            for div in desc_divs:
                # 获取原始文本，保留标签间的紧密连接
                text = div.get_text(separator='', strip=False)
                # 将不间断空格 \xa0 转换为普通空格
                text = text.replace('\xa0', ' ')
                # 规范化空格格式：
                # 1. 冷却时间格式（以"秒"结尾，去掉 » 前后的空格）
                #    先处理四个数字的冷却时间（如：8.0 » 7.0 » 6.0 » 5.0秒 -> 8.0»7.0»6.0»5.0秒）
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', text)
                #    再处理三个数字的冷却时间（如：5.0 » 6.0 » 7.0秒 -> 5.0»6.0»7.0秒）
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', text)
                #    最后处理两个数字的冷却时间（如：9.0 » 7.0秒 -> 9.0»7.0秒）
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', text)
                # 2. 其他数值范围（保留 » 前后的单个空格）
                #    先处理四个数字的情况（不以"秒"结尾）
                text = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', text)
                #    再处理三个数字的情况
                text = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', text)
                #    最后处理两个数字且中间没有空格的情况（如 2»3，但不以"秒"结尾）
                text = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', text)
                # 3. 规范化多个连续空格为单个空格（但保留冷却时间格式中的无空格）
                text = re.sub(r' {2,}', ' ', text).strip()
                if len(text) > 10:
                    # 跳过明显不是描述的内容
                    if any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History', 'Offered by', 
                                                      'Dropped by', 'Found in', 'Level', 'Day']):
                        continue
                    
                    # 检查是否包含附魔标识符（❯符号）或过多的附魔关键词
                    has_enchant_symbol = '❯' in text or '→' in text
                    enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
                    
                    # 如果包含附魔标识符或过多附魔关键词，跳过
                    if has_enchant_symbol or enchant_count >= 2:
                        continue
                    
                    # 检查是否包含描述特征（冷却时间、数值范围、效果关键词）
                    has_desc_pattern = any(re.search(pattern, text) for pattern in description_patterns)
                    
                    # 或者包含效果关键词（即使没有数值格式）
                    has_effect_keywords = any(keyword in text for keyword in [
                        '摧毁', '充能', '减速', '加速', '伤害', '护盾', '治疗', '冻结',
                        '使用', '获得', '每有', '每场', '相邻', '左侧', '右侧', '多重触发'
                    ])
                    
                    # 如果包含描述特征或效果关键词，且不是附魔信息，添加到描述列表
                    # 放宽条件：只要不是附魔信息，且长度合理，就认为是描述
                    if not has_enchant_symbol and enchant_count < 2:
                        # 如果包含描述特征或效果关键词，或者文本长度合理（可能是简单描述）
                        if (has_desc_pattern or has_effect_keywords or (len(text) > 10 and len(text) < 500)):
                            # 去重：只添加不重复的文本
                            if text not in descriptions:
                                descriptions.append(text)
            
            # 如果找到了描述，合并并返回（不再继续查找其他类）
            if descriptions:
                # 去重并合并所有描述部分，用空格分隔
                unique_descriptions = []
                seen = set()
                for desc in descriptions:
                    # 标准化文本用于比较（去除多余空格）
                    normalized = re.sub(r'\s+', ' ', desc.strip())
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_descriptions.append(desc)
                # 合并所有唯一的描述部分，用空格分隔，然后清理
                result = ' '.join(unique_descriptions)
                return clean_description(result)
        
        # 如果没找到，尝试 _bC 类（描述文本，不包含冷却时间）
        if not descriptions:
            desc_divs_bc = soup.find_all('div', class_=lambda x: x and '_bC' in str(x) if x else False)
            for div in desc_divs_bc:
                text = div.get_text(separator='', strip=False)
                text = text.replace('\xa0', ' ')
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', text)
                text = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', text)
                text = re.sub(r' {2,}', ' ', text).strip()
                if len(text) > 10:
                    # 跳过明显不是描述的内容
                    if any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History']):
                        continue
                    
                    # 检查是否包含附魔标识符
                    has_enchant_symbol = '❯' in text or '→' in text
                    enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
                    
                    if has_enchant_symbol or enchant_count >= 2:
                        continue
                    
                    # 检查是否包含效果关键词
                    has_effect_keywords = any(keyword in text for keyword in [
                        '摧毁', '充能', '减速', '加速', '伤害', '护盾', '治疗',
                        '使用', '获得', '每有', '每场', '相邻', '左侧', '右侧'
                    ])
                    
                    # 放宽条件：只要不是附魔信息，且长度合理，就认为是描述
                    if not has_enchant_symbol and enchant_count < 2:
                        if has_effect_keywords or (len(text) > 10 and len(text) < 500):
                            if text not in descriptions:
                                descriptions.append(text)
            
            if descriptions:
                # 去重并合并
                unique_descriptions = []
                seen = set()
                for desc in descriptions:
                    normalized = re.sub(r'\s+', ' ', desc.strip())
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_descriptions.append(desc)
                result = ' '.join(unique_descriptions)
                return clean_description(result)
        
        # 如果还没找到，尝试 _cm 类（每个描述行单独一个div，需要合并）
        if not descriptions:
            desc_divs_cm = soup.find_all('div', class_=lambda x: x and '_cm' in str(x) if x else False)
            cm_texts = []
            for div in desc_divs_cm:
                text = div.get_text(separator='', strip=False)
                text = text.replace('\xa0', ' ')
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', text)
                text = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', text)
                text = re.sub(r' {2,}', ' ', text).strip()
                if len(text) > 10:
                    # 跳过明显不是描述的内容
                    if any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History']):
                        continue
                    
                    # 检查是否包含附魔标识符
                    has_enchant_symbol = '❯' in text or '→' in text
                    enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
                    
                    if has_enchant_symbol or enchant_count >= 2:
                        continue
                    
                    # 检查是否包含效果关键词或描述模式
                    has_desc_pattern = any(re.search(pattern, text) for pattern in description_patterns)
                    has_effect_keywords = any(keyword in text for keyword in [
                        '摧毁', '充能', '减速', '加速', '伤害', '护盾', '治疗',
                        '使用', '获得', '每有', '每场', '相邻', '左侧', '右侧'
                    ])
                    
                    # 放宽条件：只要不是附魔信息，且长度合理，就认为是描述
                    if not has_enchant_symbol and enchant_count < 2:
                        if (has_desc_pattern or has_effect_keywords or (len(text) > 10 and len(text) < 500)):
                            # 去重
                            if text not in cm_texts:
                                cm_texts.append(text)
            
            if cm_texts:
                # 去重并合并多个 _cm div 的文本
                unique_cm_texts = []
                seen = set()
                for text in cm_texts:
                    normalized = re.sub(r'\s+', ' ', text.strip())
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_cm_texts.append(text)
                result = ' '.join(unique_cm_texts)
                return clean_description(result)
        
        # 最后尝试 _bM 类（向后兼容）
        if not descriptions:
            desc_divs = soup.find_all('div', class_='_bM')
            for div in desc_divs:
                text = div.get_text(separator='', strip=False)
                text = text.replace('\xa0', ' ')
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', text)
                text = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', text)
                text = re.sub(r' {2,}', ' ', text).strip()
                if (len(text) > 10 and 
                    'Offered by' not in text and 
                    'Dropped by' not in text and
                    'Found in' not in text and
                    'Enchantments' not in text and
                    'Level' not in text and
                    'Day' not in text):
                    has_desc_pattern = any(re.search(pattern, text) for pattern in description_patterns)
                    enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
                    
                    if has_desc_pattern and enchant_count < 2:
                        descriptions.append(text)
                    elif (any(keyword in text for keyword in ['摧毁', '充能', '减速', '加速', '造成', 
                                                              '获得', '使用', '伤害', '治疗', '护盾',
                                                              '每有', '每场', '相邻', '左侧', '右侧']) and
                          enchant_count < 2 and
                          len(text) > 15):
                        descriptions.append(text)
            
            if descriptions:
                # 合并并返回，然后清理
                result = ' '.join(descriptions)
                return clean_description(result)
        
        # 方法2: 从页面文本中提取描述（更精确）
        if not descriptions:
            page_text = soup.get_text()
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            description_lines = []
            in_description = False
            skip_keywords = ['Offered by', 'Dropped by', 'Found in', 'Level', 'Day', 
                           'Enchantments', 'Tier', 'Size', 'Types', 'Tags', 'All', 
                           'Items', 'Skills', 'Monsters', 'Heroes', 'Database']
            
            for line in lines:
                # 跳过标题和导航
                if any(skip in line for skip in skip_keywords):
                    continue
                
                # 检查是否是附魔信息（如果行包含多个附魔关键词，跳过）
                enchant_count = sum(1 for keyword in enchant_keywords if keyword in line)
                if enchant_count >= 2:
                    # 很可能是附魔信息，跳过
                    if in_description:
                        # 如果正在收集描述，遇到附魔信息就停止
                        break
                    continue
                
                # 检查是否是描述开始（包含冷却时间格式或效果关键词，但不是附魔）
                is_description_start = False
                if not in_description and len(line) > 5:
                    # 检查是否包含冷却时间格式（如 5.0秒、9.0»7.0秒）
                    if re.search(r'\d+\.\d+\s*»?\s*\d*\.?\d*\s*秒', line):
                        is_description_start = True
                    # 检查是否包含数值范围格式（如 1 » 2 » 3）
                    elif re.search(r'\d+\s*»\s*\d+\s*»\s*\d+', line):
                        is_description_start = True
                    # 检查是否包含效果关键词
                    elif any(keyword in line for keyword in ['摧毁', '充能', '减速', '加速', '造成', 
                                                            '获得', '使用', '伤害', '治疗', '护盾',
                                                            '每有', '每场', '相邻', '左侧', '右侧',
                                                            'Deal', 'Gain', 'When', 'Shield', 
                                                            'Damage', 'Heal', 'Haste', 'Slow', 
                                                            'Poison', 'Burn', 'Charge', 'Cooldown']):
                        is_description_start = True
                
                if is_description_start and enchant_count < 2:
                    in_description = True
                    description_lines.append(line)
                # 继续收集描述行
                elif in_description:
                    # 如果遇到附魔标识，停止收集
                    if any(stop in line for stop in ['Enchantments', 'Golden', 'Heavy', 
                                                     '黄金', '沉重']) and len(line) < 30:
                        break
                    # 如果包含多个附魔关键词，停止收集
                    elif enchant_count >= 2:
                        break
                    # 继续收集描述文本
                    elif len(line) > 5 and len(line) < 500:
                        description_lines.append(line)
                    # 如果行太长，可能是其他内容，停止
                    elif len(line) >= 500:
                        break
            
            if description_lines:
                descriptions.append(' '.join(description_lines))  # 用空格连接，保持紧凑
        
        if descriptions:
            # 过滤掉明显是附魔信息的描述
            valid_descriptions = []
            for desc in descriptions:
                # 检查是否主要是附魔信息
                enchant_count = sum(1 for keyword in enchant_keywords if keyword in desc)
                # 如果包含太多附魔关键词，很可能是附魔信息
                if enchant_count < 3:  # 允许少量附魔关键词（可能是描述中提到）
                    # 放宽条件：只要不是附魔信息，且长度合理，就认为是描述
                    has_desc_pattern = any(re.search(pattern, desc) for pattern in description_patterns)
                    if has_desc_pattern or len(desc) > 10:  # 降低长度要求从20到10
                        valid_descriptions.append(desc)
            
            if valid_descriptions:
                # 合并所有有效的描述，用空格分隔（描述通常在同一段中）
                full_description = ' '.join(valid_descriptions)
                # 清理多余的空格，但保留必要的空格
                full_description = re.sub(r'\s+', ' ', full_description).strip()
                return full_description
        
        # 方法3: 如果前面都没找到，尝试更通用的提取（兜底方法）
        # 查找所有可能的描述div，只要不是明显的非描述内容
        all_desc_divs = soup.find_all('div', class_=lambda x: x and any(cls in str(x) for cls in ['_bw', '_bx', '_bC', '_cm', '_bM']) if x else False)
        fallback_descriptions = []
        for div in all_desc_divs:
            text = div.get_text(separator='', strip=False)
            text = text.replace('\xa0', ' ')
            text = re.sub(r' {2,}', ' ', text).strip()
            
            # 跳过明显不是描述的内容
            if any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History', 'Offered by', 
                                              'Dropped by', 'Found in', 'Level', 'Day', 'Enchantments',
                                              'Tier', 'Size', 'Types', 'All', 'Items', 'Skills', 
                                              'Monsters', 'Heroes', 'Database']):
                continue
            
            # 跳过附魔信息
            has_enchant_symbol = '❯' in text or '→' in text
            enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
            if has_enchant_symbol or enchant_count >= 2:
                continue
            
            # 如果文本长度合理，且不全是数字或符号，就认为是描述
            if 15 <= len(text) <= 500 and not re.match(r'^[\d\s»\.]+$', text):
                # 检查是否包含中文或常见描述关键词
                has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
                has_common_keywords = any(keyword in text for keyword in [
                    '秒', '伤害', '护盾', '治疗', '物品', '使用', '获得', '造成', '相邻'
                ])
                
                if has_chinese or has_common_keywords:
                    if text not in fallback_descriptions:
                        fallback_descriptions.append(text)
        
            if fallback_descriptions:
                # 去重并合并
                unique_fallback = []
                seen = set()
                for desc in fallback_descriptions:
                    normalized = re.sub(r'\s+', ' ', desc.strip())
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_fallback.append(desc)
                
                if unique_fallback:
                    # 规范化空格格式
                    result = ' '.join(unique_fallback)
                    # 处理冷却时间格式
                    result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', result)
                    result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', result)
                    result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', result)
                    result = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', result)
                    result = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', result)
                    result = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', result)
                    result = re.sub(r' {2,}', ' ', result).strip()
                    return clean_description(result)
        
        return ''
    except Exception as e:
        return ''


def fetch_enchantments_from_detail_page(item_url):
    """从物品详情页获取附魔信息"""
    try:
        response = requests.get(item_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        enchantments_list = []
        cannot_be_enchanted = False
        
        # 附魔关键词
        enchant_keywords = ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded', 'Restorative', 
                           'Toxic', 'Fiery', 'Shiny', 'Deadly', 'Radiant', 'Obsidian',
                           '黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', 
                           '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
        
        # 检查是否不能附魔
        cannot_be_enchanted_keywords = ["Can't be enchanted", "can't be enchanted", 
                                       "cannot be enchanted", "不能附魔", "无法附魔", "不可附魔"]
        
        page_text = soup.get_text()
        if any(keyword in page_text for keyword in cannot_be_enchanted_keywords):
            cannot_be_enchanted = True
        
        # 方法1: 查找包含附魔描述的 div（使用 _bM 类）
        desc_divs = soup.find_all('div', class_='_bM')
        for div in desc_divs:
            text = div.get_text(strip=True)
            # 检查是否包含附魔关键词
            if any(keyword in text for keyword in enchant_keywords):
                if len(text) > 15 and len(text) < 500:  # 合理长度范围
                    enchantments_list.append(text)
        
        # 方法2: 从页面文本中查找附魔信息（更精确的匹配）
        if not enchantments_list:
            page_text = soup.get_text()
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            current_enchantment = []
            found_enchantment = False
            
            for i, line in enumerate(lines):
                # 检测附魔标题（必须是单独一行，且长度较短）
                is_enchant_title = any(keyword in line for keyword in enchant_keywords) and len(line) < 50
                is_invalid = any(invalid in line for invalid in invalid_keywords)
                
                if is_invalid:
                    # 跳过无效信息
                    if current_enchantment:
                        current_enchantment = []
                    found_enchantment = False
                    continue
                
                if is_enchant_title:
                    # 如果之前有收集的附魔信息，先保存
                    if current_enchantment:
                        enchant_text = '\n'.join(current_enchantment)
                        if len(enchant_text) > 20:  # 确保有实际内容
                            enchantments_list.append(enchant_text)
                    # 开始新的附魔信息
                    current_enchantment = [line]
                    found_enchantment = True
                elif found_enchantment:
                    # 收集附魔描述
                    if line and len(line) > 5 and not line.startswith('http'):
                        # 检查是否是下一个附魔标题
                        if any(keyword in line for keyword in enchant_keywords) and len(line) < 50:
                            # 保存当前附魔，开始新的
                            if current_enchantment:
                                enchant_text = '\n'.join(current_enchantment)
                                if len(enchant_text) > 20:
                                    enchantments_list.append(enchant_text)
                            current_enchantment = [line]
                        else:
                            current_enchantment.append(line)
                    elif not line and current_enchantment:
                        # 空行，结束当前附魔
                        enchant_text = '\n'.join(current_enchantment)
                        if len(enchant_text) > 20:
                            enchantments_list.append(enchant_text)
                        current_enchantment = []
                        found_enchantment = False
            
            # 保存最后一个附魔
            if current_enchantment:
                enchant_text = '\n'.join(current_enchantment)
                if len(enchant_text) > 20:
                    enchantments_list.append(enchant_text)
        
        # 去重并过滤
        unique_enchantments = []
        seen = set()
        for enchant in enchantments_list:
            # 过滤无效信息（但保留"不能附魔"的情况）
            if any(invalid in enchant for invalid in cannot_be_enchanted_keywords):
                # 如果包含"不能附魔"关键词，标记但不能直接返回（可能还有其他附魔信息）
                continue
            # 去重
            enchant_normalized = enchant.lower().replace(' ', '').replace('\n', '')
            if enchant_normalized not in seen:
                seen.add(enchant_normalized)
                unique_enchantments.append(enchant)
        
        if unique_enchantments:
            return '\n\n'.join(unique_enchantments)
        
        # 如果检测到"不能附魔"且没有其他附魔信息，返回明确标记
        if cannot_be_enchanted:
            return '不能附魔'
        
        return ''
    except Exception as e:
        return ''


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
        return ''


def extract_items_from_index_html(html_content, items_list, items_db_map):
    """从首页HTML中提取物品信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    items_dict = {}
    
    # 构建物品字典（以URL为键）
    for item in items_list:
        items_dict[item['url']] = {
            'name': item['name'],
            'url': item['url'],
            'name_zh': '',
            'description_zh': '',
            'icon': '',
            'aspect_ratio': 1.0,
            'enchantments': ''
        }
    
    # 从HTML中提取所有物品卡片
    print("  正在解析首页HTML...")
    # 查找所有包含物品链接的a标签
    item_links = soup.find_all('a', href=lambda x: x and '/card/' in x and x not in ['/card/skill/', '/card/monster/'])
    
    # 提取图标URL（从img标签）
    icon_pattern = re.compile(r'https://s\.bazaardb\.gg/v0/[^/]+/item/([a-f0-9]{40})@(\d+)\.webp')
    icon_matches = icon_pattern.findall(html_content)
    
    # 按URL匹配物品
    for link in item_links:
        href = link.get('href', '')
        if not href or '/card/' not in href:
            continue
        
        # 规范化URL
        if href.startswith('/'):
            full_url = f"https://bazaardb.gg{href}"
        elif href.startswith('http'):
            full_url = href
        else:
            continue
        
        # 移除查询参数和锚点
        base_url = full_url.split('?')[0].split('#')[0].rstrip('/')
        
        if base_url in items_dict:
            item_data = items_dict[base_url]
            
            # 提取h3标签中的名称（可能包含中文）
            h3 = link.find('h3')
            if h3:
                name_text = h3.get_text(strip=True)
                # 如果包含中文，提取中文名称
                if any('\u4e00' <= c <= '\u9fff' for c in name_text):
                    # 提取括号中的中文名
                    match = re.search(r'[\(（]([^)）]+)[\)）]', name_text)
                    if match:
                        item_data['name_zh'] = match.group(1).strip()
                    else:
                        item_data['name_zh'] = name_text
            
            # 尝试从附近查找图标
            parent = link.parent
            if parent:
                img = parent.find('img', src=icon_pattern)
                if not img:
                    img = parent.find_previous('img', src=icon_pattern)
                if not img:
                    img = parent.find_next('img', src=icon_pattern)
                
                if img:
                    icon_url = img.get('src', '')
                    match = icon_pattern.search(icon_url)
                    if match:
                        icon_hash = match.group(1)
                        item_data['icon_url'] = f"https://s.bazaardb.gg/v0/z10.0/item/{icon_hash}@256.webp?v=0"
            
            # 提取尺寸信息
            size_text = link.parent.get_text() if link.parent else ''
            size_match = re.search(r'\b(Small|Medium|Large)\b', size_text, re.IGNORECASE)
            if size_match:
                size = size_match.group(1).lower()
                size_map = {'small': 0.5, 'medium': 1.0, 'large': 1.5}
                item_data['aspect_ratio'] = size_map.get(size, 1.0)
            
            # 尝试从首页HTML提取描述（从卡片文本中）
            if not item_data['description_zh']:
                # 查找链接附近的描述文本
                parent = link.parent
                if parent:
                    # 查找包含描述的div
                    desc_divs = parent.find_all('div', class_=lambda x: x and ('_bM' in str(x) or '_bq' in str(x)) if x else False)
                    for desc_div in desc_divs:
                        text = desc_div.get_text(strip=True)
                        # 过滤无效描述
                        if (len(text) > 10 and 
                            'Offered by' not in text and 
                            'Dropped by' not in text and
                            'Found in' not in text and
                            'Enchantments' not in text and
                            not text.startswith('http')):
                            item_data['description_zh'] = text
                            break
    
    # 从items_db.json补充中文名称和附魔信息
    print("  正在补充中文名称和附魔信息...")
    for url, item_data in items_dict.items():
        normalized = normalize_name(item_data['name'])
        item_db = items_db_map.get(normalized)
        if item_db:
            # 补充中文名称
            if not item_data['name_zh']:
                name_zh = item_db.get('name_zh', '')
                if name_zh and name_zh != item_data['name']:
                    item_data['name_zh'] = name_zh
            
            # 补充附魔信息（从 items_db.json）
            if not item_data['enchantments']:
                enchantments_list = item_db.get('enchantments', [])
                if enchantments_list:
                    item_data['enchantments'] = format_enchantments_from_db(enchantments_list)
    
    return list(items_dict.values())


def extract_from_index_html(test_mode=False, test_count=10, batch_size=0, batch_index=0):
    """从首页HTML提取所有物品信息"""
    print("=" * 80)
    print("从首页HTML提取物品信息")
    if test_mode:
        print(f"⚠️ 测试模式：只处理前 {test_count} 个缺失描述的物品")
    elif batch_size > 0:
        print(f"📦 批次模式：每批 {batch_size} 个物品，当前批次 {batch_index + 1}")
    print("=" * 80)
    
    # 确保目录存在
    ITEMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载参考数据
    print("\n正在加载参考数据...")
    items_db_map = load_items_db_map()
    
    # 加载物品列表
    if not ITEMS_LIST_JSON.exists():
        print(f"❌ 未找到物品列表文件: {ITEMS_LIST_JSON}")
        print("请先运行: python fetch_items_html.py")
        return
    
    print(f"  加载物品列表: {ITEMS_LIST_JSON}")
    with open(ITEMS_LIST_JSON, 'r', encoding='utf-8') as f:
        items_list = json.load(f)
    print(f"  ✓ 已加载 {len(items_list)} 个物品")
    
    # 读取首页HTML
    if not INDEX_HTML.exists():
        print(f"❌ 未找到首页HTML文件: {INDEX_HTML}")
        print("请先运行: python fetch_items_html.py")
        return
    
    print(f"\n正在读取首页HTML: {INDEX_HTML}")
    try:
        with open(INDEX_HTML, 'r', encoding='utf-8') as f:
            html_content = f.read()
        print(f"  ✓ HTML文件大小: {len(html_content) / 1024:.2f} KB")
    except Exception as e:
        print(f"  ❌ 读取HTML失败: {e}")
        return
    
    # 先加载现有的 items.json（如果存在），用于合并数据
    existing_items_map = {}
    if ITEMS_JSON.exists():
        try:
            with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
                existing_items = json.load(f)
            for item in existing_items:
                url = item.get('url', '')
                if url:
                    existing_items_map[url] = item
            print(f"  ✓ 已加载现有数据：{len(existing_items_map)} 个物品")
        except Exception as e:
            print(f"  ⚠ 加载现有 items.json 失败: {e}")
    
    # 从首页HTML提取物品信息
    print("\n正在从首页HTML提取物品信息...")
    all_items = extract_items_from_index_html(html_content, items_list, items_db_map)
    
    # 合并已有数据（保留其他物品的原有信息）
    for item in all_items:
        url = item.get('url', '')
        if url in existing_items_map:
            existing_item = existing_items_map[url]
            # 保留其他已有字段（如果新提取的为空）
            if not item.get('name_zh') and existing_item.get('name_zh'):
                item['name_zh'] = existing_item['name_zh']
            if not item.get('enchantments') and existing_item.get('enchantments'):
                item['enchantments'] = existing_item['enchantments']
            if not item.get('icon') and existing_item.get('icon'):
                item['icon'] = existing_item['icon']
            # 如果是批次模式，保留其他批次的描述；否则重新获取所有描述
            if batch_size > 0 or test_mode:
                # 批次/测试模式：只更新当前批次的描述，保留其他批次的
                if existing_item.get('description_zh'):
                    item['description_zh'] = existing_item['description_zh']
    
    # 确定需要从详情页获取描述的物品
    # 如果是批次模式或测试模式，只处理指定范围的物品；否则处理所有物品
    if test_mode:
        # 测试模式：只处理前N个物品
        items_to_fetch = all_items[:test_count]
        print(f"\n⚠️ 测试模式：处理前 {len(items_to_fetch)} 个物品的描述")
    elif batch_size > 0:
        # 批次模式：处理指定批次的物品
        start_idx = batch_index * batch_size
        end_idx = start_idx + batch_size
        items_to_fetch = all_items[start_idx:end_idx]
        total_batches = (len(all_items) + batch_size - 1) // batch_size
        print(f"\n📦 批次模式：处理第 {batch_index + 1}/{total_batches} 批")
        print(f"   范围：第 {start_idx + 1} - {min(end_idx, len(all_items))} 个物品（共 {len(all_items)} 个）")
        print(f"   注意：只更新当前批次物品的描述，其他物品保持不变")
    else:
        # 非批次模式：处理所有物品的描述（强制重新获取）
        items_to_fetch = all_items
        print(f"\n🔄 重新获取所有物品的描述（共 {len(items_to_fetch)} 个）")
    
    # 从详情页获取描述信息（仅获取描述）
    if items_to_fetch:
        print(f"\n正在从物品详情页获取描述信息（共 {len(items_to_fetch)} 个物品）...")
        for idx, item_data in enumerate(items_to_fetch, 1):
            url = item_data.get('url')
            if not url:
                continue
            
            # 只获取描述信息
            description = fetch_description_from_detail_page(url)
            if description:
                item_data['description_zh'] = description
                print(f"  [{idx}/{len(items_to_fetch)}] ✓ {item_data['name']} (描述)")
            else:
                print(f"  [{idx}/{len(items_to_fetch)}] - {item_data['name']} (未找到描述)")
            
            # 避免请求过快
            if idx % 10 == 0:
                time.sleep(0.5)
    
    # 跳过图标下载（暂时）
    print(f"\n⏭️  跳过图标下载（共 {len(all_items)} 个物品）")
    # 处理图标URL，只保存文件名（不实际下载）
    for idx, item_data in enumerate(all_items, 1):
        if item_data.get('icon_url'):
            # 从URL提取文件名
            icon_url = item_data['icon_url']
            # 如果已经有icon字段，保持原样
            if not item_data.get('icon'):
                # 尝试从URL提取文件名，或使用物品名称
                icon_filename = safe_filename(item_data['name']) + '.webp'
                item_data['icon'] = icon_filename
        
        # 移除临时字段
        item_data.pop('icon_url', None)
    
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
    print("提取完成")
    print("=" * 80)
    print(f"物品总数: {len(all_items)}")
    print(f"含中文名: {items_with_zh}")
    print(f"含描述: {items_with_desc}")
    print(f"含图标: {items_with_icon}")
    print(f"含附魔: {items_with_enchantments}")
    print(f"输出文件: {ITEMS_JSON}")


def extract_from_html_files():
    """从 HTML 文件提取所有物品信息（旧方法，保留用于兼容）"""
    print("=" * 80)
    print("从 HTML 文件提取物品信息")
    print("=" * 80)
    
    # 确保目录存在
    ITEMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载参考数据
    print("\n正在加载参考数据...")
    items_db_map = load_items_db_map()
    
    # 获取所有 HTML 文件
    html_files = sorted(list(HTML_DIR.glob('*.html')))
    print(f"\n找到 {len(html_files)} 个 HTML 文件")
    
    if not html_files:
        print("❌ 未找到任何 HTML 文件")
        return
    
    # 提取所有物品信息
    print("\n正在提取物品信息...")
    all_items = []
    
    for idx, html_file in enumerate(html_files, 1):
        try:
            # 读取 HTML
            with open(html_file, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # 跳过失败标记
            if html.strip().startswith('<!-- FAILED'):
                continue
            
            # 从文件名提取物品名称
            item_name = html_file.stem
            parts = item_name.split('_', 1)
            if len(parts) == 2:
                item_name = parts[1]
            
            # 提取详细信息
            item_data = extract_item_details(html, item_name, items_db_map)
            
            # 下载图标
            if item_data.get('icon_url'):
                icon_filename = download_icon(item_data['icon_url'], item_data['name'])
                if icon_filename:
                    item_data['icon'] = icon_filename
            
            # 移除临时字段
            item_data.pop('icon_url', None)
            
            all_items.append(item_data)
            
            if idx % 50 == 0:
                print(f"  [{idx}/{len(html_files)}] 已处理 {idx} 个...")
        
        except Exception as e:
            print(f"  ⚠ [{idx}/{len(html_files)}] {html_file.name}: {e}")
    
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
    print("提取完成")
    print("=" * 80)
    print(f"物品总数: {len(all_items)}")
    print(f"含中文名: {items_with_zh}")
    print(f"含描述: {items_with_desc}")
    print(f"含图标: {items_with_icon}")
    print(f"含附魔: {items_with_enchantments}")
    print(f"输出文件: {ITEMS_JSON}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='从HTML提取物品信息')
    parser.add_argument('--test', type=int, metavar='N', default=0,
                        help='测试模式：只处理前N个缺失描述的物品（默认：0，处理全部）')
    parser.add_argument('--batch-size', type=int, metavar='N', default=0,
                        help='批次大小：每次处理N个物品（默认：0，处理全部）')
    parser.add_argument('--batch-index', type=int, metavar='N', default=0,
                        help='批次索引：从0开始（默认：0，第一批）')
    args = parser.parse_args()
    
    # 优先使用首页HTML解析
    if INDEX_HTML.exists() and ITEMS_LIST_JSON.exists():
        test_mode = args.test > 0
        test_count = args.test if test_mode else 0
        batch_size = args.batch_size if args.batch_size > 0 else 0
        batch_index = args.batch_index if batch_size > 0 else 0
        extract_from_index_html(test_mode=test_mode, test_count=test_count, 
                               batch_size=batch_size, batch_index=batch_index)
    elif HTML_DIR.exists() and list(HTML_DIR.glob('*.html')):
        extract_from_html_files()
    else:
        print("❌ 未找到HTML文件")
        print("请先运行: python fetch_items_html.py")
