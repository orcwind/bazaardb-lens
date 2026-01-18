#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查物品描述是否有明显错误
注意：这个脚本只能检查明显错误（如Types、Ammo等），无法验证正确性
真正验证正确性需要人工检查或使用不同的提取方法
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


def fetch_description_from_page(url):
    """从网页获取描述"""
    try:
        if '?lang=' not in url and '&lang=' not in url:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}lang=zh"
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取主描述
        desc_divs = soup.find_all('div', class_=lambda x: x and ('_bw' in str(x) or '_bx' in str(x)) if x else False)
        descriptions = []
        
        for div in desc_divs:
            text = div.get_text(separator='', strip=False).replace('\xa0', ' ').strip()
            if len(text) > 5 and len(text) < 500:
                if not any(skip in text for skip in ['Tags', 'Cost', 'Value', 'History', 'Enchantments']):
                    if '❯' not in text and '→' not in text:
                        descriptions.append(text)
        
        if descriptions:
            return ' '.join(descriptions[:3])  # 取前3个可能的描述
        
        return ''
    except Exception as e:
        return f"错误: {e}"


def check_description_quality(desc):
    """检查描述质量，返回问题列表"""
    issues = []
    
    if not desc or desc.strip() == '':
        issues.append('描述为空')
        return issues
    
    # 检查是否包含不应该出现的内容
    if re.search(r'Types[A-Za-z]', desc):
        issues.append('包含Types标签')
    
    if 'Ammo:' in desc:
        issues.append('包含Ammo标签')
    
    # 检查是否包含附魔错误信息
    enchant_zh = ['黄金', '沉重', '寒冰', '疾速', '护盾', '回复', '毒性蔓延', '毒素', '炽焰', '闪亮', '致命', '辉耀', '黑曜石']
    if re.search(rf'({"|".join(enchant_zh)}).*(Can\'t|can\'t|cannot).*be.*enchanted.*with', desc, re.I):
        issues.append('包含附魔错误信息')
    
    # 检查描述长度
    if len(desc) < 5:
        issues.append('描述过短')
    elif len(desc) > 1000:
        issues.append('描述过长（可能包含多余内容）')
    
    # 检查是否包含明显的关键词（说明可能是有效描述）
    valid_keywords = ['秒', '伤害', '护盾', '治疗', '物品', '使用', '获得', '造成', '相邻', '左侧', '右侧', 
                     '充能', '减速', '加速', '冻结', '剧毒', '灼烧', '暴击', '多重触发', '出售', '购买']
    has_valid_keywords = any(keyword in desc for keyword in valid_keywords)
    
    if not has_valid_keywords and len(desc) > 10:
        issues.append('缺少有效关键词（可能不是描述）')
    
    return issues


def compare_descriptions(json_desc, web_desc):
    """对比两个描述，返回相似度评分和差异"""
    if not json_desc and not web_desc:
        return 1.0, '两者都为空'
    
    if not json_desc:
        return 0.0, 'JSON描述为空'
    
    if not web_desc:
        return 0.5, '网页描述为空（无法对比）'
    
    # 标准化描述（去除空格、标点差异）
    def normalize(text):
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 统一 » 符号周围的空格
        text = re.sub(r'\s*»\s*', '»', text)
        return text.strip().lower()
    
    json_norm = normalize(json_desc)
    web_norm = normalize(web_desc)
    
    # 计算相似度（简单方法：共同字符比例）
    if len(json_norm) == 0 or len(web_norm) == 0:
        return 0.0, '标准化后为空'
    
    # 检查是否包含相同的关键部分
    json_key_parts = set(re.findall(r'[\u4e00-\u9fff]+|\d+\.?\d*', json_norm))
    web_key_parts = set(re.findall(r'[\u4e00-\u9fff]+|\d+\.?\d*', web_norm))
    
    if len(json_key_parts) == 0 or len(web_key_parts) == 0:
        return 0.0, '无法提取关键部分'
    
    common_parts = json_key_parts & web_key_parts
    similarity = len(common_parts) / max(len(json_key_parts), len(web_key_parts))
    
    # 检查长度差异
    length_diff = abs(len(json_norm) - len(web_norm)) / max(len(json_norm), len(web_norm))
    
    # 综合评分
    final_score = similarity * 0.7 + (1 - min(length_diff, 0.5)) * 0.3
    
    diff_note = ''
    if similarity < 0.5:
        diff_note = '关键部分差异较大'
    elif length_diff > 0.3:
        diff_note = f'长度差异较大（JSON: {len(json_desc)}, 网页: {len(web_desc)}）'
    elif final_score > 0.8:
        diff_note = '基本一致'
    else:
        diff_note = '部分一致'
    
    return final_score, diff_note


