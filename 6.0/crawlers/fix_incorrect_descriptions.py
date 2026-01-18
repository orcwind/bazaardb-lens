#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复明显错误的物品描述
"""

import json
import re
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup

# 文件路径
ITEMS_JSON = Path(__file__).parent.parent.parent / 'data' / 'Json' / 'items.json'

# HTTP请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}
REQUEST_TIMEOUT = 15


def fetch_description_from_detail_page(item_url):
    """从物品详情页获取描述信息"""
    try:
        # 确保URL包含中文语言参数
        if '?lang=' not in item_url and '&lang=' not in item_url:
            separator = '&' if '?' in item_url else '?'
            item_url = f"{item_url}{separator}lang=zh"
        
        response = requests.get(item_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 附魔关键词（用于过滤）
        enchant_keywords = ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded', 'Restorative', 
                           'Toxic', 'Fiery', 'Shiny', 'Deadly', 'Radiant', 'Obsidian',
                           '黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', 
                           '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
        
        # 描述特征模式
        description_patterns = [
            r'\d+\.\d+\s*»?\s*\d*\.?\d*\s*秒',
            r'\d+\s*»\s*\d+\s*»\s*\d+',
            r'摧毁|充能|减速|加速|伤害|护盾|治疗|冻结|剧毒|灼烧',
        ]
        
        descriptions = []
        
        # 优先查找 _bw、_bx 类的 div
        for class_name in ['_bw', '_bx']:
            desc_divs = soup.find_all('div', class_=lambda x: x and class_name in str(x) if x else False)
            for div in desc_divs:
                text = div.get_text(separator='', strip=False)
                text = text.replace('\xa0', ' ')
                
                # 规范化空格格式
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', text)
                text = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', text)
                text = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', text)
                text = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', text)
                text = re.sub(r' {2,}', ' ', text).strip()
                
                if len(text) > 5:
                    if any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History', 'Offered by', 
                                                      'Dropped by', 'Found in', 'Level', 'Day']):
                        continue
                    
                    has_enchant_symbol = '❯' in text or '→' in text
                    enchant_count = sum(1 for keyword in enchant_keywords if keyword in text)
                    
                    if has_enchant_symbol or enchant_count >= 2:
                        continue
                    
                    has_desc_pattern = any(re.search(pattern, text) for pattern in description_patterns)
                    has_effect_keywords = any(keyword in text for keyword in [
                        '摧毁', '充能', '减速', '加速', '伤害', '护盾', '治疗', '冻结',
                        '使用', '获得', '每有', '每场', '相邻', '左侧', '右侧', '多重触发',
                        '出售', '购买', '最大生命值', '收入', '价值', '重掷', '服饰'
                    ])
                    
                    if not has_enchant_symbol and enchant_count < 2:
                        if (has_desc_pattern or has_effect_keywords or (len(text) > 5 and len(text) < 500)):
                            if text not in descriptions:
                                descriptions.append(text)
            
            if descriptions:
                unique_descriptions = []
                seen = set()
                for desc in descriptions:
                    normalized = re.sub(r'\s+', ' ', desc.strip())
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_descriptions.append(desc)
                result = ' '.join(unique_descriptions)
                return clean_description(result)
        
        return ''
    except Exception as e:
        print(f"  错误: {e}")
        return ''


def clean_description(text):
    """清理描述文本"""
    if not text:
        return text
    
    # 移除 Types 标签
    text = re.sub(r'Types[A-Za-z]+\s*', '', text)
    
    # 移除版本号、Hotfix信息等
    text = re.sub(r'\d+\.\d+\.\d+\s*Hotfix#\d+', '', text)
    text = re.sub(r'\d+\.\d+\s*Hotfix#\d+', '', text)
    text = re.sub(r'Hotfix#\d+', '', text)
    
    # 移除类型信息（如 Bronze+ItemSmallCommon）
    text = re.sub(r'[A-Za-z]+\+Item[A-Za-z]+\s*', '', text)
    text = re.sub(r'[A-Za-z]+\+Item\s*', '', text)
    
    # 移除单独出现的 "gold"（如果只是类型标识）
    text = re.sub(r'\b(gold|Gold|GOLD)\b\s*$', '', text)
    
    # 规范化空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def fix_incorrect_descriptions():
    """修复明显错误的物品描述"""
    print("=" * 80)
    print("修复明显错误的物品描述")
    print("=" * 80)
    
    # 加载数据
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    items_map = {item['name']: item for item in items}
    
    # 明显错误的物品（包含版本号、类型信息等）
    incorrect_items = [
        'Bag of Jewels',    # 包含版本号
        'Bar of Gold',      # 包含类型信息
        'Pelt',             # 包含版本号和类型信息
        'Spare Change',     # 包含版本号和类型信息
    ]
    
    # 需要重新获取的物品（描述可能不完整或错误）
    items_to_refetch = incorrect_items
    
    print(f"\n需要修复的物品: {len(items_to_refetch)} 个\n")
    
    fixed = 0
    failed = []
    
    for item_name in items_to_refetch:
        if item_name not in items_map:
            print(f"❌ {item_name}: 未找到")
            failed.append(item_name)
            continue
        
        item = items_map[item_name]
        url = item.get('url', '')
        current_desc = item.get('description_zh', '')
        
        if not url:
            print(f"❌ {item_name}: 无URL")
            failed.append(item_name)
            continue
        
        print(f"处理: {item_name}")
        print(f"  当前描述: {current_desc[:150]}")
        
        # 重新获取描述
        description = fetch_description_from_detail_page(url)
        
        if description:
            item['description_zh'] = description
            print(f"  ✓ 描述已更新: {description[:150]}")
            fixed += 1
        else:
            print(f"  ✗ 未找到描述")
            failed.append(item_name)
        
        print()
        time.sleep(0.5)
    
    # 保存结果
    print(f"\n保存结果...")
    all_items = list(items_map.values())
    all_items.sort(key=lambda x: x.get('name', ''))
    
    with open(ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("修复完成")
    print("=" * 80)
    print(f"成功修复: {fixed} 个")
    if failed:
        print(f"失败: {len(failed)} 个")
        for name in failed:
            print(f"  - {name}")
    print("=" * 80)


if __name__ == '__main__':
    fix_incorrect_descriptions()
