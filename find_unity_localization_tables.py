#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查找Unity Localization Package的本地化文件
适用于有官方多语言支持的Unity游戏
"""

import os
import sys
import json
from pathlib import Path

def find_unity_localization_files(base_path):
    """查找Unity Localization Package的本地化文件"""
    results = {
        'localization_tables': [],
        'addressables_localization': [],
        'localization_bundles': [],
        'possible_files': []
    }
    
    # 1. 查找Addressables目录中的本地化文件
    addressable_paths = [
        os.path.join(base_path, 'StreamingAssets', 'aa'),
        os.path.join(base_path, 'StreamingAssets', 'Addressables'),
        os.path.join(base_path, 'StreamingAssets', 'AddressableAssetsData'),
    ]
    
    for aa_path in addressable_paths:
        if os.path.exists(aa_path):
            print(f"\n检查Addressables目录: {aa_path}")
            # 查找所有可能的本地化文件
            for root, dirs, files in os.walk(aa_path):
                for file in files:
                    file_lower = file.lower()
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, base_path)
                    
                    # 查找本地化相关的文件
                    if any(kw in file_lower for kw in ['localization', 'locale', 'lang', 'i18n', 'translation']):
                        try:
                            size = os.path.getsize(file_path)
                            file_ext = os.path.splitext(file)[1].lower()
                            
                            file_info = {
                                'path': file_path,
                                'relative_path': relative_path,
                                'size': size,
                                'ext': file_ext,
                                'name': file
                            }
                            
                            if file_ext == '.bundle':
                                results['localization_bundles'].append(file_info)
                            elif file_ext in ['.asset', '.bytes']:
                                results['localization_tables'].append(file_info)
                            else:
                                results['addressables_localization'].append(file_info)
                        except:
                            pass
    
    # 2. 查找StreamingAssets中的所有可能文件
    sa_path = os.path.join(base_path, 'StreamingAssets')
    if os.path.exists(sa_path):
        print(f"\n检查StreamingAssets目录...")
        for root, dirs, files in os.walk(sa_path):
            # 跳过已经检查过的目录
            if 'aa' in root or 'Addressables' in root:
                continue
            
            for file in files:
                file_lower = file.lower()
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, base_path)
                
                # 查找包含语言标识的文件（特别是中文）
                if any(kw in file_lower for kw in ['zh', 'chinese', 'cn', 'zh-cn', 'zh_cn']):
                    try:
                        size = os.path.getsize(file_path)
                        file_ext = os.path.splitext(file)[1].lower()
                        
                        file_info = {
                            'path': file_path,
                            'relative_path': relative_path,
                            'size': size,
                            'ext': file_ext,
                            'name': file
                        }
                        results['possible_files'].append(file_info)
                    except:
                        pass
    
    # 3. 查找所有.bundle文件（可能是本地化bundle）
    bundle_files = []
    sa_path = os.path.join(base_path, 'StreamingAssets', 'aa')
    if os.path.exists(sa_path):
        for root, dirs, files in os.walk(sa_path):
            for file in files:
                if file.endswith('.bundle'):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        # 检查文件名是否可能包含本地化内容
                        file_lower = file.lower()
                        if any(kw in file_lower for kw in ['localization', 'locale', 'lang', 'text', 'string', 'i18n']):
                            bundle_files.append({
                                'path': file_path,
                                'relative_path': os.path.relpath(file_path, base_path),
                                'size': size,
                                'name': file
                            })
                    except:
                        pass
    
    results['localization_bundles'].extend(bundle_files)
    
    return results

def analyze_ui_localization_structure():
    """分析ui_localization.json的结构，了解本地化系统"""
    file_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\StaticData\ui_localization.json'
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n分析ui_localization.json结构...")
        print(f"总条目数: {len(data)}")
        
        # 检查结构
        if isinstance(data, list) and len(data) > 0:
            sample = data[0]
            print(f"\n示例条目结构:")
            print(json.dumps(sample, ensure_ascii=False, indent=2))
            
            # 检查是否所有条目都只有en_gb
            all_locales = set()
            for item in data[:100]:  # 检查前100个
                if isinstance(item, dict) and 'Locales' in item:
                    all_locales.update(item['Locales'].keys())
            
            print(f"\n前100个条目中的语言键: {sorted(all_locales)}")
            
            # 说明
            if len(all_locales) == 1 and 'en_gb' in all_locales:
                print("\n⚠️ 说明: 文件中只有英文键值对")
                print("   如果游戏显示中文，可能：")
                print("   1. 使用Unity Localization Package，翻译存储在.asset文件中")
                print("   2. 翻译通过Addressables远程加载")
                print("   3. 翻译存储在单独的bundle文件中")
                print("   4. 游戏运行时动态替换翻译键")
    except Exception as e:
        print(f"分析失败: {e}")
    
    return None

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data'
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    print("Unity Localization Package 本地化文件查找工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    if not os.path.exists(base_path):
        print(f"错误: 目录不存在: {base_path}")
        return
    
    # 查找本地化文件
    results = find_unity_localization_files(base_path)
    
    # 显示结果
    print("\n" + "="*70)
    print("查找结果")
    print("="*70)
    
    total_found = sum(len(v) for v in results.values())
    print(f"\n总共找到 {total_found} 个可能的本地化文件\n")
    
    # 显示各个类别
    if results['localization_tables']:
        print(f"本地化Tables (.asset/.bytes): {len(results['localization_tables'])} 个")
        for item in results['localization_tables']:
            print(f"  - {item['relative_path']} ({item['size']:,} 字节)")
    
    if results['localization_bundles']:
        print(f"\n本地化Bundle文件: {len(results['localization_bundles'])} 个")
        for item in results['localization_bundles']:
            print(f"  - {item['relative_path']} ({item['size']:,} 字节, {item['size']/1024/1024:.2f} MB)")
    
    if results['addressables_localization']:
        print(f"\nAddressables本地化文件: {len(results['addressables_localization'])} 个")
        for item in results['addressables_localization'][:20]:
            print(f"  - {item['relative_path']} ({item['size']:,} 字节)")
        if len(results['addressables_localization']) > 20:
            print(f"  ... 还有 {len(results['addressables_localization']) - 20} 个")
    
    if results['possible_files']:
        print(f"\n包含中文标识的文件: {len(results['possible_files'])} 个")
        for item in results['possible_files']:
            print(f"  - {item['relative_path']} ({item['size']:,} 字节)")
    
    # 分析ui_localization.json
    analyze_ui_localization_structure()
    
    # 保存结果
    output_file = 'unity_localization_files.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n保存结果时出错: {e}")
    
    # 建议
    print("\n" + "="*70)
    print("建议")
    print("="*70)
    print("\n对于Unity游戏，特别是使用Unity Localization Package的：")
    print("1. 翻译可能存储在Unity的.asset文件（ScriptableObject）中")
    print("2. 需要使用UnityPy或AssetStudio等工具来提取")
    print("3. 或者翻译通过Addressables远程加载，需要查看网络请求")
    print("4. 如果游戏有官方中文版本，翻译应该已经集成，可能：")
    print("   - 在单独的本地化bundle中")
    print("   - 使用Unity Localization Package的Tables")
    print("   - 通过运行时加载替换en_gb的文本")

if __name__ == '__main__':
    main()

