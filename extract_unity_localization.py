#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提取Unity游戏中的本地化内容
"""

import os
import sys
import json
import struct
from pathlib import Path
from collections import defaultdict

def find_unity_files(base_path, extensions=None):
    """查找Unity相关文件"""
    if extensions is None:
        extensions = ['.asset', '.bytes', '.resources', '.bundle', '.txt']
    
    unity_files = []
    
    for root, dirs, files in os.walk(base_path):
        # 跳过一些不相关的目录
        skip_dirs = ['Cache', 'Cache_Data', 'Code Cache', 'GPUCache', 
                     'DawnCache', '__pycache__', '.git']
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in extensions:
                file_path = os.path.join(root, file)
                unity_files.append({
                    'path': file_path,
                    'relative_path': os.path.relpath(file_path, base_path),
                    'size': os.path.getsize(file_path),
                    'name': file,
                    'ext': file_ext
                })
    
    return unity_files

def read_text_file(file_path):
    """尝试以文本方式读取文件，查找中文内容"""
    try:
        # 尝试UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except:
        try:
            # 尝试UTF-16
            with open(file_path, 'r', encoding='utf-16') as f:
                content = f.read()
                return content
        except:
            try:
                # 尝试GBK（中文编码）
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                    return content
            except:
                return None
    return None

def extract_chinese_from_text(content):
    """从文本中提取中文内容"""
    if not content:
        return []
    
    chinese_strings = []
    import re
    
    # 查找中文字符串（至少2个字符）
    pattern = r'[\u4e00-\u9fff]{2,}'
    matches = re.findall(pattern, content)
    
    # 去重并过滤
    seen = set()
    for match in matches:
        if match not in seen and len(match) >= 2:
            chinese_strings.append(match)
            seen.add(match)
    
    return chinese_strings

def analyze_unity_asset_file(file_path):
    """分析Unity .asset文件（尝试读取文本部分）"""
    results = {
        'has_text': False,
        'chinese_count': 0,
        'chinese_strings': [],
        'readable': False
    }
    
    try:
        # Unity .asset文件可能包含文本
        content = read_text_file(file_path)
        if content:
            results['readable'] = True
            results['has_text'] = True
            
            # 检查是否包含中文
            chinese = extract_chinese_from_text(content)
            results['chinese_count'] = len(chinese)
            results['chinese_strings'] = chinese[:50]  # 只保存前50个
    except Exception as e:
        pass
    
    return results

def search_in_addressables(base_path):
    """在Addressables目录中搜索本地化文件"""
    aa_path = os.path.join(base_path, 'StreamingAssets', 'aa')
    if not os.path.exists(aa_path):
        return []
    
    results = []
    
    # 查找可能的本地化文件
    for root, dirs, files in os.walk(aa_path):
        for file in files:
            file_lower = file.lower()
            if any(keyword in file_lower for keyword in ['localization', 'locale', 'lang', 'i18n', 'zh', 'chinese']):
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    results.append({
                        'path': file_path,
                        'relative_path': os.path.relpath(file_path, base_path),
                        'size': size,
                        'name': file
                    })
                except:
                    pass
    
    return results

def search_in_streaming_assets(base_path):
    """在StreamingAssets中搜索可能的本地化文件"""
    sa_path = os.path.join(base_path, 'StreamingAssets')
    if not os.path.exists(sa_path):
        return []
    
    localization_files = []
    
    # 查找包含本地化关键词的文件和目录
    keywords = ['localization', 'locale', 'lang', 'i18n', 'zh', 'chinese', 'translation']
    
    for root, dirs, files in os.walk(sa_path):
        # 检查目录名
        for d in dirs:
            if any(kw in d.lower() for kw in keywords):
                dir_path = os.path.join(root, d)
                localization_files.append({
                    'type': 'directory',
                    'path': dir_path,
                    'relative_path': os.path.relpath(dir_path, base_path),
                    'name': d
                })
        
        # 检查文件名
        for file in files:
            file_lower = file.lower()
            if any(kw in file_lower for kw in keywords):
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    localization_files.append({
                        'type': 'file',
                        'path': file_path,
                        'relative_path': os.path.relpath(file_path, base_path),
                        'size': size,
                        'name': file
                    })
                except:
                    pass
    
    return localization_files

def extract_from_json_file(file_path):
    """从JSON文件中提取所有可能的本地化内容"""
    results = {
        'chinese_strings': [],
        'keys': [],
        'structure': None
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def extract_all_strings(obj, path=''):
            """递归提取所有字符串"""
            if isinstance(obj, str):
                # 检查是否包含中文
                if any('\u4e00' <= c <= '\u9fff' for c in obj) and len(obj) >= 2:
                    results['chinese_strings'].append({
                        'path': path,
                        'text': obj
                    })
                results['keys'].append(path)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}" if path else k
                    extract_all_strings(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    extract_all_strings(item, new_path)
        
        extract_all_strings(data)
        results['structure'] = type(data).__name__
        
    except Exception as e:
        pass
    
    return results

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    print("Unity本地化内容提取工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    if not os.path.exists(base_path):
        print(f"错误: 目录不存在: {base_path}")
        return
    
    all_results = {
        'unity_files': [],
        'localization_files': [],
        'addressable_files': [],
        'chinese_content': []
    }
    
    # 1. 查找Unity资源文件
    print("1. 查找Unity资源文件...")
    unity_files = find_unity_files(base_path)
    print(f"   找到 {len(unity_files)} 个Unity资源文件")
    
    # 显示前20个
    for f in unity_files[:20]:
        print(f"   - {f['relative_path']} ({f['size']:,} 字节)")
    if len(unity_files) > 20:
        print(f"   ... 还有 {len(unity_files) - 20} 个文件")
    
    all_results['unity_files'] = unity_files
    
    # 2. 在Addressables中搜索
    print("\n2. 在Addressables目录中搜索...")
    aa_files = search_in_addressables(base_path)
    print(f"   找到 {len(aa_files)} 个可能的本地化文件")
    for f in aa_files:
        print(f"   - {f['relative_path']} ({f['size']:,} 字节)")
    
    all_results['addressable_files'] = aa_files
    
    # 3. 在StreamingAssets中搜索
    print("\n3. 在StreamingAssets中搜索本地化相关内容...")
    sa_files = search_in_streaming_assets(base_path)
    print(f"   找到 {len(sa_files)} 个可能的本地化文件/目录")
    for item in sa_files[:20]:
        print(f"   - [{item['type']}] {item['relative_path']}")
    if len(sa_files) > 20:
        print(f"   ... 还有 {len(sa_files) - 20} 个")
    
    all_results['localization_files'] = sa_files
    
    # 4. 分析已找到的JSON文件中的中文
    print("\n4. 分析JSON文件中的中文内容...")
    json_files = [f for f in unity_files if f['ext'] == '.txt' or 'json' in f['name'].lower()]
    json_files.append({
        'path': os.path.join(base_path, 'StreamingAssets', 'StaticData', 'ui_localization.json'),
        'relative_path': 'StreamingAssets/StaticData/ui_localization.json'
    })
    
    total_chinese = 0
    for f_info in json_files:
        if os.path.exists(f_info['path']):
            try:
                result = extract_from_json_file(f_info['path'])
                if result['chinese_strings']:
                    print(f"   {f_info['relative_path']}: 找到 {len(result['chinese_strings'])} 个中文字符串")
                    total_chinese += len(result['chinese_strings'])
                    all_results['chinese_content'].extend(result['chinese_strings'])
            except:
                pass
    
    # 5. 尝试从.asset文件中提取文本
    print("\n5. 分析Unity .asset文件（查找可读文本）...")
    asset_files = [f for f in unity_files if f['ext'] == '.asset']
    readable_assets = []
    
    for f_info in asset_files[:50]:  # 限制处理数量
        result = analyze_unity_asset_file(f_info['path'])
        if result['readable']:
            readable_assets.append(f_info['relative_path'])
            if result['chinese_count'] > 0:
                print(f"   {f_info['relative_path']}: 找到 {result['chinese_count']} 个中文字符串")
                total_chinese += result['chinese_count']
                all_results['chinese_content'].extend([
                    {'path': f_info['relative_path'], 'text': s} 
                    for s in result['chinese_strings']
                ])
    
    if readable_assets:
        print(f"   找到 {len(readable_assets)} 个可读的.asset文件")
    else:
        print("   未找到可读的.asset文件（可能需要专门的工具）")
    
    # 总结
    print("\n" + "="*70)
    print("提取总结")
    print("="*70)
    print(f"Unity资源文件: {len(unity_files)} 个")
    print(f"Addressable本地化文件: {len(aa_files)} 个")
    print(f"StreamingAssets本地化文件: {len(sa_files)} 个")
    print(f"找到的中文字符串: {total_chinese} 个")
    
    # 保存结果
    output_file = 'unity_localization_extraction.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存到: {output_file}")
    
    # 如果有中文内容，保存到单独的文件
    if all_results['chinese_content']:
        chinese_file = 'unity_chinese_strings.txt'
        with open(chinese_file, 'w', encoding='utf-8') as f:
            f.write("Unity游戏中的中文字符串\n")
            f.write("="*70 + "\n\n")
            for i, item in enumerate(all_results['chinese_content'], 1):
                f.write(f"{i:4d}. [{item.get('path', 'N/A')}]\n")
                f.write(f"     {item['text']}\n\n")
        print(f"中文字符串已保存到: {chinese_file}")

if __name__ == '__main__':
    main()


