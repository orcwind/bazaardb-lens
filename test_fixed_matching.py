#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试修复后的匹配逻辑"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'main_script'))

def test_fixed_matching():
    """测试修复后的匹配逻辑"""
    print("=" * 80)
    print("测试修复后的匹配逻辑")
    print("=" * 80)
    
    # 导入修复后的matcher
    import importlib.util
    matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
    spec = importlib.util.spec_from_file_location("matcher", matcher_path)
    matcher_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matcher_module)
    TextMatcher = matcher_module.TextMatcher
    
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
    matcher = TextMatcher(monster_data=monster_data)
    
    # 测试案例：实际OCR结果
    test_cases = [
        ("2 和和 于 舞火大师", "应该匹配: 舞火大师 (完整匹配)"),
        ("和和于舞火大师", "应该匹配: 舞火大师 (完整匹配)"),
        ("舞火大师", "应该匹配: 舞火大师 (完全相等)"),
        ("火大师", "应该匹配: 舞火大师 (部分匹配)"),
        ("火灵", "应该匹配: 火灵 (完全相等)"),
        ("火", "应该不匹配或匹配火灵 (单字匹配)"),
    ]
    
    for ocr_text, expected in test_cases:
        print(f"\n测试: OCR='{ocr_text}'")
        print(f"期望: {expected}")
        
        match_type, match_name = matcher.find_best_match(ocr_text)
        
        if match_type and match_name:
            print(f"结果: {match_type} = {match_name}")
            
            # 验证结果
            if "舞火大师" in expected and match_name == "舞火大师":
                print("  ✅ 符合期望")
            elif "火灵" in expected and match_name == "火灵":
                print("  ✅ 符合期望")
            else:
                print("  ⚠️  可能不符合期望")
        else:
            print(f"结果: 未匹配")
            if "应该不匹配" in expected:
                print("  ✅ 符合期望")
            else:
                print("  ❌ 不符合期望")

if __name__ == "__main__":
    test_fixed_matching()