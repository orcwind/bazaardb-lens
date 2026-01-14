#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单测试匹配逻辑"""

import os
import sys
import json

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'main_script'))

# 直接导入matcher
import importlib.util
matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
spec = importlib.util.spec_from_file_location("matcher", matcher_path)
matcher_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matcher_module)
TextMatcher = matcher_module.TextMatcher

def test_matcher_directly():
    """直接测试匹配器"""
    print("测试匹配逻辑...")
    
    # 手动创建一些测试数据
    monster_data = {
        "舞火大师": {
            "name_zh": "舞火大师",
            "name": "Fire Dance Master",
            "id": "test_001"
        },
        "火灵": {
            "name_zh": "火灵",
            "name": "Fire Spirit",
            "id": "test_002"
        },
        "水车": {
            "name_zh": "水车",
            "name": "Water Wheel",
            "id": "test_003"
        }
    }
    
    # 创建匹配器
    matcher = TextMatcher(monster_data=monster_data)
    
    # 测试文本
    test_texts = [
        "舞火大师 ER",
        "舞火大师",
        "火大师",
        "火灵",
        "水车测试",
        "测试水车"
    ]
    
    for text in test_texts:
        print(f"\nOCR文本: {repr(text)}")
        match_type, match_name = matcher.find_best_match(text)
        if match_type and match_name:
            print(f"匹配结果: {match_type} = {match_name}")
            print(f"怪物数据: {monster_data.get(match_name, {})}")
        else:
            print(f"匹配结果: 未匹配")

def check_monster_data():
    """检查怪物数据文件"""
    print("\n检查怪物数据文件...")
    
    monsters_json_path = os.path.join(project_root, 'data', 'Json', 'monsters.json')
    monsters_detail_path = os.path.join(project_root, 'data', 'Json', 'monsters_detail.json')
    
    for path in [monsters_json_path, monsters_detail_path]:
        if os.path.exists(path):
            print(f"\n文件: {os.path.basename(path)}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"  数据条数: {len(data)}")
                        # 查找舞火大师和火灵
                        for item in data[:10]:  # 只检查前10条
                            name_zh = item.get('name_zh', '')
                            if name_zh in ['舞火大师', '火灵']:
                                print(f"  找到: {name_zh} - {item.get('name', '')}")
                    else:
                        print(f"  数据类型: {type(data)}")
            except Exception as e:
                print(f"  读取错误: {e}")
        else:
            print(f"\n文件不存在: {path}")

if __name__ == "__main__":
    print("=" * 80)
    print("简单匹配测试")
    print("=" * 80)
    
    test_matcher_directly()
    check_monster_data()