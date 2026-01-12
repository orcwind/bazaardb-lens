#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在游戏文件中搜索中文字符串
"""

import json
import os
import sys

def search_chinese_in_file(file_path):
    """在文件中搜索中文字符"""
    if not os.path.exists(file_path):
        return []
    
    chinese_items = []
    
    try:
        # 尝试作为JSON读取
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            def extract_strings(obj, path=''):
                """递归提取字符串"""
                if isinstance(obj, str):
                    # 检查是否包含中文
                    if any('\u4e00' <= c <= '\u9fff' for c in obj):
                        chinese_items.append({
                            'path': path,
                            'text': obj
                        })
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        extract_strings(v, f"{path}.{k}" if path else k)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        extract_strings(item, f"{path}[{i}]" if path else f"[{i}]")
            
            extract_strings(data)
    except:
        # 如果不是JSON或读取失败，尝试作为文本读取
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找中文字符串
                import re
                matches = re.findall(r'[\u4e00-\u9fff]+', content)
                for match in matches:
                    if len(match) >= 2:  # 至少2个字符
                        chinese_items.append({
                            'path': 'text_content',
                            'text': match
                        })
        except:
            pass
    
    return chinese_items

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\StaticData'
    
    files_to_check = [
        'Tooltips.json',
        'ui_localization.json',
        'embeddedLocales.json',
        'gameRules.json',
        'levelUp.json',
    ]
    
    print("在游戏文件中搜索中文字符串\n")
    print("="*70)
    
    all_chinese = {}
    
    for filename in files_to_check:
        file_path = os.path.join(base_path, filename)
        print(f"\n检查文件: {filename}")
        print("-"*70)
        
        chinese_items = search_chinese_in_file(file_path)
        if chinese_items:
            all_chinese[filename] = chinese_items
            print(f"找到 {len(chinese_items)} 个包含中文的条目")
            for i, item in enumerate(chinese_items[:10], 1):
                print(f"  {i}. [{item['path']}] {item['text'][:100]}")
            if len(chinese_items) > 10:
                print(f"  ... 还有 {len(chinese_items) - 10} 个")
        else:
            print("  未找到中文字符")
    
    print("\n" + "="*70)
    print("总结")
    print("="*70)
    
    total = sum(len(items) for items in all_chinese.values())
    print(f"\n总共找到 {total} 个包含中文的条目，分布在 {len(all_chinese)} 个文件中")
    
    for filename, items in all_chinese.items():
        print(f"  {filename}: {len(items)} 条")

if __name__ == '__main__':
    main()

