#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 items.json 中所有物品的描述是否有错误和缺漏
"""

import json
import re
from pathlib import Path

# 文件路径
ITEMS_JSON = Path(__file__).parent.parent.parent / 'data' / 'Json' / 'items.json'


def check_descriptions():
    """检查所有物品的描述"""
    print("=" * 80)
    print("检查物品描述")
    print("=" * 80)
    
    # 加载数据
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    items = sorted(items, key=lambda x: x.get('name', ''))
    print(f"\n总物品数: {len(items)}\n")
    
    problems = {
        'missing_desc': [],
        'has_types': [],
        'has_ammo': [],
        'has_enchant_error': []
    }
    
    # 附魔中文名称
    enchant_zh_names = ['黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '毒素', '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
    
    for item in items:
        name = item.get('name', '')
        desc = item.get('description_zh', '')
        
        # 1. 检查缺失描述
        if not desc or desc.strip() == '':
            problems['missing_desc'].append(name)
            continue
        
        # 2. 检查包含 Types 标签
        if 'Types' in desc and re.search(r'Types[A-Za-z]', desc):
            problems['has_types'].append((name, desc[:100]))
        
        # 3. 检查包含 Ammo 标签
        if 'Ammo:' in desc:
            problems['has_ammo'].append((name, desc[:100]))
        
        # 4. 检查包含附魔错误信息
        if re.search(r"(Can't|can't|cannot).*be.*enchanted.*with", desc, re.I) or '不能附魔' in desc or '无法附魔' in desc:
            # 如果同时包含附魔中文名称，则认为是错误
            if any(zh_name in desc for zh_name in enchant_zh_names):
                problems['has_enchant_error'].append((name, desc[:150]))
    
    # 输出结果
    print(f"1. 缺失描述: {len(problems['missing_desc'])} 个")
    if problems['missing_desc']:
        for name in problems['missing_desc'][:30]:
            print(f"   - {name}")
        if len(problems['missing_desc']) > 30:
            print(f"   ... 还有 {len(problems['missing_desc']) - 30} 个")
    
    print(f"\n2. 包含 Types 标签: {len(problems['has_types'])} 个")
    if problems['has_types']:
        for name, desc in problems['has_types'][:20]:
            print(f"   - {name}: {desc}...")
        if len(problems['has_types']) > 20:
            print(f"   ... 还有 {len(problems['has_types']) - 20} 个")
    
    print(f"\n3. 包含 Ammo 标签: {len(problems['has_ammo'])} 个")
    if problems['has_ammo']:
        for name, desc in problems['has_ammo'][:20]:
            print(f"   - {name}: {desc}...")
        if len(problems['has_ammo']) > 20:
            print(f"   ... 还有 {len(problems['has_ammo']) - 20} 个")
    
    print(f"\n4. 包含附魔错误信息: {len(problems['has_enchant_error'])} 个")
    if problems['has_enchant_error']:
        for name, desc in problems['has_enchant_error'][:20]:
            print(f"   - {name}: {desc}...")
        if len(problems['has_enchant_error']) > 20:
            print(f"   ... 还有 {len(problems['has_enchant_error']) - 20} 个")
    
    # 统计
    total_problems = (len(problems['missing_desc']) + 
                     len(problems['has_types']) + 
                     len(problems['has_ammo']) + 
                     len(problems['has_enchant_error']))
    
    print("\n" + "=" * 80)
    print(f"总计问题: {total_problems} 个")
    print(f"无问题物品: {len(items) - total_problems} 个")
    print("=" * 80)
    
    return problems


if __name__ == '__main__':
    check_descriptions()
