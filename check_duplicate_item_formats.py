#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查monsters_detail.json中是否有同一物品的不同命名格式同时出现
例如：abc def, abc-def, abc_def
"""
from pathlib import Path
import json
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'


def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    normalized = n.lower().replace('-', ' ').replace('_', ' ').replace(' ', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def check_duplicate_formats():
    """检查是否有同一物品的不同格式"""
    print(f"读取文件: {INPUT_JSON}")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    print(f"总共 {len(monsters)} 个怪物\n")
    
    issues_found = []
    
    for monster in monsters:
        monster_name = monster.get('name', 'Unknown')
        items = monster.get('items', [])
        
        # 按标准化名称分组，记录原始格式
        item_groups = defaultdict(set)
        for item in items:
            item_name = item.get('name', '')
            if item_name:
                normalized = normalize_name(item_name)
                item_groups[normalized].add(item_name)
        
        # 检查是否有同一标准化名称对应多个不同格式
        for normalized, formats in item_groups.items():
            if len(formats) > 1:
                # 发现同一物品的不同格式
                formats_list = sorted(formats)
                issues_found.append({
                    'monster': monster_name,
                    'normalized': normalized,
                    'formats': formats_list
                })
    
    # 输出结果
    if issues_found:
        print(f"发现 {len(issues_found)} 个怪物存在同一物品的不同命名格式：\n")
        for issue in issues_found:
            print(f"怪物: {issue['monster']}")
            print(f"  标准化名称: {issue['normalized']}")
            print(f"  不同格式: {', '.join(issue['formats'])}")
            print()
    else:
        print("✓ 未发现同一物品的不同命名格式")
    
    # 统计信息
    print(f"\n统计:")
    print(f"  检查的怪物数: {len(monsters)}")
    print(f"  发现问题的怪物数: {len(issues_found)}")
    
    return issues_found


if __name__ == '__main__':
    check_duplicate_formats()
