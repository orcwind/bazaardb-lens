#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从HTML中提取物品和技能的品质信息
品质信息在HTML中以CSS变量的形式存在：border-color:var(--bronze/silver/gold/diamond/legendary)
"""

import re
import json
import time
import requests
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ITEMS_JSON = BASE_DIR / 'data' / 'Json' / 'items.json'
SKILLS_JSON = BASE_DIR / 'data' / 'Json' / 'skills.json'


# 品质映射：英文 -> 中文
QUALITY_MAP = {
    'bronze': '青铜',
    'silver': '白银',
    'gold': '黄金',
    'diamond': '钻石',
    'legendary': '传说'
}

# 反向映射：中文 -> 英文
QUALITY_REVERSE_MAP = {v: k for k, v in QUALITY_MAP.items()}


def extract_quality_from_html(html_content):
    """从HTML内容中提取品质信息
    
    Args:
        html_content: HTML字符串
        
    Returns:
        品质字符串（中文）：'青铜'、'白银'、'黄金'、'钻石'、'传说'，如果未找到返回 None
    """
    if not html_content:
        return None
    
    # 方法1: 查找 border-color:var(--quality) 格式
    # 支持多种格式：border-color:var(--bronze)、border-color:var(--silver) 等
    quality_pattern = r'border-color\s*:\s*var\(--(bronze|silver|gold|diamond|legendary)\)'
    match = re.search(quality_pattern, html_content, re.IGNORECASE)
    
    if match:
        quality_en = match.group(1).lower()
        return QUALITY_MAP.get(quality_en)
    
    # 方法2: 查找 style 属性中的品质信息
    # 提取所有包含 border-color 的 style 属性
    style_pattern = r'style=["\'][^"\']*border-color\s*:\s*var\(--(bronze|silver|gold|diamond|legendary)\)[^"\']*["\']'
    matches = re.findall(style_pattern, html_content, re.IGNORECASE)
    
    if matches:
        quality_en = matches[0].lower()
        return QUALITY_MAP.get(quality_en)
    
    # 方法3: 在HTML中查找品质关键词（中文）
    for quality_zh in QUALITY_MAP.values():
        if quality_zh in html_content:
            # 检查是否在相关的上下文中（避免误匹配）
            quality_pattern_zh = rf'(?:品质|等级|rarity|tier)[^>]*{quality_zh}'
            if re.search(quality_pattern_zh, html_content, re.IGNORECASE):
                return quality_zh
    
    return None


def fetch_html_from_url(url, timeout=10, retries=3):
    """从URL获取HTML内容
    
    Args:
        url: 目标URL
        timeout: 超时时间（秒）
        retries: 重试次数
        
    Returns:
        HTML字符串，如果失败返回 None
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))  # 递增延迟
            else:
                print(f"  警告：获取 {url} 失败: {e}")
                return None
    return None


def extract_quality_from_url(url):
    """从URL获取HTML并提取品质信息
    
    Args:
        url: 目标URL
        
    Returns:
        品质字符串（中文），如果未找到返回 None
    """
    html_content = fetch_html_from_url(url)
    if html_content:
        return extract_quality_from_html(html_content)
    return None


def update_json_with_quality(json_path, delay=0.5, dry_run=False):
    """更新JSON文件，为每个条目添加品质信息
    
    Args:
        json_path: JSON文件路径
        delay: 请求间隔（秒）
        dry_run: 如果为True，只显示会执行的操作，不实际更新
        
    Returns:
        更新统计信息
    """
    print(f"\n处理文件: {json_path}")
    
    # 读取JSON数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print(f"  错误：JSON数据不是数组格式")
        return {'total': 0, 'updated': 0, 'failed': 0, 'skipped': 0}
    
    stats = {
        'total': len(data),
        'updated': 0,
        'failed': 0,
        'skipped': 0,
        'no_url': 0
    }
    
    for idx, item in enumerate(data, 1):
        item_name = item.get('name', '') or item.get('name_en', '')
        url = item.get('url', '')
        existing_quality = item.get('quality', '')
        
        # 如果已经有品质信息，跳过
        if existing_quality:
            stats['skipped'] += 1
            if idx % 10 == 0:
                print(f"  进度: {idx}/{stats['total']} (已跳过: {stats['skipped']})")
            continue
        
        # 如果没有URL，跳过
        if not url:
            stats['no_url'] += 1
            if idx % 10 == 0:
                print(f"  进度: {idx}/{stats['total']} (无URL: {stats['no_url']})")
            continue
        
        if dry_run:
            print(f"  [{idx}/{stats['total']}] {item_name}: 将从 {url} 提取品质")
            continue
        
        # 提取品质信息
        print(f"  [{idx}/{stats['total']}] {item_name}...", end='')
        quality = extract_quality_from_url(url)
        
        if quality:
            item['quality'] = quality
            stats['updated'] += 1
            print(f" ✓ {quality}")
        else:
            stats['failed'] += 1
            print(f" ✗ 未找到品质信息")
        
        # 延迟以避免请求过快
        if idx < stats['total']:
            time.sleep(delay)
        
        if idx % 10 == 0:
            print(f"    统计: 已更新 {stats['updated']}, 失败 {stats['failed']}, 跳过 {stats['skipped']}")
    
    # 保存更新后的JSON
    if not dry_run and stats['updated'] > 0:
        print(f"\n正在保存更新后的文件...")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 已保存")
    
    return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从HTML中提取物品和技能的品质信息')
    parser.add_argument('--items', action='store_true', help='处理 items.json')
    parser.add_argument('--skills', action='store_true', help='处理 skills.json')
    parser.add_argument('--all', action='store_true', help='处理所有JSON文件')
    parser.add_argument('--dry-run', action='store_true', help='只显示会执行的操作，不实际更新')
    parser.add_argument('--delay', type=float, default=0.5, help='请求间隔（秒），默认0.5')
    
    args = parser.parse_args()
    
    # 默认处理所有文件
    if not args.items and not args.skills:
        args.all = True
    
    total_stats = {'total': 0, 'updated': 0, 'failed': 0, 'skipped': 0, 'no_url': 0}
    
    if args.all or args.items:
        stats = update_json_with_quality(ITEMS_JSON, delay=args.delay, dry_run=args.dry_run)
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    if args.all or args.skills:
        stats = update_json_with_quality(SKILLS_JSON, delay=args.delay, dry_run=args.dry_run)
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    # 显示总统计
    print(f"\n{'='*50}")
    print(f"总计统计:")
    print(f"  总数: {total_stats['total']}")
    print(f"  已更新: {total_stats['updated']}")
    print(f"  失败: {total_stats['failed']}")
    print(f"  跳过（已有品质）: {total_stats['skipped']}")
    print(f"  无URL: {total_stats['no_url']}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
