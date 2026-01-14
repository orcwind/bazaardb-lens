#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""立即调试最令人困惑的案例"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'main_script'))

def debug_wuhuodashi_case():
    """调试舞火大师案例"""
    print("=" * 80)
    print("调试：OCR='舞火大师' 为什么匹配到'火灵'")
    print("=" * 80)
    
    # 1. 检查怪物数据
    print("\n1. 检查怪物数据...")
    monsters_json = os.path.join(project_root, 'data', 'Json', 'monsters.json')
    monsters_detail_json = os.path.join(project_root, 'data', 'Json', 'monsters_detail.json')
    
    import json
    
    # 检查monsters.json
    if os.path.exists(monsters_json):
        with open(monsters_json, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
        
        wuhuodashi_found = False
        huoling_found = False
        
        for monster in monsters:
            name_zh = monster.get('name_zh', '')
            if name_zh == '舞火大师':
                wuhuodashi_found = True
                print(f"  ✅ 在monsters.json中找到: 舞火大师")
                print(f"     英文名: {monster.get('name', 'N/A')}")
                print(f"     ID: {monster.get('id', 'N/A')}")
            elif name_zh == '火灵':
                huoling_found = True
                print(f"  ✅ 在monsters.json中找到: 火灵")
                print(f"     英文名: {monster.get('name', 'N/A')}")
                print(f"     ID: {monster.get('id', 'N/A')}")
        
        if not wuhuodashi_found:
            print(f"  ❌ 在monsters.json中未找到: 舞火大师")
        if not huoling_found:
            print(f"  ❌ 在monsters.json中未找到: 火灵")
    
    # 2. 检查文本清理函数
    print("\n2. 检查文本清理函数...")
    
    # 导入清理函数
    import importlib.util
    matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
    spec = importlib.util.spec_from_file_location("matcher", matcher_path)
    matcher_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matcher_module)
    
    # 获取清理函数
    import re
    
    def clean_text_chinese_only_debug(s):
        """调试版本的清理函数"""
        if not isinstance(s, str):
            return ""
        # 只保留中文字符
        result = re.sub(r'[^\u4e00-\u9fff]', '', s)
        print(f"    清理 '{s}' -> '{result}' (长度: {len(result)})")
        return result
    
    # 测试清理
    test_texts = ['舞火大师', '舞火大师 人', '2 和和 于 舞火大师']
    for text in test_texts:
        cleaned = clean_text_chinese_only_debug(text)
    
    # 3. 检查完整匹配逻辑
    print("\n3. 检查完整匹配逻辑...")
    
    monster_clean = clean_text_chinese_only_debug('舞火大师')
    line_clean = clean_text_chinese_only_debug('舞火大师')
    
    print(f"    monster_clean: '{monster_clean}'")
    print(f"    line_clean: '{line_clean}'")
    print(f"    monster_clean in line_clean: {monster_clean in line_clean}")
    print(f"    line_clean in monster_clean: {line_clean in monster_clean}")
    
    # 4. 直接测试匹配
    print("\n4. 直接测试匹配...")
    
    # 创建测试数据
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
        }
    }
    
    # 创建匹配器
    matcher = matcher_module.TextMatcher(monster_data=monster_data)
    
    # 测试
    test_ocr = "舞火大师"
    print(f"   测试OCR: '{test_ocr}'")
    match_type, match_name = matcher.find_best_match(test_ocr)
    
    if match_type and match_name:
        print(f"   匹配结果: {match_type} = {match_name}")
        if match_name == "舞火大师":
            print("   ✅ 正确匹配到舞火大师")
        else:
            print(f"   ❌ 错误匹配到{match_name}，应该是舞火大师")
    else:
        print(f"   匹配结果: 未匹配")
        print("   ❌ 应该匹配到舞火大师")

if __name__ == "__main__":
    debug_wuhuodashi_case()