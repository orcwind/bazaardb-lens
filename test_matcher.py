#!/usr/bin/env python3
"""测试匹配逻辑"""
import sys
import os

# 添加路径
sys.path.insert(0, 'main_script')

# 导入匹配器
from data.matcher import TextMatcher

# 创建测试数据
monster_data = {
    '舞火大师': {'name': 'Flame Juggler', 'name_zh': '舞火大师'},
    '火灵': {'name': 'Fire Spirit', 'name_zh': '火灵'},
    '火焰巨人': {'name': 'Fire Giant', 'name_zh': '火焰巨人'}
}

# 创建匹配器
print("创建匹配器...")
matcher = TextMatcher(monster_data=monster_data)

# 测试匹配
test_texts = ['舞火大师', '舞火大师 人', '一 舞火大师', '火灵', '火焰巨人']

print("\n测试匹配结果:")
for text in test_texts:
    result = matcher.find_best_match(text)
    print(f'文本: "{text}" -> 匹配: {result}')

# 测试调试日志
print("\n测试带调试日志的匹配:")
import logging
logging.basicConfig(level=logging.DEBUG)
result = matcher.find_best_match('舞火大师')
print(f'最终结果: {result}')