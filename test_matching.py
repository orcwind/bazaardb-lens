#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试名称匹配逻辑
"""
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
SKILLS_JSON = BASE_DIR / 'data' / 'Json' / 'skills.json'

def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    # 将所有分隔符（空格、减号、下划线）统一替换为单个空格
    normalized = n.lower().replace('-', ' ').replace('_', ' ')
    # 合并多个空格为单个空格
    normalized = ' '.join(normalized.split())
    return normalized

# 测试用例
test_cases = [
    ("Laser-Pistol", "Laser Pistol"),
    ("Weakpoint-Detector", "Weakpoint Detector"),
    ("Grappling-Hook", "Grappling Hook"),
    ("Eagle-Talisman", "Eagle Talisman"),
    ("Small-Refresh", "Small Refresh"),
    ("Bar-of-Gold", "Bar of Gold"),
    ("Sharpening-Stone", "Sharpening Stone"),
    ("Temple-Expedition-Ticket", "Temple Expedition Ticket"),
    ("Red-Piggles-R", "Red Piggles R"),
    ("Premium-Red-Piggles", "Premium Red Piggles"),
    ("Piggles-Protectors", "Piggles Protectors"),
    ("Yellow-Piggles-L", "Yellow Piggles L"),
]

print("测试标准化函数:")
print("=" * 60)
for detail_name, json_name in test_cases:
    norm_detail = normalize_name(detail_name)
    norm_json = normalize_name(json_name)
    match = norm_detail == norm_json
    print(f"{detail_name:30} -> {norm_detail:30}")
    print(f"{json_name:30} -> {norm_json:30}")
    print(f"匹配: {match}")
    print()

# 测试实际数据
print("\n" + "=" * 60)
print("测试实际数据匹配:")
print("=" * 60)

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

# 测试查找
def find_chinese_name(name_en, direct_mapping, normalized_mapping):
    """查找中文名称，支持多种格式匹配"""
    if not name_en:
        return None
    
    # 1. 直接匹配
    if name_en in direct_mapping:
        return direct_mapping[name_en]
    
    # 2. 标准化后匹配
    normalized = normalize_name(name_en)
    if normalized and normalized in normalized_mapping:
        return normalized_mapping[normalized]
    
    # 3. 格式变体匹配
    name_with_space = name_en.replace('-', ' ')
    if name_with_space in direct_mapping:
        return direct_mapping[name_with_space]
    
    name_with_hyphen = name_en.replace(' ', '-')
    if name_with_hyphen in direct_mapping:
        return direct_mapping[name_with_hyphen]
    
    return None

print("\n查找结果:")
for detail_name, json_name in test_cases:
    result = find_chinese_name(detail_name, items_mapping, items_normalized)
    expected = items_mapping.get(json_name, "未找到")
    print(f"{detail_name:30} -> {result or '未找到':20} (期望: {expected})")
