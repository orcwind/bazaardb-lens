#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 JSON 数据补充怪物信息
加载 data/json/items.json 和 data/json/skills.json，
为 extracted_monsters_raw.jsonl 中的 drops、skills 等引用
补充中文名称、描述和品质信息（青铜、白银、黄金、钻石）。
"""

import json
from pathlib import Path
from urllib.parse import unquote


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
SKILLS_JSON = BASE_DIR / 'data' / 'Json' / 'skills.json'
INPUT_JSONL = BASE_DIR / 'data' / 'intermediate' / 'extracted_monsters_raw.jsonl'
OUTPUT_JSON = BASE_DIR / 'data' / 'intermediate' / 'monsters_enriched.json'


def normalize_name(name):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def build_name_mapping(data_list):
    """构建名称映射字典，支持多种格式匹配
    
    Returns:
        (direct_mapping, normalized_mapping): 
        - direct_mapping: {name: item_data}
        - normalized_mapping: {normalized_name: item_data}
    """
    direct_mapping = {}
    normalized_mapping = {}
    
    for item in data_list:
        name = item.get('name', '')
        if not name:
            continue
        
        # 直接映射
        direct_mapping[name] = item
        
        # 标准化映射
        normalized = normalize_name(name)
        if normalized:
            normalized_mapping[normalized] = item
        
        # 别名映射
        aliases = item.get('aliases', [])
        if isinstance(aliases, list):
            for alias in aliases:
                if alias:
                    direct_mapping[alias] = item
                    normalized_alias = normalize_name(alias)
                    if normalized_alias:
                        normalized_mapping[normalized_alias] = item
    
    return direct_mapping, normalized_mapping


def find_item_data(name, direct_mapping, normalized_mapping):
    """根据名称查找物品/技能数据"""
    if not name:
        return None
    
    # 优先精确匹配
    if name in direct_mapping:
        return direct_mapping[name]
    
    # 标准化匹配
    normalized = normalize_name(name)
    if normalized in normalized_mapping:
        return normalized_mapping[normalized]
    
    # 尝试带中横线的变体
    name_with_hyphen = name.replace('_', '-').replace(' ', '-')
    if name_with_hyphen in direct_mapping:
        return direct_mapping[name_with_hyphen]
    
    # 尝试带下划线的变体
    name_with_underscore = name.replace('-', '_').replace(' ', '_')
    if name_with_underscore in direct_mapping:
        return direct_mapping[name_with_underscore]
    
    return None


def extract_quality_from_name(name_zh):
    """从中文名称中提取品质信息
    
    品质关键词：青铜、白银、黄金、钻石、传说
    """
    if not name_zh:
        return None
    
    quality_keywords = {
        '青铜': '青铜',
        '白银': '白银',
        '黄金': '黄金',
        '钻石': '钻石',
        '传说': '传说',
    }
    
    for keyword, quality in quality_keywords.items():
        if keyword in name_zh:
            return quality
    
    return None


def enrich_monster_data(monster, items_map, skills_map):
    """为单个怪物补充数据"""
    enriched = {
        'name': monster.get('name', ''),
        'name_zh': monster.get('name_zh', ''),
        'skills': [],
        'items': []
    }
    
    # 补充技能信息
    skills = monster.get('skills', [])
    for skill in skills:
        skill_name = skill.get('name', '') if isinstance(skill, dict) else str(skill)
        skill_data = find_item_data(skill_name, skills_map[0], skills_map[1])
        
        enriched_skill = {
            'name': skill_name,
            'name_zh': skill_data.get('name_zh', '') if skill_data else '',
            'description_zh': skill_data.get('description_zh', '') if skill_data else '',
            'quality': skill_data.get('quality', '') if skill_data else None
        }
        
        # 如果JSON中没有品质信息，尝试从中文名称中提取
        if not enriched_skill['quality']:
            quality_from_name = extract_quality_from_name(enriched_skill['name_zh'])
            if quality_from_name:
                enriched_skill['quality'] = quality_from_name
        
        enriched['skills'].append(enriched_skill)
    
    # 补充物品信息
    items = monster.get('items', []) or monster.get('drops', [])
    for item in items:
        item_name = item.get('name', '') if isinstance(item, dict) else str(item)
        item_data = find_item_data(item_name, items_map[0], items_map[1])
        
        enriched_item = {
            'name': item_name,
            'name_zh': item_data.get('name_zh', '') if item_data else '',
            'description_zh': item_data.get('description_zh', '') if item_data else '',
            'quality': item_data.get('quality', '') if item_data else None
        }
        
        # 如果JSON中没有品质信息，尝试从中文名称中提取
        if not enriched_item['quality']:
            quality_from_name = extract_quality_from_name(enriched_item['name_zh'])
            if quality_from_name:
                enriched_item['quality'] = quality_from_name
        
        enriched['items'].append(enriched_item)
    
    return enriched


def main():
    """主函数"""
    # 确保输出目录存在
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载物品和技能数据
    print("正在加载物品和技能数据...")
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    items_map = build_name_mapping(items_data)
    print(f"已加载 {len(items_map[0])} 个物品")
    
    with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
    skills_map = build_name_mapping(skills_data)
    print(f"已加载 {len(skills_map[0])} 个技能")
    
    # 读取原始怪物数据
    print(f"\n正在读取 {INPUT_JSONL}...")
    if not INPUT_JSONL.exists():
        print(f"错误：文件不存在 {INPUT_JSONL}")
        return
    
    monsters = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    monster = json.loads(line)
                    monsters.append(monster)
                except json.JSONDecodeError as e:
                    print(f"警告：跳过无效JSON行: {e}")
    
    print(f"已读取 {len(monsters)} 个怪物")
    
    # 补充数据
    print("\n正在补充数据...")
    enriched_monsters = []
    for i, monster in enumerate(monsters, 1):
        enriched = enrich_monster_data(monster, items_map, skills_map)
        enriched_monsters.append(enriched)
        if i % 10 == 0:
            print(f"  已处理 {i}/{len(monsters)}")
    
    # 保存结果
    print(f"\n正在保存结果到 {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(enriched_monsters, f, ensure_ascii=False, indent=2)
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in enriched_monsters)
    total_items = sum(len(m['items']) for m in enriched_monsters)
    skills_with_quality = sum(1 for m in enriched_monsters for s in m['skills'] if s.get('quality'))
    items_with_quality = sum(1 for m in enriched_monsters for i in m['items'] if i.get('quality'))
    
    print(f"\n完成！")
    print(f"  怪物数量: {len(enriched_monsters)}")
    print(f"  技能总数: {total_skills} (包含品质: {skills_with_quality})")
    print(f"  物品总数: {total_items} (包含品质: {items_with_quality})")


if __name__ == '__main__':
    main()
