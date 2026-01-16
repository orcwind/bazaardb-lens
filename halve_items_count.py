#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将monsters_detail.json中所有物品的数量除以2
因为现在所有物品都是2倍的数量
"""
from pathlib import Path
import json
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'


def halve_items(monster_data):
    """将怪物的物品数量减半"""
    items = monster_data.get('items', [])
    if not items:
        return monster_data
    
    # 统计每个物品出现的次数
    item_counts = Counter()
    for item in items:
        item_name = item.get('name', '')
        if item_name:
            item_counts[item_name] += 1
    
    # 重新构建items数组，每个物品只保留一半的数量（向下取整）
    new_items = []
    processed_items = set()
    
    for item in items:
        item_name = item.get('name', '')
        if not item_name or item_name in processed_items:
            continue
        
        processed_items.add(item_name)
        original_count = item_counts[item_name]
        new_count = original_count // 2  # 除以2，向下取整
        
        # 添加新数量的物品
        for _ in range(new_count):
            new_items.append({'name': item_name})
    
    # 更新怪物数据
    monster_data['items'] = new_items
    return monster_data


def process_all_monsters():
    """处理所有怪物数据"""
    print(f"读取文件: {INPUT_JSON}")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    print(f"总共 {len(monsters)} 个怪物")
    
    # 处理每个怪物
    total_items_before = 0
    total_items_after = 0
    
    for monster in monsters:
        items_before = len(monster.get('items', []))
        total_items_before += items_before
        
        halve_items(monster)
        
        items_after = len(monster.get('items', []))
        total_items_after += items_after
    
    # 保存结果
    print(f"\n保存结果到: {INPUT_JSON}")
    with open(INPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, ensure_ascii=False, indent=2)
    
    print(f"\n处理完成！")
    print(f"处理前总物品数: {total_items_before}")
    print(f"处理后总物品数: {total_items_after}")
    print(f"减少数量: {total_items_before - total_items_after}")


if __name__ == '__main__':
    process_all_monsters()
