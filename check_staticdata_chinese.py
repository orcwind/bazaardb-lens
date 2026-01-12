#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查StaticData目录中的JSON文件，查找中文本地化内容
"""

import os
import json

static_data_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\StaticData'

files_to_check = [
    'embeddedLocales.json',
    'ui_localization.json',
    'Tooltips.json',
    'gameRules.json',
    'levelUp.json',
]

print("检查StaticData目录中的JSON文件...")
print("="*70)

for filename in files_to_check:
    file_path = os.path.join(static_data_path, filename)
    if not os.path.exists(file_path):
        continue
    
    print(f"\n检查文件: {filename}")
    print("-"*70)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        file_size = os.path.getsize(file_path)
        print(f"文件大小: {file_size:,} 字节")
        
        # 检查是否包含中文
        chinese_strings = []
        
        def find_chinese(obj, path=''):
            if isinstance(obj, str):
                if any('\u4e00' <= c <= '\u9fff' for c in obj) and len(obj) >= 2:
                    chinese_strings.append({'path': path, 'text': obj})
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}" if path else k
                    find_chinese(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    find_chinese(item, new_path)
        
        find_chinese(data)
        
        if chinese_strings:
            print(f"✓ 找到 {len(chinese_strings)} 个中文字符串")
            print("\n中文内容示例（前10个）:")
            for i, item in enumerate(chinese_strings[:10], 1):
                text_preview = item['text'][:60].replace('\n', ' ')
                print(f"  {i:2d}. {text_preview}...")
            if len(chinese_strings) > 10:
                print(f"  ... 还有 {len(chinese_strings) - 10} 个")
        else:
            print("  未找到中文字符串")
    
    except Exception as e:
        print(f"  读取文件时出错: {e}")

print("\n" + "="*70)
print("检查完成")

