#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细分析游戏本地化文件，查找所有语言
"""

import json
import os
import sys
from collections import defaultdict

def analyze_localization_file(file_path):
    """详细分析本地化文件"""
    print(f"\n{'='*70}")
    print(f"详细分析: {file_path}")
    print(f"{'='*70}\n")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"文件大小: {os.path.getsize(file_path):,} 字节")
    print(f"条目总数: {len(data)}\n")
    
    # 统计所有语言
    all_locales = set()
    locale_stats = defaultdict(int)
    
    for item in data:
        if isinstance(item, dict) and 'Locales' in item:
            locales = item['Locales']
            all_locales.update(locales.keys())
            for locale in locales.keys():
                locale_stats[locale] += 1
    
    print(f"发现的语言 ({len(all_locales)} 种):")
    for locale in sorted(all_locales):
        count = locale_stats[locale]
        print(f"  {locale:10s}: {count:4d} 条翻译")
    print()
    
    # 检查是否有中文（通过语言键）
    chinese_locale_keys = ['zh_cn', 'zh-CN', 'zh-CN', 'zh_CN', 'chinese', 'zh']
    has_chinese_key = any(any(key in locale.lower() for key in chinese_locale_keys) 
                          for locale in all_locales)
    
    # 检查是否有中文内容（通过字符）
    chinese_items = []
    for item in data:
        if isinstance(item, dict) and 'Locales' in item:
            locales = item['Locales']
            for locale, text in locales.items():
                if isinstance(text, str):
                    # 检查是否包含中文字符
                    if any('\u4e00' <= c <= '\u9fff' for c in text):
                        chinese_items.append({
                            'key': item.get('TranslationKey'),
                            'locale': locale,
                            'text': text,
                            'context': item.get('Context', {})
                        })
    
    print(f"包含中文字符的条目: {len(chinese_items)} 条\n")
    
    if chinese_items:
        print("中文内容示例（前30条）:")
        print("-" * 70)
        for i, item in enumerate(chinese_items[:30], 1):
            print(f"{i:3d}. [{item['locale']}] {item['text']}")
            if item['context']:
                print(f"     场景: {item['context'].get('Scene', 'N/A')}, 类型: {item['context'].get('Type', 'N/A')}")
        print()
        
        # 按语言键分组统计
        locale_text_counts = defaultdict(int)
        for item in chinese_items:
            locale_text_counts[item['locale']] += 1
        
        print("中文内容按语言键统计:")
        for locale, count in sorted(locale_text_counts.items()):
            print(f"  {locale}: {count} 条")
        print()
    
    # 显示一些示例条目，包括所有语言
    print("示例条目（显示所有语言）:")
    print("-" * 70)
    for i, item in enumerate(data[:5], 1):
        print(f"\n条目 {i}:")
        print(f"  TranslationKey: {item.get('TranslationKey', 'N/A')}")
        if 'Locales' in item:
            print(f"  Locales:")
            for locale, text in item['Locales'].items():
                print(f"    {locale}: {text}")
        if 'Context' in item:
            print(f"  Context: {item['Context']}")
    
    return {
        'total': len(data),
        'locales': sorted(all_locales),
        'locale_stats': dict(locale_stats),
        'chinese_items_count': len(chinese_items),
        'chinese_items': chinese_items[:100]  # 保存前100条
    }

def main():
    file_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\StaticData\ui_localization.json'
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    print("游戏本地化文件详细分析工具\n")
    result = analyze_localization_file(file_path)
    
    if result:
        print(f"\n{'='*70}")
        print("分析总结")
        print(f"{'='*70}\n")
        print(f"总条目数: {result['total']}")
        print(f"支持语言: {len(result['locales'])} 种")
        print(f"包含中文的条目: {result['chinese_items_count']} 条")
        print(f"\n语言统计:")
        for locale, count in sorted(result['locale_stats'].items()):
            print(f"  {locale}: {count} 条")

if __name__ == '__main__':
    main()

