#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速搜索游戏中的中文本地化文件
"""

import os
import json

def quick_scan_for_chinese(base_path):
    """快速扫描StaticData目录中的JSON文件，查找中文"""
    static_data_path = os.path.join(base_path, 'StreamingAssets', 'StaticData')
    
    if not os.path.exists(static_data_path):
        print(f"错误: 目录不存在: {static_data_path}")
        return
    
    print("快速扫描StaticData目录...")
    print("="*70)
    
    json_files = [f for f in os.listdir(static_data_path) if f.endswith('.json')]
    print(f"找到 {len(json_files)} 个JSON文件\n")
    
    files_with_chinese = []
    
    for filename in json_files:
        file_path = os.path.join(static_data_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 快速检查是否包含中文
                if any('\u4e00' <= c <= '\u9fff' for c in content):
                    # 尝试解析JSON并提取中文
                    f.seek(0)
                    data = json.load(f)
                    
                    chinese_strings = []
                    def extract_chinese(obj):
                        if isinstance(obj, str) and any('\u4e00' <= c <= '\u9fff' for c in obj) and len(obj) >= 2:
                            chinese_strings.append(obj)
                        elif isinstance(obj, dict):
                            for v in obj.values():
                                extract_chinese(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_chinese(item)
                    
                    extract_chinese(data)
                    
                    if chinese_strings:
                        files_with_chinese.append({
                            'file': filename,
                            'path': file_path,
                            'chinese_count': len(chinese_strings),
                            'samples': chinese_strings[:10]
                        })
                        print(f"✓ {filename}: 找到 {len(chinese_strings)} 个中文字符串")
        except Exception as e:
            pass
    
    print(f"\n总共找到 {len(files_with_chinese)} 个包含中文的文件\n")
    
    if files_with_chinese:
        print("="*70)
        print("详细结果:")
        print("="*70)
        for item in files_with_chinese:
            print(f"\n文件: {item['file']}")
            print(f"中文字符串数量: {item['chinese_count']} 个")
            print("示例内容（前5个）:")
            for i, s in enumerate(item['samples'][:5], 1):
                preview = s[:60].replace('\n', ' ')
                print(f"  {i}. {preview}...")
    
    return files_with_chinese

def check_all_streamingassets(base_path):
    """检查StreamingAssets目录下所有JSON文件"""
    streaming_assets_path = os.path.join(base_path, 'StreamingAssets')
    
    if not os.path.exists(streaming_assets_path):
        return []
    
    print("\n" + "="*70)
    print("扩展搜索: StreamingAssets目录")
    print("="*70 + "\n")
    
    files_with_chinese = []
    
    # 只搜索主要的JSON文件，避免太慢
    important_files = []
    for root, dirs, files in os.walk(streaming_assets_path):
        # 限制深度
        if root.count(os.sep) - streaming_assets_path.count(os.sep) > 2:
            continue
        
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                # 跳过太大的文件（可能不是本地化文件）
                try:
                    if os.path.getsize(file_path) > 5 * 1024 * 1024:  # 5MB
                        continue
                    important_files.append(file_path)
                except:
                    pass
    
    print(f"检查 {len(important_files)} 个JSON文件...")
    
    for file_path in important_files[:50]:  # 限制检查数量
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(50000)  # 只读取前50KB快速检查
                if any('\u4e00' <= c <= '\u9fff' for c in content):
                    rel_path = os.path.relpath(file_path, base_path)
                    files_with_chinese.append(rel_path)
                    print(f"  ✓ {rel_path}")
        except:
            pass
    
    return files_with_chinese

if __name__ == '__main__':
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    print("游戏中文本地化文件快速搜索工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    if not os.path.exists(base_path):
        print(f"错误: 目录不存在")
        sys.exit(1)
    
    # 1. 快速扫描StaticData
    static_results = quick_scan_for_chinese(base_path)
    
    # 2. 扩展搜索
    extended_results = check_all_streamingassets(base_path)
    
    # 总结
    print("\n" + "="*70)
    print("总结")
    print("="*70)
    print(f"\nStaticData目录: {len(static_results)} 个包含中文的文件")
    print(f"StreamingAssets目录: {len(extended_results)} 个可能包含中文的文件")
    
    if static_results or extended_results:
        print("\n建议:")
        print("1. 如果找到了包含中文的文件，这些可能就是本地化文件")
        print("2. 如果没有找到，中文可能存储在Unity的二进制资源文件中")
        print("3. 需要使用UnityPy或AssetStudio等工具来提取Unity资源")


