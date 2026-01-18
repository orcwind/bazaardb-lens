#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 monsters_detail.json 中的技能和物品添加品质信息
从怪物的HTML文件中提取每个技能和物品的品质信息（青铜、白银、黄金、钻石、传说）
"""

import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import unquote


BASE_DIR = Path(__file__).resolve().parent.parent.parent
MONSTERS_DETAIL_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'


# 品质映射：英文 -> 中文
QUALITY_MAP = {
    'bronze': '青铜',
    'silver': '白银',
    'gold': '黄金',
    'diamond': '钻石',
    'legendary': '传说'
}


def normalize_name(name):
    """标准化名称，用于匹配"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def extract_quality_from_html_element(html_element_str):
    """从HTML元素字符串中提取品质信息
    
    Args:
        html_element_str: HTML元素字符串
        
    Returns:
        品质字符串（中文），如果未找到返回 None
    """
    if not html_element_str:
        return None
    
    # 查找 border-color:var(--quality) 格式
    quality_pattern = r'border-color\s*:\s*var\(--(bronze|silver|gold|diamond|legendary)\)'
    match = re.search(quality_pattern, html_element_str, re.IGNORECASE)
    
    if match:
        quality_en = match.group(1).lower()
        return QUALITY_MAP.get(quality_en)
    
    return None


def extract_card_qualities_from_html(html_content, card_names, card_type='item'):
    """从HTML内容中提取卡片名称和品质的映射
    
    Args:
        html_content: HTML字符串
        card_names: 卡片名称列表（英文名）
        card_type: 'skill' 或 'item'
        
    Returns:
        dict: {card_name: quality} 映射
    """
    if not html_content or not card_names:
        return {}
    
    soup = BeautifulSoup(html_content, 'html.parser')
    card_quality_map = {}
    
    # 标准化卡片名称
    normalized_card_names = {normalize_name(name): name for name in card_names}
    
    # 方法1: 从 /card/ 链接中提取，每个卡片链接后面应该能找到对应的品质信息
    # 查找所有包含卡片名称的链接
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if '/card/' in href:
            # 提取卡片名称
            try:
                parts = href.split('/card/')
                if len(parts) > 1:
                    rest = parts[1]
                    path_parts = rest.split('/')
                    if len(path_parts) >= 2:
                        card_name_from_url = unquote(path_parts[1].split('?')[0].split('#')[0])
                        normalized_url_name = normalize_name(card_name_from_url)
                        
                        # 检查是否在卡片名称列表中
                        original_name = normalized_card_names.get(normalized_url_name)
                        if original_name:
                            # 查找该链接附近的品质信息
                            # 获取包含该链接的父元素
                            parent = link.parent
                            max_depth = 5
                            depth = 0
                            
                            while parent and depth < max_depth:
                                parent_str = str(parent)
                                quality = extract_quality_from_html_element(parent_str)
                                if quality:
                                    card_quality_map[original_name] = quality
                                    break
                                
                                parent = parent.parent
                                depth += 1
            except Exception:
                pass
    
    # 方法2: 如果方法1没有找到，尝试从整个HTML中匹配卡片名称和品质
    # 按顺序匹配卡片名称和品质
    # HTML中技能/物品通常按顺序出现，我们可以根据顺序匹配
    if len(card_quality_map) < len(card_names):
        # 查找所有包含品质信息的元素
        quality_pattern = r'border-color\s*:\s*var\(--(bronze|silver|gold|diamond|legendary)\)'
        quality_elements = []
        
        # 在HTML中查找所有包含品质信息的元素位置
        for match in re.finditer(quality_pattern, html_content, re.IGNORECASE):
            quality_en = match.group(1).lower()
            quality_zh = QUALITY_MAP.get(quality_en)
            if quality_zh:
                # 查找该品质信息附近的卡片链接
                start_pos = max(0, match.start() - 1000)
                end_pos = min(len(html_content), match.end() + 1000)
                context = html_content[start_pos:end_pos]
                
                # 在上下文中查找卡片链接
                card_pattern = r'/card/[a-zA-Z0-9]+/([^/<>"\'\s?&#]+)'
                card_matches = re.findall(card_pattern, context)
                for card_match in card_matches:
                    try:
                        card_name_from_url = unquote(card_match.split('?')[0].split('#')[0])
                        normalized_url_name = normalize_name(card_name_from_url)
                        original_name = normalized_card_names.get(normalized_url_name)
                        if original_name and original_name not in card_quality_map:
                            card_quality_map[original_name] = quality_zh
                            break
                    except Exception:
                        pass
    
    return card_quality_map


