#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出 items.json 中缺失的物品清单（来自 items_db.json）

用于检查哪些物品需要补充，以及哪些可能需要从 items_db.json 中删除
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ITEMS_DB_JSON = BASE_DIR / 'data' / 'Json' / 'items_db.json'
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'


def normalize_name(name):
    """标准化名称用于比较"""
    if not name:
        return ''
    normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def list_missing_items():
    """列出缺失的物品"""
    print("=" * 80)
    print("检查缺失的物品")
    print("=" * 80)
    
    # 加载 items_db.json
    print("\n正在加载 items_db.json...")
    with open(ITEMS_DB_JSON, 'r', encoding='utf-8') as f:
        items_db = json.load(f)
    print(f"  items_db.json 物品数量: {len(items_db)}")
    
    # 加载 items.json
    print("正在加载 items.json...")
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    print(f"  items.json 物品数量: {len(items)}")
    
    # 构建名称集合（标准化）
    items_names = {normalize_name(item['name']): item for item in items if 'name' in item}
    print(f"  已标准化 {len(items_names)} 个物品名称")
    
    # 找出缺失的物品
    print("\n正在查找缺失的物品...")
    missing_items = []
    template_items = []
    debug_items = []
    normal_items = []
    
    for uuid, item_db in items_db.items():
        name = item_db.get('name', '')
        if not name:
            continue
        
        normalized = normalize_name(name)
        if normalized not in items_names:
            item_info = {
                'uuid': uuid,
                'name': name,
                'name_zh': item_db.get('name_zh', ''),
            }
            
            # 分类
            if '[DEBUG]' in name or '[LARGE ITEM TEMPLATE]' in name or '[SMALL ITEM TEMPLATE]' in name:
                if '[DEBUG]' in name:
                    debug_items.append(item_info)
                else:
                    template_items.append(item_info)
            else:
                normal_items.append(item_info)
    
    missing_items = normal_items + template_items + debug_items
    
    # 输出结果
    print("\n" + "=" * 80)
    print("缺失物品清单")
    print("=" * 80)
    
    print(f"\n总计缺失: {len(missing_items)} 个物品")
    print(f"  - 正常物品: {len(normal_items)} 个")
    print(f"  - 模板物品: {len(template_items)} 个")
    print(f"  - DEBUG物品: {len(debug_items)} 个")
    
    # 输出正常物品（需要补充的）
    if normal_items:
        print("\n" + "-" * 80)
        print("正常物品（需要补充）:")
        print("-" * 80)
        for idx, item in enumerate(normal_items, 1):
            print(f"  {idx:2d}. {item['name']} ({item['name_zh'] or '无中文名'})")
            print(f"      UUID: {item['uuid']}")
    
    # 输出模板物品（可能需要删除）
    if template_items:
        print("\n" + "-" * 80)
        print("模板物品（可能需要从 items_db.json 删除）:")
        print("-" * 80)
        for idx, item in enumerate(template_items, 1):
            print(f"  {idx:2d}. {item['name']} ({item['name_zh'] or '无中文名'})")
            print(f"      UUID: {item['uuid']}")
    
    # 输出DEBUG物品（可能需要删除）
    if debug_items:
        print("\n" + "-" * 80)
        print("DEBUG物品（可能需要从 items_db.json 删除）:")
        print("-" * 80)
        for idx, item in enumerate(debug_items, 1):
            print(f"  {idx:2d}. {item['name']} ({item['name_zh'] or '无中文名'})")
            print(f"      UUID: {item['uuid']}")
    
    # 生成删除脚本建议
    if template_items or debug_items:
        print("\n" + "=" * 80)
        print("建议删除的 UUID 列表（复制到 Python 脚本中使用）:")
        print("=" * 80)
        uuids_to_delete = [item['uuid'] for item in template_items + debug_items]
        print("\nuuids_to_delete = [")
        for uuid in uuids_to_delete:
            print(f'    "{uuid}",  # {items_db[uuid].get("name", "")}')
        print("]")
        print("\n# 使用以下代码删除:")
        print("# for uuid in uuids_to_delete:")
        print("#     if uuid in items_db:")
        print("#         del items_db[uuid]")
    
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)
    
    return missing_items, normal_items, template_items, debug_items


if __name__ == '__main__':
    list_missing_items()
