#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 monsters_detail.json 添加中文翻译
利用 skills.json, items.json, monsters.json 中的中英文映射
"""
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent
SKILLS_JSON = BASE_DIR / 'data' / 'Json' / 'skills.json'
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
MONSTERS_JSON = BASE_DIR / 'data' / 'Json' / 'monsters.json'
INPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'


def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    # 将所有分隔符（空格、减号、下划线）统一替换为单个空格
    normalized = n.lower().replace('-', ' ').replace('_', ' ')
    # 合并多个空格为单个空格
    normalized = ' '.join(normalized.split())
    return normalized


def build_name_mapping(data_list):
    """构建名称映射字典，支持多种格式匹配"""
    # 直接映射：原始名称 -> 中文
    mapping = {}
    # 标准化映射：标准化后的名称 -> 中文（用于模糊匹配）
    normalized_mapping = {}
    
    for item in data_list:
        name_en = item.get('name', '').strip()
        name_zh = item.get('name_zh', '').strip()
        
        if name_en and name_zh:
            # 直接映射（保留原始格式）
            mapping[name_en] = name_zh
            
            # 标准化后的映射（用于格式无关的匹配）
            normalized = normalize_name(name_en)
            if normalized:
                # 如果标准化后的名称还没有映射，或者当前映射更完整，则使用它
                if normalized not in normalized_mapping:
                    normalized_mapping[normalized] = name_zh
    
    return mapping, normalized_mapping


def find_chinese_name(name_en, direct_mapping, normalized_mapping):
    """查找中文名称，支持多种格式匹配（空格、减号、下划线视为同一字符）"""
    if not name_en:
        return None
    
    # 1. 首先尝试直接匹配（完全匹配）
    if name_en in direct_mapping:
        return direct_mapping[name_en]
    
    # 2. 标准化后匹配（忽略空格、减号、下划线的差异）
    normalized = normalize_name(name_en)
    if normalized and normalized in normalized_mapping:
        return normalized_mapping[normalized]
    
    # 3. 尝试各种格式变体（以防标准化函数有遗漏）
    # 将减号替换为空格
    name_with_space = name_en.replace('-', ' ')
    if name_with_space in direct_mapping:
        return direct_mapping[name_with_space]
    
    # 将空格替换为减号
    name_with_hyphen = name_en.replace(' ', '-')
    if name_with_hyphen in direct_mapping:
        return direct_mapping[name_with_hyphen]
    
    # 将下划线替换为空格
    name_with_space_from_underscore = name_en.replace('_', ' ')
    if name_with_space_from_underscore in direct_mapping:
        return direct_mapping[name_with_space_from_underscore]
    
    # 将下划线替换为减号
    name_with_hyphen_from_underscore = name_en.replace('_', '-')
    if name_with_hyphen_from_underscore in direct_mapping:
        return direct_mapping[name_with_hyphen_from_underscore]
    
    return None


def add_chinese_translations():
    """为 monsters_detail.json 添加中文翻译"""
    # 加载参考数据
    print("正在加载参考数据...")
    
    with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
    skills_direct, skills_normalized = build_name_mapping(skills_data)
    print(f"已加载 {len(skills_direct)} 个技能映射")
    
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    items_direct, items_normalized = build_name_mapping(items_data)
    print(f"已加载 {len(items_direct)} 个物品映射")
    
    with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
        monsters_data = json.load(f)
    monsters_direct, monsters_normalized = build_name_mapping(monsters_data)
    print(f"已加载 {len(monsters_direct)} 个怪物映射")
    
    # 加载 monsters_detail.json
    print("\n正在加载 monsters_detail.json...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        monsters_detail = json.load(f)
    print(f"已加载 {len(monsters_detail)} 个怪物详情")
    
    # 统计信息
    monsters_with_zh = 0
    skills_with_zh = 0
    items_with_zh = 0
    skills_not_found = set()
    items_not_found = set()
    monsters_not_found = set()
    
    # 为每个怪物添加中文翻译
    print("\n正在添加中文翻译...")
    for monster in monsters_detail:
        # 添加怪物名称的中文翻译
        monster_name = monster.get('name', '')
        if monster_name:
            monster_zh = find_chinese_name(monster_name, monsters_direct, monsters_normalized)
            if monster_zh:
                monster['name_zh'] = monster_zh
                monsters_with_zh += 1
            else:
                # 如果找不到，保留原有的 name_zh（如果有）
                if 'name_zh' not in monster:
                    monster['name_zh'] = monster_name
                monsters_not_found.add(monster_name)
        
        # 为技能添加中文翻译（强制重新匹配，即使已有 name_zh）
        if 'skills' in monster and isinstance(monster['skills'], list):
            for skill in monster['skills']:
                skill_name = skill.get('name', '')
                if skill_name:
                    skill_zh = find_chinese_name(skill_name, skills_direct, skills_normalized)
                    if skill_zh:
                        skill['name_zh'] = skill_zh
                        skills_with_zh += 1
                    else:
                        # 如果找不到匹配，标记为未找到
                        skills_not_found.add(skill_name)
        
        # 为物品添加中文翻译（强制重新匹配，即使已有 name_zh）
        if 'items' in monster and isinstance(monster['items'], list):
            for item in monster['items']:
                item_name = item.get('name', '')
                if item_name:
                    item_zh = find_chinese_name(item_name, items_direct, items_normalized)
                    if item_zh:
                        item['name_zh'] = item_zh
                        items_with_zh += 1
                    else:
                        # 如果找不到匹配，标记为未找到
                        items_not_found.add(item_name)
    
    # 保存更新后的文件
    print("\n正在保存更新后的文件...")
    with open(INPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(monsters_detail, f, ensure_ascii=False, indent=2)
    
    # 打印统计信息
    print("\n" + "="*60)
    print("处理完成！")
    print("="*60)
    print(f"怪物: {monsters_with_zh}/{len(monsters_detail)} 已添加中文翻译")
    print(f"技能: {skills_with_zh} 个已添加中文翻译")
    print(f"物品: {items_with_zh} 个已添加中文翻译")
    
    if monsters_not_found:
        print(f"\n未找到翻译的怪物 ({len(monsters_not_found)} 个):")
        for name in sorted(monsters_not_found)[:10]:
            print(f"  - {name}")
        if len(monsters_not_found) > 10:
            print(f"  ... 还有 {len(monsters_not_found) - 10} 个")
    
    if skills_not_found:
        print(f"\n未找到翻译的技能 ({len(skills_not_found)} 个):")
        for name in sorted(skills_not_found)[:10]:
            print(f"  - {name}")
        if len(skills_not_found) > 10:
            print(f"  ... 还有 {len(skills_not_found) - 10} 个")
    
    if items_not_found:
        print(f"\n未找到翻译的物品 ({len(items_not_found)} 个):")
        for name in sorted(items_not_found)[:10]:
            print(f"  - {name}")
        if len(items_not_found) > 10:
            print(f"  ... 还有 {len(items_not_found) - 10} 个")
    
    print("\n文件已保存到:", INPUT_JSON)


if __name__ == '__main__':
    add_chinese_translations()