def verify_items(items_to_check=None):
    """检查物品描述是否有明显错误"""
    print("=" * 80)
    print("检查物品描述错误")
    print("=" * 80)
    print("\n⚠ 注意：这个脚本只能检查明显错误（如Types、Ammo等）")
    print("⚠ 无法验证描述的正确性，正确性需要通过人工检查验证\n")
    
    # 加载数据
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    items_map = {item['name']: item for item in items}
    
    # 要验证的物品列表
    if items_to_check is None:
        # 检查所有物品
        items_to_check = list(items_map.keys())
        print(f"检查所有 {len(items_to_check)} 个物品...\n")
    else:
        print(f"检查指定的 {len(items_to_check)} 个物品...\n")
    
    results = {
        'correct': [],
        'issues': [],
        'warnings': []
    }
    
    for item_name in items_to_check:
        if item_name not in items_map:
            print(f"⚠ {item_name}: 未在JSON中找到\n")
            continue
        
        item = items_map[item_name]
        url = item.get('url', '')
        json_desc = item.get('description_zh', '')
        
        if not url:
            print(f"⚠ {item_name}: 无URL\n")
            continue
        
        # 1. 检查描述质量
        quality_issues = check_description_quality(json_desc)
        
        # 2. 只检查明显错误，不对比网页（因为对比也无法验证正确性）
        if len(quality_issues) > 0:
            if len(items_to_check) <= 50:
                print(f"检查: {item_name}")
                print(f"  ❌ 发现问题: {', '.join(quality_issues)}")
                print(f"  描述: {json_desc[:150] if json_desc else '(空)'}")
                print()
            results['issues'].append({
                'name': item_name,
                'json_desc': json_desc,
                'quality_issues': quality_issues,
                'url': url
            })
        else:
            results['correct'].append(item_name)
        
        # 只在检查少量物品时显示详细信息
        if len(items_to_check) <= 50 and len(quality_issues) == 0:
            print(f"检查: {item_name}")
            print(f"  ✓ 无明显错误")
            print()
        
        # 对于所有物品的检查，不需要每次请求网页（太慢）
        # 只检查JSON中的明显错误即可
        if len(items_to_check) > 50:
            # 大量检查时，跳过网页请求（只检查明显错误）
            pass
        else:
            print()
            time.sleep(0.3)  # 避免请求过快
    
    # 总结
    print("=" * 80)
    print("检查完成")
    print("=" * 80)
    print(f"✓ 无明显错误: {len(results['correct'])} 个（但仍需人工验证）")
    print(f"❌ 发现明显错误: {len(results['issues'])} 个")
    
    if results['issues']:
        print("\n错误详情（需要修复）:")
        for item in results['issues']:
            print(f"\n  {item['name']}:")
            print(f"    错误类型: {', '.join(item['quality_issues'])}")
            print(f"    当前描述: {item['json_desc'][:200]}")
            print(f"    URL: {item['url']}")
    
    # 显示进度（如果是大量检查）
    if len(items_to_check) > 50:
        print(f"\n检查进度: {len(items_to_check)} 个物品")
        print(f"  - 完成检查: {len(results['correct']) + len(results['issues'])} 个")
        print(f"  - 明显错误: {len(results['issues'])} 个")
        print(f"  - 无明显错误: {len(results['correct'])} 个")
    
    print("\n⚠ 重要提示：")
    print("  - 这个脚本只能检查明显错误（Types、Ammo、附魔信息等）")
    print("  - 无法验证描述的正确性")
    print("  - 建议随机抽样人工检查一些物品的描述是否正确")
    print("=" * 80)
    
    return results


if __name__ == '__main__':
    verify_items()
