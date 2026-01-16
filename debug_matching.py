#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试名称匹配
"""
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'

def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    normalized = n.lower().replace('-', ' ').replace('_', ' ')
    normalized = ' '.join(normalized.split())
    return normalized

# 加载 items.json
with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
    items_data = json.load(f)

# 构建映射
items_mapping = {}
items_normalized = {}
for item in items_data:
    name_en = item.get('name', '').strip()
    name_zh = item.get('name_zh', '').strip()
    if name_en and name_zh:
        items_mapping[name_en] = name_zh
        norm = normalize_name(name_en)
        if norm:
            items_normalized[norm] = name_zh

# 测试用例
test_names = [
    "Laser-Pistol",
    "Weakpoint-Detector",
    "Grappling-Hook",
    "Eagle-Talisman",
    "Bar-of-Gold",
    "Sharpening-Stone",
    "Temple-Expedition-Ticket",
    "Red-Piggles-R",
    "Premium-Red-Piggles",
    "Piggles-Protectors",
    "Yellow-Piggles-L",
]

print("测试匹配:")
print("=" * 80)
for name in test_names:
    norm = normalize_name(name)
    print(f"\n查找: {name}")
    print(f"标准化: {norm}")
    
    # 直接匹配
    if name in items_mapping:
        print(f"✓ 直接匹配: {items_mapping[name]}")
    else:
        print("✗ 直接匹配: 未找到")
    
    # 标准化匹配
    if norm in items_normalized:
        print(f"✓ 标准化匹配: {items_normalized[norm]}")
    else:
        print("✗ 标准化匹配: 未找到")
        
        # 查找可能的匹配
        name_with_space = name.replace('-', ' ')
        if name_with_space in items_mapping:
            print(f"✓ 格式变体匹配 ({name_with_space}): {items_mapping[name_with_space]}")
