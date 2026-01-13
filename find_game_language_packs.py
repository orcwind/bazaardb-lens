#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查找游戏目录中的语言包文件
"""

import os
import sys
from pathlib import Path

def find_language_pack_files(root_dir, extensions=None):
    """
    在指定目录中查找语言包文件
    
    Args:
        root_dir: 搜索的根目录
        extensions: 要搜索的文件扩展名列表，默认搜索常见语言包格式
    """
    if extensions is None:
        extensions = ['.pak', '.json', '.txt', '.xml', '.strings', '.po', '.locale']
    
    # 语言包相关的关键词
    language_keywords = [
        'language', 'lang', 'localization', 'locale', 'i18n',
        'zh', 'chinese', 'zh-CN', 'zh-CN', 'zh_CN', 'chinese',
        'strings', 'text', 'translation', 'l10n'
    ]
    
    results = {
        'pak_files': [],
        'language_files': [],
        'potential_files': []
    }
    
    print(f"正在搜索: {root_dir}\n")
    
    if not os.path.exists(root_dir):
        print(f"错误: 目录不存在: {root_dir}")
        return results
    
    # 遍历目录
    for root, dirs, files in os.walk(root_dir):
        # 跳过一些明显不相关的目录
        skip_dirs = ['Cache', 'Cache_Data', 'Code Cache', 'GPUCache', 'DawnCache', 
                     '__pycache__', 'node_modules', '.git', 'Logs', 'Temp']
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            file_lower = file.lower()
            relative_path = os.path.relpath(file_path, root_dir)
            
            # 检查扩展名
            file_ext = os.path.splitext(file)[1].lower()
            
            # PAK文件
            if file_ext == '.pak':
                results['pak_files'].append({
                    'path': file_path,
                    'relative_path': relative_path,
                    'size': os.path.getsize(file_path),
                    'name': file
                })
                print(f"✓ 找到PAK文件: {relative_path} ({os.path.getsize(file_path)} 字节)")
            
            # 检查是否是语言相关文件
            is_language_file = False
            if any(keyword in file_lower for keyword in language_keywords):
                is_language_file = True
            
            # 检查扩展名是否匹配
            if file_ext in extensions or is_language_file:
                file_info = {
                    'path': file_path,
                    'relative_path': relative_path,
                    'size': os.path.getsize(file_path),
                    'name': file,
                    'extension': file_ext
                }
                
                if is_language_file:
                    results['language_files'].append(file_info)
                    print(f"→ 语言文件: {relative_path}")
                else:
                    results['potential_files'].append(file_info)
    
    return results

def main():
    # 默认搜索路径（从截图看的位置）
    default_paths = [
        r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game',
        r'C:\Users\vivi\AppData\Local\Tempo\TheBazaar',
        r'C:\Users\vivi\AppData\Roaming\TheBazaar',
        # Steam路径
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Steam', 'steamapps', 'common', 'TheBazaar'),
    ]
    
    # 如果提供了命令行参数，使用该路径
    if len(sys.argv) > 1:
        search_paths = [sys.argv[1]]
    else:
        search_paths = default_paths
    
    all_results = {}
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            print(f"\n{'='*70}")
            print(f"搜索目录: {search_path}")
            print(f"{'='*70}\n")
            
            results = find_language_pack_files(search_path)
            all_results[search_path] = results
            
            print(f"\n搜索结果:")
            print(f"  PAK文件: {len(results['pak_files'])} 个")
            print(f"  语言文件: {len(results['language_files'])} 个")
            print(f"  其他可能文件: {len(results['potential_files'])} 个")
        else:
            print(f"\n跳过不存在的目录: {search_path}")
    
    # 汇总结果
    print(f"\n{'='*70}")
    print("汇总结果")
    print(f"{'='*70}\n")
    
    total_pak = sum(len(r['pak_files']) for r in all_results.values())
    total_lang = sum(len(r['language_files']) for r in all_results.values())
    
    if total_pak > 0:
        print(f"找到 {total_pak} 个PAK文件:")
        for search_path, results in all_results.items():
            for pak in results['pak_files']:
                print(f"  - {pak['relative_path']} ({pak['size']} 字节)")
    
    if total_lang > 0:
        print(f"\n找到 {total_lang} 个语言相关文件:")
        for search_path, results in all_results.items():
            for lang_file in results['language_files'][:20]:  # 只显示前20个
                print(f"  - {lang_file['relative_path']}")
            if len(results['language_files']) > 20:
                print(f"  ... 还有 {len(results['language_files']) - 20} 个文件")
    
    # 重点关注的目录
    print(f"\n建议重点查看以下目录:")
    print(f"  1. game/TheBazaar_Data/StreamingAssets/")
    print(f"  2. game/TheBazaar_Data/Resources/")
    print(f"  3. game/ 目录下查找包含 'locale', 'language', 'lang', 'i18n' 的文件夹")

if __name__ == '__main__':
    print("游戏语言包文件查找工具\n")
    main()


