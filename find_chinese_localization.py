#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面搜索游戏目录中的所有JSON文件，查找中文本地化内容
"""

import os
import sys
import json
from collections import defaultdict

def search_chinese_in_json_files(base_path):
    """在所有JSON文件中搜索中文内容"""
    results = {
        'files_with_chinese': [],
        'chinese_strings_by_file': {},
        'total_chinese_strings': 0
    }
    
    print("正在搜索所有JSON文件...")
    print("="*70)
    
    json_files = []
    
    # 收集所有JSON文件
    for root, dirs, files in os.walk(base_path):
        # 跳过一些不相关的目录
        skip_dirs = ['Cache', 'Cache_Data', 'Code Cache', 'GPUCache', 'DawnCache']
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.lower().endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    json_files.append({
                        'path': file_path,
                        'relative_path': os.path.relpath(file_path, base_path),
                        'size': size,
                        'name': file
                    })
                except:
                    pass
    
    print(f"找到 {len(json_files)} 个JSON文件\n")
    
    # 分析每个JSON文件
    files_with_chinese = []
    
    for i, file_info in enumerate(json_files, 1):
        if i % 50 == 0:
            print(f"已处理 {i}/{len(json_files)} 个文件...")
        
        try:
            with open(file_info['path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 递归查找中文字符串
            chinese_strings = []
            file_has_chinese = False
            
            def extract_chinese_strings(obj, path=''):
                nonlocal file_has_chinese
                if isinstance(obj, str):
                    # 检查是否包含中文字符
                    if any('\u4e00' <= c <= '\u9fff' for c in obj) and len(obj) >= 2:
                        file_has_chinese = True
                        chinese_strings.append({
                            'path': path,
                            'text': obj
                        })
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        new_path = f"{path}.{k}" if path else k
                        extract_chinese_strings(v, new_path)
                elif isinstance(obj, list):
                    for idx, item in enumerate(obj):
                        new_path = f"{path}[{idx}]" if path else f"[{idx}]"
                        extract_chinese_strings(item, new_path)
            
            extract_chinese_strings(data)
            
            if file_has_chinese:
                files_with_chinese.append({
                    'file': file_info,
                    'chinese_count': len(chinese_strings),
                    'strings': chinese_strings[:100]  # 只保存前100个
                })
                results['chinese_strings_by_file'][file_info['relative_path']] = chinese_strings[:100]
                results['total_chinese_strings'] += len(chinese_strings)
                
        except Exception as e:
            # 如果文件无法解析为JSON，跳过
            pass
    
    results['files_with_chinese'] = files_with_chinese
    
    return results

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    print("游戏中文本地化文件搜索工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    if not os.path.exists(base_path):
        print(f"错误: 目录不存在: {base_path}")
        return
    
    # 搜索中文内容
    results = search_chinese_in_json_files(base_path)
    
    # 显示结果
    print("\n" + "="*70)
    print("搜索结果")
    print("="*70)
    
    files_with_chinese = results['files_with_chinese']
    print(f"\n找到 {len(files_with_chinese)} 个包含中文的JSON文件")
    print(f"总共找到 {results['total_chinese_strings']} 个中文字符串\n")
    
    if files_with_chinese:
        print("包含中文的文件列表:")
        print("-"*70)
        
        for item in files_with_chinese:
            file_info = item['file']
            print(f"\n文件: {file_info['relative_path']}")
            print(f"  大小: {file_info['size']:,} 字节 ({file_info['size']/1024:.2f} KB)")
            print(f"  中文字符串数量: {item['chinese_count']} 个")
            
            # 显示前10个中文字符串示例
            if item['strings']:
                print(f"  中文内容示例（前10个）:")
                for i, s in enumerate(item['strings'][:10], 1):
                    text_preview = s['text'][:80].replace('\n', ' ').replace('\r', ' ')
                    print(f"    {i:2d}. [{s['path']}] {text_preview}")
                if item['chinese_count'] > 10:
                    print(f"    ... 还有 {item['chinese_count'] - 10} 个")
    
    # 重点检查可能的本地化文件
    print("\n" + "="*70)
    print("重点检查可能的本地化文件")
    print("="*70)
    
    localization_keywords = ['localization', 'locale', 'lang', 'i18n', 'translation', 'ui', 'text', 'string']
    
    localization_files = []
    for item in files_with_chinese:
        file_name = item['file']['name'].lower()
        if any(kw in file_name for kw in localization_keywords):
            localization_files.append(item)
    
    if localization_files:
        print(f"\n找到 {len(localization_files)} 个可能的本地化文件:\n")
        for item in localization_files:
            print(f"  ✓ {item['file']['relative_path']}")
            print(f"    包含 {item['chinese_count']} 个中文字符串")
    else:
        print("\n未找到明确标记为本地化的文件")
        print("但找到了以下包含中文的文件（可能是本地化文件）:\n")
        for item in files_with_chinese[:10]:
            print(f"  - {item['file']['relative_path']} ({item['chinese_count']} 个中文字符串)")
        if len(files_with_chinese) > 10:
            print(f"  ... 还有 {len(files_with_chinese) - 10} 个文件")
    
    # 保存结果
    output_file = 'chinese_localization_files.json'
    output_txt_file = 'chinese_localization_strings.txt'
    
    try:
        # 保存JSON格式结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n结果已保存到: {output_file}")
        
        # 保存文本格式的中文字符串
        if files_with_chinese:
            with open(output_txt_file, 'w', encoding='utf-8') as f:
                f.write("游戏中文本地化字符串\n")
                f.write("="*70 + "\n\n")
                
                for item in files_with_chinese:
                    file_info = item['file']
                    f.write(f"\n文件: {file_info['relative_path']}\n")
                    f.write(f"大小: {file_info['size']:,} 字节\n")
                    f.write(f"中文字符串数量: {item['chinese_count']} 个\n")
                    f.write("-"*70 + "\n\n")
                    
                    for i, s in enumerate(item['strings'], 1):
                        f.write(f"{i:4d}. [{s['path']}]\n")
                        f.write(f"     {s['text']}\n\n")
                    
                    f.write("\n" + "="*70 + "\n\n")
            
            print(f"中文字符串已保存到: {output_txt_file}")
    
    except Exception as e:
        print(f"\n保存结果时出错: {e}")

if __name__ == '__main__':
    main()


