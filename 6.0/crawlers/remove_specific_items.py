#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 items_db.json 和 items.json 中删除指定的物品
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


def remove_specific_items():
    """删除指定的物品"""
    print("=" * 80)
    print("删除指定物品")
    print("=" * 80)
    
    # 要删除的物品名称列表
    items_to_remove = [
        "Elixir of Immortality",
        "Flying Pig"
    ]
    
    print(f"\n要删除的物品:")
    for item_name in items_to_remove:
        print(f"  - {item_name}")
    
    # 处理 items_db.json
    print("\n" + "-" * 80)
    print("处理 items_db.json...")
    with open(ITEMS_DB_JSON, 'r', encoding='utf-8') as f:
        items_db = json.load(f)
    
    print(f"  原始物品数量: {len(items_db)}")
    
    removed_from_db = []
    items_to_remove_normalized = {normalize_name(name): name for name in items_to_remove}
    
    for uuid, item_db in list(items_db.items()):
        name = item_db.get('name', '')
        normalized = normalize_name(name)
        if normalized in items_to_remove_normalized:
            original_name = items_to_remove_normalized[normalized]
            del items_db[uuid]
            removed_from_db.append(original_name)
            print(f"  ✓ 从 items_db.json 删除: {name} (UUID: {uuid})")
    
    if removed_from_db:
        # 备份
        backup_file = ITEMS_DB_JSON.with_suffix('.json.backup2')
        print(f"\n  备份到 {backup_file}...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(dict(items_db), f, ensure_ascii=False, indent=2)
        
        # 保存
        print(f"  保存到 {ITEMS_DB_JSON}...")
        with open(ITEMS_DB_JSON, 'w', encoding='utf-8') as f:
            json.dump(items_db, f, ensure_ascii=False, indent=2)
        print(f"  剩余物品数量: {len(items_db)}")
    else:
        print("  ℹ️  items_db.json 中没有找到要删除的物品")
    
    # 处理 items.json
    print("\n" + "-" * 80)
    print("处理 items.json...")
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    print(f"  原始物品数量: {len(items)}")
    
    removed_from_items = []
    items_filtered = []
    
    for item in items:
        name = item.get('name', '')
        normalized = normalize_name(name)
        if normalized in items_to_remove_normalized:
            original_name = items_to_remove_normalized[normalized]
            removed_from_items.append(original_name)
            print(f"  ✓ 从 items.json 删除: {name}")
        else:
            items_filtered.append(item)
    
    if removed_from_items:
        # 备份
        backup_file = ITEMS_JSON.with_suffix('.json.backup2')
        print(f"\n  备份到 {backup_file}...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        # 保存
        print(f"  保存到 {ITEMS_JSON}...")
        with open(ITEMS_JSON, 'w', encoding='utf-8') as f:
            json.dump(items_filtered, f, ensure_ascii=False, indent=2)
        print(f"  剩余物品数量: {len(items_filtered)}")
    else:
        print("  ℹ️  items.json 中没有找到要删除的物品")
    
    # 总结
    print("\n" + "=" * 80)
    print("删除完成")
    print("=" * 80)
    print(f"从 items_db.json 删除: {len(removed_from_db)} 个")
    if removed_from_db:
        for name in removed_from_db:
            print(f"  - {name}")
    print(f"从 items.json 删除: {len(removed_from_items)} 个")
    if removed_from_items:
        for name in removed_from_items:
            print(f"  - {name}")


if __name__ == '__main__':
    remove_specific_items()