def find_monster_html_file(monster_name):
    """根据怪物名称查找对应的HTML文件"""
    # 方法1: 尝试通过文件名模式匹配 (格式: NNNN_Name.html)
    safe_name = monster_name.replace(' ', '_').replace('/', '_')
    patterns = [
        f'*_{safe_name}.html',
        f'*{safe_name}*.html',
        f'*_{monster_name.replace(" ", "_")}.html'
    ]
    
    for pattern in patterns:
        matches = list(HTML_DIR.glob(pattern))
        if matches:
            # 验证HTML文件中的h1标签是否匹配
            for match in matches:
                try:
                    with open(match, 'r', encoding='utf-8') as f:
                        content = f.read()
                        soup = BeautifulSoup(content, 'html.parser')
                        h1 = soup.find('h1')
                        if h1 and h1.text.strip() == monster_name:
                            return match
                except Exception:
                    continue
    
    # 方法2: 如果找不到，通过HTML中的h1标签精确匹配所有文件
    for html_file in HTML_DIR.glob('*.html'):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                h1 = soup.find('h1')
                # 精确匹配h1标签中的文本
                if h1 and h1.text.strip() == monster_name:
                    return html_file
        except Exception:
            continue
    
    return None


def update_monster_with_qualities(monster, html_content):
    """更新怪物数据，为技能和物品添加品质信息"""
    # 提取技能名称列表
    skill_names = [skill.get('name', '') for skill in monster.get('skills', [])]
    item_names = [item.get('name', '') for item in monster.get('items', [])]
    
    # 从HTML中提取品质映射
    skill_qualities = extract_card_qualities_from_html(html_content, skill_names, 'skill')
    item_qualities = extract_card_qualities_from_html(html_content, item_names, 'item')
    
    # 更新技能品质
    for skill in monster.get('skills', []):
        skill_name = skill.get('name', '')
        if skill_name in skill_qualities:
            skill['quality'] = skill_qualities[skill_name]
    
    # 更新物品品质
    for item in monster.get('items', []):
        item_name = item.get('name', '')
        if item_name in item_qualities:
            item['quality'] = item_qualities[item_name]


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='为 monsters_detail.json 添加品质信息')
    parser.add_argument('--dry-run', action='store_true', help='只显示会执行的操作，不实际更新')
    
    args = parser.parse_args()
    
    # 读取 monsters_detail.json
    print(f"正在读取 {MONSTERS_DETAIL_JSON}...")
    with open(MONSTERS_DETAIL_JSON, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    print(f"找到 {len(monsters)} 个怪物")
    
    stats = {
        'total': len(monsters),
        'found_html': 0,
        'missing_html': 0,
        'skills_updated': 0,
        'items_updated': 0,
        'skills_total': 0,
        'items_total': 0
    }
    
    # 处理每个怪物
    for idx, monster in enumerate(monsters, 1):
        monster_name = monster.get('name', '')
        print(f"\n[{idx}/{stats['total']}] {monster_name}...")
        
        # 查找对应的HTML文件
        html_file = find_monster_html_file(monster_name)
        
        if not html_file:
            print(f"  ✗ 未找到HTML文件")
            stats['missing_html'] += 1
            continue
        
        print(f"  ✓ 找到HTML文件: {html_file.name}")
        stats['found_html'] += 1
        
        # 读取HTML内容
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"  ✗ 读取HTML文件失败: {e}")
            continue
        
        # 统计技能和物品数量
        skills_count = len(monster.get('skills', []))
        items_count = len(monster.get('items', []))
        stats['skills_total'] += skills_count
        stats['items_total'] += items_count
        
        if not args.dry_run:
            # 更新品质信息
            update_monster_with_qualities(monster, html_content)
            
            # 统计更新的数量
            skills_with_quality = sum(1 for s in monster.get('skills', []) if s.get('quality'))
            items_with_quality = sum(1 for i in monster.get('items', []) if i.get('quality'))
            
            stats['skills_updated'] += skills_with_quality
            stats['items_updated'] += items_with_quality
            
            print(f"    技能: {skills_with_quality}/{skills_count} 有品质")
            print(f"    物品: {items_with_quality}/{items_count} 有品质")
        else:
            print(f"    技能: {skills_count} 个")
            print(f"    物品: {items_count} 个")
    
    # 保存更新后的文件
    if not args.dry_run:
        print(f"\n正在保存更新后的文件...")
        with open(MONSTERS_DETAIL_JSON, 'w', encoding='utf-8') as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 已保存")
    
    # 显示统计信息
    print(f"\n{'='*50}")
    print(f"统计:")
    print(f"  怪物总数: {stats['total']}")
    print(f"  找到HTML: {stats['found_html']}")
    print(f"  缺失HTML: {stats['missing_html']}")
    if not args.dry_run:
        print(f"  技能总数: {stats['skills_total']}")
        print(f"  技能已添加品质: {stats['skills_updated']}")
        print(f"  物品总数: {stats['items_total']}")
        print(f"  物品已添加品质: {stats['items_updated']}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
