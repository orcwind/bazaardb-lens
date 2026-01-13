#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看游戏语言包文件内容
"""

import json
import os
import sys
from collections import defaultdict

def analyze_language_pack(file_path):
    """分析语言包文件"""
    print(f"\n{'='*70}")
    print(f"分析文件: {file_path}")
    print(f"{'='*70}\n")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return None
    
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size} 字节\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            print(f"文件类型: JSON数组")
            print(f"项目数量: {len(data)}\n")
            
            # 统计所有语言
            all_locales = set()
            for item in data:
                if isinstance(item, dict) and 'Locales' in item:
                    all_locales.update(item['Locales'].keys())
            
            print(f"支持的语言 ({len(all_locales)} 种):")
            for locale in sorted(all_locales):
                print(f"  - {locale}")
            print()
            
            # 查找中文相关
            chinese_keys = ['zh', 'chinese', 'cn', 'zh-cn', 'zh_cn', 'zh-CN', 'zh_CN']
            chinese_items = []
            
            for item in data:
                if isinstance(item, dict) and 'Locales' in item:
                    locales = item['Locales']
                    # 检查是否有中文语言
                    has_chinese = any(key.lower() in [c.lower() for c in chinese_keys] 
                                     for key in locales.keys())
                    if has_chinese:
                        chinese_items.append(item)
                    # 也检查内容是否包含中文
                    for locale, text in locales.items():
                        if isinstance(text, str) and any('\u4e00' <= c <= '\u9fff' for c in text):
                            if item not in chinese_items:
                                chinese_items.append(item)
            
            print(f"找到中文相关内容: {len(chinese_items)} 项\n")
            
            # 显示前20个中文项
            if chinese_items:
                print("中文内容示例（前20个）:")
                print("-" * 70)
                for i, item in enumerate(chinese_items[:20], 1):
                    print(f"{i:3d}. TranslationKey: {item.get('TranslationKey', 'N/A')}")
                    if 'Locales' in item:
                        for locale, text in item['Locales'].items():
                            # 检查是否是中文或包含中文
                            if any(c.lower() in locale.lower() for c in chinese_keys) or \
                               (isinstance(text, str) and any('\u4e00' <= c <= '\u9fff' for c in text)):
                                print(f"     {locale}: {text}")
                    if 'Context' in item:
                        print(f"     上下文: {item['Context']}")
                    print()
            
            # 按场景统计
            if any('Context' in item for item in data):
                scene_stats = defaultdict(int)
                for item in data:
                    if isinstance(item, dict) and 'Context' in item:
                        scene = item['Context'].get('Scene', 'Unknown')
                        scene_stats[scene] += 1
                
                print(f"\n按场景统计（前10个）:")
                for scene, count in sorted(scene_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {scene}: {count} 条")
            
            return {
                'type': 'array',
                'count': len(data),
                'locales': sorted(all_locales),
                'chinese_items': len(chinese_items),
                'data': data[:100] if len(data) > 100 else data  # 保存前100项用于预览
            }
        else:
            print(f"文件类型: {type(data)}")
            if isinstance(data, dict):
                print(f"JSON键: {list(data.keys())}")
            print(f"内容预览: {str(data)[:500]}")
            return {'type': type(data).__name__, 'data': data}
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\StaticData'
    
    files_to_check = [
        'embeddedLocales.json',
        'ui_localization.json'
    ]
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    results = {}
    
    for filename in files_to_check:
        file_path = os.path.join(base_path, filename)
        result = analyze_language_pack(file_path)
        if result:
            results[filename] = result
    
    # 生成摘要报告
    print(f"\n{'='*70}")
    print("摘要报告")
    print(f"{'='*70}\n")
    
    for filename, result in results.items():
        print(f"{filename}:")
        if 'locales' in result:
            print(f"  - 支持 {len(result['locales'])} 种语言")
            print(f"  - 找到 {result['chinese_items']} 个中文相关项")
        print()

if __name__ == '__main__':
    print("游戏语言包查看工具\n")
    main()


