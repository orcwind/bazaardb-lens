#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从Unity Asset Bundle文件中提取字符串（包括本地化内容）
"""

import os
import sys
import json
import re
from collections import defaultdict

def extract_strings_from_binary(file_path, min_length=2):
    """
    从二进制文件中提取字符串（包括中文）
    """
    strings = []
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 尝试提取UTF-8字符串
        try:
            # 查找UTF-8编码的中文字符串
            # 中文字符在UTF-8中通常是3字节: \xE4-\xEF开头
            pattern = rb'[\xE4-\xEF][\x80-\xBF]{2}+'
            matches = re.finditer(pattern, data)
            
            for match in matches:
                try:
                    text = match.group(0).decode('utf-8')
                    if len(text) >= min_length and any('\u4e00' <= c <= '\u9fff' for c in text):
                        strings.append({
                            'offset': match.start(),
                            'text': text,
                            'encoding': 'utf-8'
                        })
                except:
                    pass
        except:
            pass
        
        # 尝试提取UTF-16字符串（小端序）
        try:
            # UTF-16 LE中文字符范围：0x4E00-0x9FFF
            # 模式：查找连续的UTF-16字符
            text_utf16 = []
            i = 0
            while i < len(data) - 1:
                try:
                    # 读取UTF-16字符
                    char_code = int.from_bytes(data[i:i+2], 'little')
                    if 0x4E00 <= char_code <= 0x9FFF:  # 中文字符范围
                        char = chr(char_code)
                        text_utf16.append(char)
                        i += 2
                        # 继续读取连续的字符
                        while i < len(data) - 1:
                            try:
                                next_char_code = int.from_bytes(data[i:i+2], 'little')
                                if 0x4E00 <= next_char_code <= 0x9FFF or \
                                   (0x0020 <= next_char_code <= 0x007E):  # ASCII范围
                                    if next_char_code == 0:  # 字符串结束
                                        break
                                    text_utf16.append(chr(next_char_code))
                                    i += 2
                                else:
                                    break
                            except:
                                break
                        
                        if len(text_utf16) >= min_length:
                            text = ''.join(text_utf16)
                            strings.append({
                                'offset': i - len(text) * 2,
                                'text': text,
                                'encoding': 'utf-16-le'
                            })
                        text_utf16 = []
                    else:
                        i += 1
                except:
                    i += 1
        except:
            pass
        
        # 去重
        seen = set()
        unique_strings = []
        for s in strings:
            if s['text'] not in seen:
                unique_strings.append(s)
                seen.add(s['text'])
        
        return unique_strings
        
    except Exception as e:
        print(f"错误: {e}")
        return []

def extract_all_text_strings(file_path):
    """
    提取所有可读的文本字符串（包括英文和其他语言）
    """
    all_strings = []
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 尝试作为文本文件读取（查找可打印字符序列）
        current_string = bytearray()
        for i, byte in enumerate(data):
            if 32 <= byte <= 126:  # 可打印ASCII
                current_string.append(byte)
            elif byte in [0x09, 0x0A, 0x0D]:  # 制表符、换行符
                current_string.append(byte)
            else:
                if len(current_string) >= 4:  # 至少4个字符
                    try:
                        text = current_string.decode('utf-8', errors='ignore')
                        if any(c.isprintable() or c.isspace() for c in text):
                            all_strings.append({
                                'offset': i - len(current_string),
                                'text': text,
                                'encoding': 'ascii'
                            })
                    except:
                        pass
                current_string = bytearray()
        
        # 处理最后一个字符串
        if len(current_string) >= 4:
            try:
                text = current_string.decode('utf-8', errors='ignore')
                if any(c.isprintable() or c.isspace() for c in text):
                    all_strings.append({
                        'offset': len(data) - len(current_string),
                        'text': text,
                        'encoding': 'ascii'
                    })
            except:
                pass
        
        return all_strings[:1000]  # 限制数量
        
    except Exception as e:
        return []

def analyze_bundle_file(file_path):
    """分析Unity Asset Bundle文件"""
    print(f"\n{'='*70}")
    print(f"分析文件: {os.path.basename(file_path)}")
    print(f"{'='*70}")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在")
        return None
    
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size:,} 字节 ({file_size / 1024 / 1024:.2f} MB)\n")
    
    # 提取中文字符串
    print("正在提取中文字符串...")
    chinese_strings = extract_strings_from_binary(file_path, min_length=2)
    
    print(f"找到 {len(chinese_strings)} 个中文字符串\n")
    
    if chinese_strings:
        print("中文字符串示例（前30个）:")
        print("-"*70)
        for i, item in enumerate(chinese_strings[:30], 1):
            print(f"{i:3d}. [{item['encoding']}] {item['text']}")
        if len(chinese_strings) > 30:
            print(f"... 还有 {len(chinese_strings) - 30} 个")
    
    # 提取所有文本字符串（查找可能包含本地化关键词的字符串）
    print("\n正在提取所有文本字符串（查找本地化相关内容）...")
    all_strings = extract_all_text_strings(file_path)
    
    # 查找包含本地化关键词的字符串
    localization_keywords = [
        'localization', 'locale', 'language', 'translation', 
        'zh', 'chinese', 'en_gb', 'zh_cn', 'TranslationKey',
        'Locales', 'TextAsset', 'LocalizedString'
    ]
    
    localization_strings = []
    for s in all_strings:
        text_lower = s['text'].lower()
        if any(keyword.lower() in text_lower for keyword in localization_keywords):
            localization_strings.append(s)
    
    print(f"找到 {len(localization_strings)} 个包含本地化关键词的字符串\n")
    
    if localization_strings:
        print("本地化相关字符串示例（前20个）:")
        print("-"*70)
        for i, item in enumerate(localization_strings[:20], 1):
            text_preview = item['text'][:100].replace('\n', ' ').replace('\r', ' ')
            print(f"{i:3d}. {text_preview}")
    
    return {
        'file': os.path.basename(file_path),
        'size': file_size,
        'chinese_strings': chinese_strings,
        'localization_strings': localization_strings[:100],
        'all_strings_count': len(all_strings)
    }

def main():
    base_path = r'C:\Users\vivi\AppData\Roaming\Tempo Launcher - Beta\game\buildx64\TheBazaar_Data\StreamingAssets\aa\StandaloneWindows64'
    
    bundle_files = [
        'board_common__591851dd4e477814891b4440a2834174.bundle',
        'board_thegrand__ba392908159347adf93b7242d6db9dfa.bundle',
        'projectiles__22ed2daa2a4684a04cc98e640823fac7.bundle'
    ]
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        bundle_files = sys.argv[2:]
    
    print("Unity Asset Bundle 字符串提取工具")
    print("="*70)
    print(f"搜索目录: {base_path}\n")
    
    all_results = []
    
    for bundle_file in bundle_files:
        file_path = os.path.join(base_path, bundle_file)
        if os.path.exists(file_path):
            result = analyze_bundle_file(file_path)
            if result:
                all_results.append(result)
        else:
            print(f"\n警告: 文件不存在: {file_path}")
    
    # 总结
    print("\n" + "="*70)
    print("提取总结")
    print("="*70)
    
    total_chinese = sum(len(r['chinese_strings']) for r in all_results)
    total_localization = sum(len(r['localization_strings']) for r in all_results)
    
    print(f"\n处理的文件: {len(all_results)} 个")
    print(f"找到的中文字符串: {total_chinese} 个")
    print(f"找到的本地化相关字符串: {total_localization} 个")
    
    # 保存结果
    output_file = 'bundle_extraction_results.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n保存结果时出错: {e}")
    
    # 如果有中文内容，保存到单独的文件
    if total_chinese > 0:
        chinese_file = 'bundle_chinese_strings.txt'
        try:
            with open(chinese_file, 'w', encoding='utf-8') as f:
                f.write("Unity Asset Bundle 中的中文字符串\n")
                f.write("="*70 + "\n\n")
                
                for result in all_results:
                    if result['chinese_strings']:
                        f.write(f"\n文件: {result['file']}\n")
                        f.write("-"*70 + "\n\n")
                        for i, item in enumerate(result['chinese_strings'], 1):
                            f.write(f"{i:4d}. [{item['encoding']}] {item['text']}\n")
                        f.write("\n")
            
            print(f"中文字符串已保存到: {chinese_file}")
        except Exception as e:
            print(f"保存中文字符串时出错: {e}")

if __name__ == '__main__':
    main()

