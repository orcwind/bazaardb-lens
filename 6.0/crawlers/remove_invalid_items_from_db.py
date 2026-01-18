#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 items_db.json 中删除模板物品和 DEBUG 物品
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ITEMS_DB_JSON = BASE_DIR / 'data' / 'Json' / 'items_db.json'


def remove_invalid_items():
    """删除无效物品"""
    print("=" * 80)
    print("从 items_db.json 删除无效物品")
    print("=" * 80)
    
    # 加载 items_db.json
    print("\n正在加载 items_db.json...")
    with open(ITEMS_DB_JSON, 'r', encoding='utf-8') as f:
        items_db = json.load(f)
    print(f"  原始物品数量: {len(items_db)}")
    
    def normalize_name(name):
        """标准化名称用于比较"""
        if not name:
            return ''
        normalized = name.lower().replace('-', ' ').replace('_', ' ').replace('—', ' ')
        normalized = ' '.join(normalized.split())
        return normalized
    
    # 加载 items.json 以检查缺失的物品
    ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    items_names = {normalize_name(item['name']): item for item in items if 'name' in item}
    
    # 需要删除的 UUID 列表（模板和 DEBUG 物品）
    uuids_to_delete = [
        "273b7c90-a4be-4226-b374-94a7c01f07d9",  # [SMALL ITEM TEMPLATE]
        "a031a51e-7b07-4055-adff-a421d2ee8943",  # [MEDIUM ITEM TEMPLATE]
        "8367c019-9866-41b7-b699-330fb7275261",  # [DEBUG] Speedrunner
        "5c570e21-cb8a-444c-9155-cd202631091b",  # [DEBUG] Decharge Test
        "e19e88e3-9296-4bac-b087-346f1b6d906e",  # [DEBUG] Repeatable Quest
        "3130ec0b-ee54-4bd1-8bf9-706c41066f11",  # [DEBUG] Fortune Cookie
        "692e3e47-5bbf-438c-a9c6-af1e2e7d0a05",  # [DEBUG] Gland
        "75c44aaa-dd75-4db3-a47e-8f72a64ffcb7",  # [DEBUG] Recycling Bin
        "f4a7f5d3-73d6-4f08-ab70-6b5ee3309005",  # [DEBUG] Peacewrought
        "e4b32ed8-b70c-48de-818f-e8201fc64a6e",  # [DEBUG] Nested Reference Modifier
    ]
    
    # 找出缺失且没有中文名称的物品（name_zh == name 或 name_zh 为空）
    for uuid, item_db in items_db.items():
        name = item_db.get('name', '')
        if not name:
            continue
        
        # 跳过模板和 DEBUG 物品（已在列表中）
        if any(keyword in name for keyword in ['[DEBUG]', '[SMALL ITEM TEMPLATE]', '[MEDIUM ITEM TEMPLATE]', '[LARGE ITEM TEMPLATE]']):
            continue
        
        # 检查是否缺失
        normalized = normalize_name(name)
        if normalized not in items_names:
            # 如果没有中文名称（name_zh 为空或等于英文名），添加到删除列表
            name_zh = item_db.get('name_zh', '')
            if not name_zh or name_zh.strip() == '' or name_zh == name:
                if uuid not in uuids_to_delete:
                    uuids_to_delete.append(uuid)
    
    # 显示要删除的物品
    print("\n将要删除的物品:")
    deleted_items = []
    for uuid in uuids_to_delete:
        if uuid in items_db:
            item = items_db[uuid]
            name = item.get('name', 'Unknown')
            deleted_items.append({'uuid': uuid, 'name': name})
            print(f"  - {name} ({uuid})")
        else:
            print(f"  - UUID {uuid} 不存在（跳过）")
    
    if not deleted_items:
        print("  没有需要删除的物品")
        return
    
    # 确认删除
    if not deleted_items:
        print("  没有需要删除的物品")
        return
    
    print(f"\n将删除 {len(deleted_items)} 个物品")
    
    # 删除
    print("\n正在删除...")
    deleted_count = 0
    for uuid in uuids_to_delete:
        if uuid in items_db:
            del items_db[uuid]
            deleted_count += 1
    
    # 备份原文件
    backup_file = ITEMS_DB_JSON.with_suffix('.json.backup')
    print(f"\n正在备份原文件到 {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(dict(items_db), f, ensure_ascii=False, indent=2)
    
    # 保存
    print(f"正在保存到 {ITEMS_DB_JSON}...")
    with open(ITEMS_DB_JSON, 'w', encoding='utf-8') as f:
        json.dump(items_db, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("删除完成")
    print("=" * 80)
    print(f"删除物品数: {deleted_count}")
    print(f"剩余物品数: {len(items_db)}")
    print(f"备份文件: {backup_file}")


if __name__ == '__main__':
    remove_invalid_items()
