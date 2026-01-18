#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从已抓取的 HTML 中解析出结构化怪物信息
提取：中英文名称、生命值、技能和物品的中英文名称及品质

输出：data/Json/monsters_detail.json

用法:
    python extract_monsters.py
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
MONSTERS_JSON = BASE_DIR / 'data' / 'Json' / 'monsters.json'
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
SKILLS_JSON = BASE_DIR / 'data' / 'Json' / 'skills.json'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'

# 品质映射
QUALITY_MAP = {
    'bronze': '青铜',
    'silver': '白银',
    'gold': '黄金',
    'diamond': '钻石',
    'legendary': '传说'
}


def normalize_name(name):
    """标准化名称用于匹配"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def load_reference_data():
    """加载参考数据（怪物中英文名称映射，物品和技能数据）"""
    monsters_map = {}
    if MONSTERS_JSON.exists():
        with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
            for m in monsters:
                name = m.get('name') or m.get('name_en', '')
                name_zh = m.get('name_zh', '')
                if name:
                    monsters_map[normalize_name(name)] = {'name': name, 'name_zh': name_zh}
    
    items_map = {}
    skills_map = {}
    
    if ITEMS_JSON.exists():
        with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
            items = json.load(f)
            for item in items:
                name = item.get('name', '')
                if name:
                    items_map[normalize_name(name)] = item
    
    if SKILLS_JSON.exists():
        with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
            skills = json.load(f)
            for skill in skills:
                name = skill.get('name', '')
                if name:
                    skills_map[normalize_name(name)] = skill
    
    return monsters_map, items_map, skills_map


def extract_health_from_html(html_content):
    """从 HTML 中提取生命值"""
    if not html_content:
        return None
    
    # 方法1: 查找 health 图标后的数字（最可靠的方法）
    # 格式: keyword_sprites.svg?11#health"></use></svg> <!-- -->数字</div>
    # 或: keyword_sprites.svg?11#health"></use></svg>数字</div>
    health_icon_patterns = [
        r'keyword_sprites\.svg[^>]*#health["\'][^>]*></use></svg>\s*<!--\s*-->\s*(\d+)</div>',
        r'keyword_sprites\.svg[^>]*#health["\'][^>]*></use></svg>\s*(\d+)</div>',
        r'#health["\'][^>]*></use></svg>\s*<!--\s*-->\s*(\d+)</div>',
        r'#health["\'][^>]*></use></svg>\s*(\d+)</div>',
    ]
    
    for pattern in health_icon_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            try:
                health = int(match.group(1))
                # 生命值通常在合理范围内（50-10000）
                if 50 <= health <= 10000:
                    return health
            except ValueError:
                pass
    
    # 方法2: 查找包含 "Health" 标签的元素后的数字
    # 格式: <span>Health</span></div><div class="_bn">数字</div>
    health_label_patterns = [
        r'<span[^>]*>Health</span></div><div[^>]*>\s*(\d+)</div>',
        r'<span[^>]*>生命值</span></div><div[^>]*>\s*(\d+)</div>',
        r'Health</span>[^<]*<div[^>]*>\s*(\d+)</div>',
    ]
    
    for pattern in health_label_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            try:
                health = int(match.group(1))
                if 50 <= health <= 10000:
                    return health
            except ValueError:
                pass
    
    # 方法3: 查找 meta description 中的生命值
    meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
    if meta_match:
        desc = meta_match.group(1)
        health_patterns = [
            r'health\s*:?\s*(\d+)',
            r'hp\s*:?\s*(\d+)',
            r'生命值\s*:?\s*(\d+)',
        ]
        for pattern in health_patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                try:
                    health = int(match.group(1))
                    if 50 <= health <= 10000:
                        return health
                except ValueError:
                    pass
    
    # 方法4: 查找 Level X • Day Y Monster. Health: Z 格式
    html_lower = html_content.lower()
    level_health_pattern = r'level\s+\d+\s+.*?health\s*:?\s*(\d+)'
    match = re.search(level_health_pattern, html_lower)
    if match:
        try:
            health = int(match.group(1))
            if 50 <= health <= 10000:
                return health
        except ValueError:
            pass
    
    return None


def extract_quality_from_element(html_str):
    """从 HTML 元素中提取品质信息"""
    if not html_str:
        return None
    
    quality_pattern = r'border-color\s*:\s*var\(--(bronze|silver|gold|diamond|legendary)\)'
    match = re.search(quality_pattern, html_str, re.IGNORECASE)
    if match:
        quality_en = match.group(1).lower()
        return QUALITY_MAP.get(quality_en)
    
    return None


def extract_skills_and_items_with_quality(html_content, items_map, skills_map):
    """从 HTML 中提取技能和物品及其品质"""
    soup = BeautifulSoup(html_content, 'html.parser')
    skills = []
    items = []
    
    # 方法1: 从 meta description 提取名称
    meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
    skill_names = []
    item_names = []
    
    if meta_match:
        desc = meta_match.group(1)
        # 提取 Skills: ... Items: ...
        skills_match = re.search(r'Skills:\s*([^.]+)\.', desc)
        if skills_match:
            skill_names = [s.strip() for s in skills_match.group(1).split(',') if s.strip()]
        
        items_match = re.search(r'Items:\s*([^.]+)\.', desc)
        if items_match:
            item_names = [i.strip() for i in items_match.group(1).split(',') if i.strip()]
    
    # 方法2: 从 DOM 中提取技能和物品卡片（包含品质信息）
    # 查找所有包含 /card/ 的链接
    card_links = soup.find_all('a', href=re.compile(r'/card/'))
    card_info_map = {}
    
    for link in card_links:
        href = link.get('href', '')
        if '/card/' in href:
            try:
                # 提取卡片名称
                parts = href.split('/card/')
                if len(parts) > 1:
                    rest = parts[1]
                    path_parts = rest.split('/')
                    if len(path_parts) >= 2:
                        card_name = unquote(path_parts[1].split('?')[0].split('#')[0])
                        
                        # 查找品质信息（在链接附近的父元素中）
                        parent = link.parent
                        quality = None
                        for _ in range(5):  # 向上查找5层
                            if parent:
                                parent_str = str(parent)
                                quality = extract_quality_from_element(parent_str)
                                if quality:
                                    break
                                parent = parent.parent
                        
                        card_info_map[normalize_name(card_name)] = {
                            'name': card_name,
                            'quality': quality
                        }
            except Exception:
                continue
    
    # 匹配技能
    for skill_name in skill_names:
        normalized = normalize_name(skill_name)
        card_info = card_info_map.get(normalized, {})
        
        skill_data = skills_map.get(normalized)
        skill_entry = {
            'name': skill_name,
            'name_zh': skill_data.get('name_zh', '') if skill_data else '',
            'quality': card_info.get('quality') or skill_data.get('quality') if skill_data else None
        }
        skills.append(skill_entry)
    
    # 匹配物品
    for item_name in item_names:
        normalized = normalize_name(item_name)
        card_info = card_info_map.get(normalized, {})
        
        item_data = items_map.get(normalized)
        item_entry = {
            'name': item_name,
            'name_zh': item_data.get('name_zh', '') if item_data else '',
            'quality': card_info.get('quality') or item_data.get('quality') if item_data else None
        }
        items.append(item_entry)
    
    # 方法3: 如果方法1和2没找到，从 DOM 结构查找
    if not skills and not items:
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True).lower()
            if 'skill' in text or '技能' in text:
                div = h3.find_next_sibling('div')
                if div:
                    for card in div.find_all('div', recursive=False):
                        card_link = card.find('a', href=re.compile(r'/card/'))
                        if card_link:
                            href = card_link.get('href', '')
                            try:
                                parts = href.split('/card/')
                                if len(parts) > 1:
                                    rest = parts[1]
                                    path_parts = rest.split('/')
                                    if len(path_parts) >= 2:
                                        card_name = unquote(path_parts[1].split('?')[0])
                                        normalized = normalize_name(card_name)
                                        
                                        quality = extract_quality_from_element(str(card))
                                        skill_data = skills_map.get(normalized)
                                        
                                        skill_entry = {
                                            'name': card_name,
                                            'name_zh': skill_data.get('name_zh', '') if skill_data else '',
                                            'quality': quality or (skill_data.get('quality') if skill_data else None)
                                        }
                                        if skill_entry['name'] and skill_entry not in skills:
                                            skills.append(skill_entry)
                            except Exception:
                                continue
            
            if 'item' in text or '物品' in text:
                div = h3.find_next_sibling('div')
                if div:
                    for card in div.find_all('div', recursive=False):
                        card_link = card.find('a', href=re.compile(r'/card/'))
                        if card_link:
                            href = card_link.get('href', '')
                            try:
                                parts = href.split('/card/')
                                if len(parts) > 1:
                                    rest = parts[1]
                                    path_parts = rest.split('/')
                                    if len(path_parts) >= 2:
                                        card_name = unquote(path_parts[1].split('?')[0])
                                        normalized = normalize_name(card_name)
                                        
                                        quality = extract_quality_from_element(str(card))
                                        item_data = items_map.get(normalized)
                                        
                                        item_entry = {
                                            'name': card_name,
                                            'name_zh': item_data.get('name_zh', '') if item_data else '',
                                            'quality': quality or (item_data.get('quality') if item_data else None)
                                        }
                                        if item_entry['name'] and item_entry not in items:
                                            items.append(item_entry)
                            except Exception:
                                continue
    
    return skills, items


def extract_from_single_html(html_path, monsters_map, items_map, skills_map):
    """从单个 HTML 文件提取怪物信息"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        print(f"  读取失败 {html_path.name}: {e}")
        return None
    
    # 跳过失败的页面
    if html.strip().startswith('<!-- FAILED'):
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 提取名称
    name = None
    name_zh = None
    
    # 方法1: 从 h1 提取
    h1 = soup.find('h1')
    if h1 and h1.text.strip():
        name = h1.text.strip()
    
    # 方法2: 从文件名提取
    if not name:
        name = html_path.stem
        parts = name.split('_', 1)
        if len(parts) == 2:
            name = parts[1]
    
    # 方法3: 从 meta description 提取
    meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html)
    if meta_match and not name:
        desc = meta_match.group(1)
        # 格式通常是: "Name. Day X Monster. Skills: ... Items: ..."
        name_match = re.match(r'^([^.]+)\.', desc)
        if name_match:
            name = name_match.group(1).strip()
    
    # 从 monsters_map 获取中文名称
    if name:
        normalized = normalize_name(name)
        monster_info = monsters_map.get(normalized)
        if monster_info:
            name_zh = monster_info.get('name_zh', '')
    
    # 如果没有找到中文名称，尝试从标题中提取（如果页面是中文）
    if not name_zh:
        title = soup.find('title')
        if title:
            title_text = title.text
            # 如果标题包含中文字符，尝试提取
            if re.search(r'[\u4e00-\u9fff]', title_text):
                # 尝试提取中文名称部分（待实现）
                pass
    
    # 提取生命值
    health = extract_health_from_html(html)
    
    # 提取技能和物品
    skills, items = extract_skills_and_items_with_quality(html, items_map, skills_map)
    
    # 去重
    def deduplicate_by_name(seq, key='name'):
        seen = set()
        result = []
        for item in seq:
            name_val = item.get(key, '')
            if name_val and name_val not in seen:
                seen.add(name_val)
                result.append(item)
        return result
    
    skills = deduplicate_by_name(skills)
    items = deduplicate_by_name(items)
    
    return {
        'name': name or html_path.stem,
        'name_zh': name_zh or '',
        'health': health,
        'skills': skills,
        'items': items
    }


