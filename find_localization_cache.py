#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查找游戏语言包缓存位置（适用于经常更新的游戏）
"""

import os
import sys
import json
from pathlib import Path

def find_localization_caches(base_path):
    """查找可能的本地化缓存位置"""
    locations = []
    
    # 1. Addressables缓存目录
    # Unity Addressables通常缓存远程资源
    addressable_cache_paths = [
        os.path.join(base_path, 'StreamingAssets', 'aa'),
        os.path.join(base_path, 'aa'),
    ]
    
    for cache_path in addressable_cache_paths:
        if os.path.exists(cache_path):
            locations.append({
                'type': 'Addressables缓存',
                'path': cache_path,
                'description': 'Unity Addressables远程资源缓存'
            })
    
    # 2. 玩家数据目录（AppData）
    appdata_local = os.environ.get('LOCALAPPDATA', '')
    appdata_roaming = os.environ.get('APPDATA', '')
    
    # 可能的游戏数据目录
    possible_data_dirs = [
        os.path.join(appdata_local, 'TheBazaar'),
        os.path.join(appdata_local, 'Tempo', 'TheBazaar'),
        os.path.join(appdata_roaming, 'TheBazaar'),
        os.path.join(appdata_roaming, 'Tempo Launcher - Beta'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'TheBazaar'),
    ]
    
    for data_dir in possible_data_dirs:
        if os.path.exists(data_dir):
            # 查找可能的本地化目录
            for root, dirs, files in os.walk(data_dir):
                # 查找包含本地化关键词的目录和文件
                keywords = ['localization', 'locale', 'lang', 'i18n', 'translation', 'zh', 'chinese']
                
                for d in dirs:
                    if any(kw in d.lower() for kw in keywords):
                        dir_path = os.path.join(root, d)
                        locations.append({
                            'type': '数据目录',
                            'path': dir_path,
                            'description': f'在 {data_dir} 中找到的本地化目录'
                        })
                
                # 查找JSON文件
                for file in files:
                    if file.endswith('.json'):
                        file_lower = file.lower()
                        if any(kw in file_lower for kw in keywords):
                            file_path = os.path.join(root, file)
                            try:
                                size = os.path.getsize(file_path)
                                locations.append({
                                    'type': '本地化文件',
                                    'path': file_path,
                                    'size': size,
                                    'description': f'本地化JSON文件'
                                })
                            except:
                                pass
                
                # 限制深度，避免搜索太久
                if root.count(os.sep) - data_dir.count(os.sep) > 3:
                    dirs[:] = []  # 停止深入
    
    # 3. Unity缓存目录
    unity_cache_paths = [
        os.path.join(base_path, 'StreamingAssets', 'aa', 'StandaloneWindows64'),
    ]
    
    for cache_path in unity_cache_paths:
        if os.path.exists(cache_path):
            # 查找可能的本地化bundle文件
            try:
                for file in os.listdir(cache_path):
                    file_lower = file.lower()
                    keywords = ['localization', 'locale', 'lang', 'i18n', 'zh', 'chinese', 'text', 'string']
                    if any(kw in file_lower for kw in keywords):
                        file_path = os.path.join(cache_path, file)
                        try:
                            size = os.path.getsize(file_path)
                            locations.append({
                                'type': 'Unity Bundle',
                                'path': file_path,
                                'size': size,
                                'description': '可能包含本地化的Unity Bundle文件'
                            })
                        except:
                            pass
            except:
                pass
    
    # 4. 检查游戏目录下是否有专门的本地化目录
    localization_dirs = [
        os.path.join(base_path, 'StreamingAssets', 'Localization'),
        os.path.join(base_path, 'StreamingAssets', 'Locales'),
        os.path.join(base_path, 'StreamingAssets', 'Languages'),
        os.path.join(base_path, 'StreamingAssets', 'i18n'),
        os.path.join(base_path, 'Resources', 'Localization'),
        os.path.join(base_path, 'Localization'),
    ]
    
    for loc_dir in localization_dirs:
        if os.path.exists(loc_dir):
            locations.append({
                'type': '本地化目录',
                'path': loc_dir,
                'description': '专门的本地化目录'
            })
    
    return locations

def analyze_remote_localization_possibility():
    """分析是否可能是远程加载的本地化"""
    indicators = []
    
    # 检查是否有网络相关的配置文件
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    # Unity Addressables设置
    settings_path = os.path.join(base_path, 'StreamingAssets', 'aa', 'settings.json')
    if os.path.exists(settings_path):
        indicators.append({
            'type': 'Addressables设置',
            'path': settings_path,
            'description': 'Unity Addressables配置文件，可能配置了远程资源'
        })
    
    # 检查是否有远程URL配置
    config_files = [
        os.path.join(base_path, 'StreamingAssets', 'UnityServicesProjectConfiguration.json'),
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 查找URL相关配置
                    config_str = json.dumps(config)
                    if any(keyword in config_str.lower() for keyword in ['url', 'http', 'cdn', 'remote', 'server']):
                        indicators.append({
                            'type': '远程配置',
                            'path': config_file,
                            'description': '可能包含远程资源URL配置'
                        })
            except:
                pass
    
    return indicators

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    print("游戏本地化缓存位置查找工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    if not os.path.exists(base_path):
        print(f"错误: 目录不存在: {base_path}")
        return
    
    # 1. 查找本地化缓存位置
    print("1. 查找本地化缓存位置...")
    print("-"*70)
    locations = find_localization_caches(base_path)
    
    if locations:
        print(f"找到 {len(locations)} 个可能的本地化位置:\n")
        for i, loc in enumerate(locations, 1):
            print(f"{i}. [{loc['type']}]")
            print(f"   路径: {loc['path']}")
            if 'size' in loc:
                print(f"   大小: {loc['size']:,} 字节 ({loc['size']/1024/1024:.2f} MB)")
            print(f"   说明: {loc['description']}")
            print()
    else:
        print("未找到明显的本地化缓存位置")
    
    # 2. 分析是否可能是远程加载
    print("\n2. 分析远程本地化可能性...")
    print("-"*70)
    remote_indicators = analyze_remote_localization_possibility()
    
    if remote_indicators:
        print(f"找到 {len(remote_indicators)} 个远程加载的指标:\n")
        for i, indicator in enumerate(remote_indicators, 1):
            print(f"{i}. [{indicator['type']}]")
            print(f"   路径: {indicator['path']}")
            print(f"   说明: {indicator['description']}")
            print()
    else:
        print("未找到明显的远程加载配置")
    
    # 3. 总结和建议
    print("\n" + "="*70)
    print("总结和建议")
    print("="*70)
    
    print("\n对于经常更新的多语言游戏，本地化文件通常：")
    print("1. ✅ 存储在StreamingAssets目录（我们已经找到ui_localization.json）")
    print("2. 🌐 从服务器动态下载并缓存到本地")
    print("3. 📦 使用Unity Addressables系统远程加载")
    print("4. 💾 缓存在玩家数据目录中")
    
    print("\n建议检查：")
    print("- 游戏启动时的网络请求（查看是否有语言包下载）")
    print("- Unity Addressables的远程URL配置")
    print("- 游戏更新日志中关于本地化的说明")
    print("- 游戏内语言切换功能的位置（可能在设置中）")
    
    # 保存结果
    results = {
        'locations': locations,
        'remote_indicators': remote_indicators,
        'base_path': base_path
    }
    
    output_file = 'localization_cache_locations.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n保存结果时出错: {e}")

if __name__ == '__main__':
    main()


