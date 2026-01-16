#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析所有 HTML 文件中的 /card/随机码/name 模式，找出规律
"""
from pathlib import Path
import re
import json
from urllib.parse import unquote
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).resolve().parents[0]
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'card_patterns_analysis.json'

def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    normalized = n.lower().replace('-', ' ').replace('_', ' ').replace(' ', ' ')
    normalized = ' '.join(normalized.split())
    return normalized

def is_english_only(text):
    """检查是否只包含英文"""
    if not text:
        return False
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return False
    if '\\' in text or text.startswith('page-') or '.js' in text:
        return False
    if len(text) < 2 or len(text) > 100:
        return False
    if text.replace('-', '').replace('_', '').replace(' ', '').isalnum() == False:
        return False
    return True

def clean_name(n):
    """清理名称"""
    n = n.rstrip('\\').strip()
    return n.strip()

def extract_all_card_names(html_path):
    """从单个 HTML 文件中提取所有 /card/随机码/name 模式"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    card_names = []
    
    # 方法1: 使用正则表达式提取
    card_pattern = r'/card/[a-zA-Z0-9]+/([^/<>"\'\s?&#]+)'
    matches = re.findall(card_pattern, html)
    for match in matches:
        try:
            decoded = unquote(match)
            decoded = decoded.split('?')[0].split('#')[0].split('/')[0]
            if decoded:
                card_names.append(decoded)
        except Exception:
            pass
    
    # 方法2: 从 DOM 的 a[href] 中提取
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if '/card/' in href and href.count('/card/') == 1:
            parts = href.split('/card/')
            if len(parts) > 1:
                rest = parts[1]
                path_parts = rest.split('/')
                if len(path_parts) >= 2:
                    name_part = path_parts[1]
                    try:
                        decoded = unquote(name_part.split('?')[0].split('#')[0].split('/')[0])
                        if decoded and decoded not in card_names:
                            card_names.append(decoded)
                    except Exception:
                        pass
    
    # 过滤和清理
    english_names = []
    for n in card_names:
        cleaned = clean_name(n)
        if is_english_only(cleaned):
            english_names.append(cleaned)
    
    return english_names

def analyze_patterns():
    """分析所有 HTML 文件中的模式"""
    html_files = sorted(HTML_DIR.glob('*.html'))
    
    all_results = []
    name_frequency = Counter()
    name_positions = defaultdict(list)  # 记录每个名称在列表中的位置模式
    
    for html_file in html_files:
        print(f"分析: {html_file.name}")
        card_names = extract_all_card_names(html_file)
        
        # 统计名称频率
        for name in card_names:
            name_frequency[name] += 1
        
        # 分析位置模式
        normalized_names = [normalize_name(n) for n in card_names]
        for i, name in enumerate(normalized_names):
            name_positions[name].append(i)
        
        all_results.append({
            'file': html_file.name,
            'total_count': len(card_names),
            'unique_count': len(set(card_names)),
            'names': card_names,
            'normalized_names': normalized_names
        })
    
    # 分析重复模式
    pattern_analysis = {
        'total_files': len(html_files),
        'name_frequency': dict(name_frequency.most_common(50)),  # 最常见的50个名称
        'duplicate_patterns': {}
    }
    
    # 分析每个文件的重复模式
    for result in all_results:
        file_name = result['file']
        names = result['names']
        normalized = result['normalized_names']
        
        # 检查是否有重复模式
        patterns = {
            'total': len(names),
            'unique': len(set(names)),
            'has_duplicates': len(names) != len(set(names)),
            'duplicate_groups': {}
        }
        
        # 找出重复的名称组
        name_groups = defaultdict(list)
        for i, name in enumerate(normalized):
            name_groups[name].append(i)
        
        for name, positions in name_groups.items():
            if len(positions) > 1:
                patterns['duplicate_groups'][name] = {
                    'count': len(positions),
                    'positions': positions
                }
        
        pattern_analysis['duplicate_patterns'][file_name] = patterns
    
    # 保存分析结果
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': pattern_analysis,
            'detailed_results': all_results[:10]  # 只保存前10个文件的详细结果
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n分析完成！结果保存到: {OUTPUT_JSON}")
    print(f"\n统计信息:")
    print(f"  总文件数: {len(html_files)}")
    print(f"  最常见的名称: {name_frequency.most_common(10)}")
    
    # 分析重复模式
    duplicate_files = [f for f, p in pattern_analysis['duplicate_patterns'].items() if p['has_duplicates']]
    print(f"\n有重复的文件数: {len(duplicate_files)}")
    
    # 分析重复倍数
    duplicate_counts = Counter()
    for file_name, patterns in pattern_analysis['duplicate_patterns'].items():
        if patterns['has_duplicates']:
            for name, group in patterns['duplicate_groups'].items():
                duplicate_counts[group['count']] += 1
    
    print(f"\n重复倍数统计:")
    for count, freq in duplicate_counts.most_common():
        print(f"  {count}倍重复: {freq} 次")
    
    return pattern_analysis

if __name__ == '__main__':
    analyze_patterns()