def main():
    """主函数"""
    print("=" * 80)
    print("开始从 HTML 提取怪物信息")
    print("=" * 80)
    
    # 确保输出目录存在
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载参考数据
    print("正在加载参考数据...")
    monsters_map, items_map, skills_map = load_reference_data()
    print(f"  怪物映射: {len(monsters_map)}")
    print(f"  物品数据: {len(items_map)}")
    print(f"  技能数据: {len(skills_map)}")
    
    # 获取所有 HTML 文件
    html_files = sorted(list(HTML_DIR.glob('*.html')))
    print(f"\n找到 {len(html_files)} 个 HTML 文件")
    
    # 提取所有怪物信息
    print("\n正在提取怪物信息...")
    results = []
    for idx, html_file in enumerate(html_files, 1):
        try:
            monster_data = extract_from_single_html(html_file, monsters_map, items_map, skills_map)
            if monster_data:
                results.append(monster_data)
                print(f"  [{idx}/{len(html_files)}] {monster_data['name']}")
            else:
                print(f"  [{idx}/{len(html_files)}] {html_file.name}: 跳过（失败标记）")
        except Exception as e:
            print(f"  [{idx}/{len(html_files)}] {html_file.name}: 错误 - {e}")
    
    # 保存结果
    print(f"\n正在保存结果到 {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 统计信息
    total_skills = sum(len(m.get('skills', [])) for m in results)
    total_items = sum(len(m.get('items', [])) for m in results)
    monsters_with_health = sum(1 for m in results if m.get('health') is not None)
    skills_with_quality = sum(1 for m in results for s in m.get('skills', []) if s.get('quality'))
    items_with_quality = sum(1 for m in results for i in m.get('items', []) if i.get('quality'))
    skills_with_zh = sum(1 for m in results for s in m.get('skills', []) if s.get('name_zh'))
    items_with_zh = sum(1 for m in results for i in m.get('items', []) if i.get('name_zh'))
    
    print("\n" + "=" * 80)
    print("提取完成")
    print("=" * 80)
    print(f"怪物数量: {len(results)}")
    print(f"包含生命值: {monsters_with_health}")
    print(f"技能总数: {total_skills} (含中文名: {skills_with_zh}, 含品质: {skills_with_quality})")
    print(f"物品总数: {total_items} (含中文名: {items_with_zh}, 含品质: {items_with_quality})")
    print(f"输出文件: {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
