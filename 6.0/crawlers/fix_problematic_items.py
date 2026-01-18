#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复有问题的物品描述
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}
REQUEST_TIMEOUT = 15


def clean_description(text):
    """清理描述文本，移除元数据和附魔信息"""
    if not text:
        return text
    
    # 移除 Types 标签（如 TypesWeapon, TypesProperty, TypesVehicle 等）
    text = re.sub(r'Types[A-Za-z]+\s*', '', text)
    
    # 移除 Ammo: 标签及其数值
    text = re.sub(r'Ammo:\s*\d+\s*(»\s*\d+)*\s*', '', text, flags=re.IGNORECASE)
    
    # 移除 "Can't be enchanted with" 相关文本
    enchant_zh_names_pattern = '黄金|沉重|寒冰|疾速|护盾|回复|毒性蔓延|毒素|炽焰|闪亮|致命|辉耀|黑曜石'
    # 模式1：中文附魔名称 + Can't be enchanted with + 中文附魔名称
    text = re.sub(rf'({enchant_zh_names_pattern})\s*(Can\'t|can\'t|cannot)\s*be\s*enchanted\s*with\s*({enchant_zh_names_pattern})\.?\s*', '', text, flags=re.IGNORECASE)
    # 模式2：Can't be enchanted with + 中文附魔名称
    text = re.sub(rf'(Can\'t|can\'t|cannot)\s*be\s*enchanted\s*with\s*({enchant_zh_names_pattern})\.?\s*', '', text, flags=re.IGNORECASE)
    
    # 规范化空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def fetch_description_from_detail_page(item_url):
    """从物品详情页获取描述信息（排除附魔信息）"""
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
                
                if len(text) > 10:
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
                        '使用', '获得', '每有', '每场', '相邻', '左侧', '右侧', '多重触发'
                    ])
                    
                    if not has_enchant_symbol and enchant_count < 2:
                        # 降低长度要求，允许更短的描述（如"可出售换得金币。"）
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
        
        # 如果没找到，尝试其他方法
        page_text = soup.get_text()
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        
        description_lines = []
        in_description = False
        skip_keywords = ['Offered by', 'Dropped by', 'Found in', 'Level', 'Day', 
                       'Enchantments', 'Tier', 'Size', 'Types', 'Tags']
        
        for line in lines:
            if any(skip in line for skip in skip_keywords):
                continue
            
            enchant_count = sum(1 for keyword in enchant_keywords if keyword in line)
            if enchant_count >= 2:
                if in_description:
                    break
                continue
            
            is_description_start = False
            if not in_description and len(line) > 5:
                if re.search(r'\d+\.\d+\s*»?\s*\d*\.?\d*\s*秒', line):
                    is_description_start = True
                elif any(keyword in line for keyword in ['摧毁', '充能', '减速', '加速', '造成', 
                                                        '获得', '使用', '伤害', '治疗', '护盾']):
                    is_description_start = True
            
            if is_description_start and enchant_count < 2:
                in_description = True
                description_lines.append(line)
            elif in_description:
                if any(stop in line for stop in ['Enchantments', 'Golden', 'Heavy']) and len(line) < 30:
                    break
                elif enchant_count >= 2:
                    break
                elif len(line) > 5 and len(line) < 500:
                    description_lines.append(line)
                elif len(line) >= 500:
                    break
        
        if description_lines:
            result = ' '.join(description_lines)
            result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3»\4秒', result)
            result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2»\3秒', result)
            result = re.sub(r'(\d+\.?\d*)\s*»\s*(\d+\.?\d*)\s*秒', r'\1»\2秒', result)
            result = re.sub(r'(\d+)\s*»\s*(\d+)\s*»\s*(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2 » \3 » \4', result)
            result = re.sub(r'(\d+)\s+»\s+(\d+)\s+»\s+(\d+)(?!\s*秒)', r'\1 » \2 » \3', result)
            result = re.sub(r'(\d+)\s*»\s*(\d+)(?!\s*秒)', r'\1 » \2', result)
            result = re.sub(r' {2,}', ' ', result).strip()
            return clean_description(result)
        
        return ''
    except Exception as e:
        print(f"  错误: {e}")
        return ''


def fix_problematic_items():
    """修复有问题的物品"""
    print("=" * 80)
    print("修复有问题的物品描述")
    print("=" * 80)
    
    # 加载数据
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    items_map = {item['name']: item for item in items}
    
    # 问题物品列表
    missing_desc = ['Chunk of Gold', 'Green Piggles A', 'Langxian', 'Pickled Peppers', 
                   'SMG', 'Sands of Time', 'Sapphire', 'Spiked Buckler', 'Stinger']
    
    has_types = ['Robotic Factory', 'Tournament Arena']
    
    has_enchant_error = ['Agility Boots', 'Crypto', 'Orbital Polisher']
    
    all_problems = missing_desc + has_types + has_enchant_error
    
    print(f"\n需要修复的物品: {len(all_problems)} 个\n")
    
    fixed = 0
    failed = []
    
    for item_name in all_problems:
        if item_name not in items_map:
            print(f"❌ {item_name}: 未找到")
            failed.append(item_name)
            continue
        
        item = items_map[item_name]
        url = item.get('url', '')
        
        if not url:
            print(f"❌ {item_name}: 无URL")
            failed.append(item_name)
            continue
        
        print(f"处理: {item_name}")
        
        # 如果是缺失描述或需要清理，重新获取描述
        if item_name in missing_desc or item_name in has_types or item_name in has_enchant_error:
            # 对于已知的简单描述，先尝试直接设置
            known_descriptions = {
                'Chunk of Gold': '可出售换得金币。',
                'Robotic Factory': '伙伴+1多重触发。',
                'Tournament Arena': '玩具+1多重触发。'
            }
            
            if item_name in known_descriptions:
                item['description_zh'] = known_descriptions[item_name]
                print(f"  ✓ 描述已设置: {known_descriptions[item_name]}")
                fixed += 1
            else:
                description = fetch_description_from_detail_page(url)
                
                if description:
                    item['description_zh'] = description
                    print(f"  ✓ 描述已更新: {description[:80]}...")
                    fixed += 1
                else:
                    print(f"  ✗ 未找到描述")
                    failed.append(item_name)
        
        # 避免请求过快
        time.sleep(0.3)
    
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
    fix_problematic_items()
