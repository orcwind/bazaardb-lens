#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试物品描述在HTML中的位置
"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# 测试物品列表
test_items = [
    {
        'name': 'Oblivion Vortex',
        'url': 'https://bazaardb.gg/card/4oqbjmk5klqh6148bg9km7qmf/Oblivion-Vortex',
        'expected_desc': '9.0»7.0秒,摧毁最左侧的物品。为其他物品充能，数值为被摧毁物品冷却时间的一半。'
    },
    {
        'name': 'Relay Drone',
        'url': 'https://bazaardb.gg/card/8f6g590mubx2anfenz8nqnpso/Relay-Drone',
        'expected_desc': '5.0 秒 为另1 » 2 » 3件物品充能2秒。'
    },
    {
        'name': 'Attachment Set',
        'url': 'https://bazaardb.gg/card/2903i2mywojh8lwx53add3lp4/Attachment-Set',
        'expected_desc': '使用非武器工具时，造成25 » 50 » 100伤害。使用武器工具时，获得25 » 50 » 100护盾。'
    }
]

def find_description_in_html(html_content, item_name, expected_desc):
    """在HTML中查找描述文本的位置"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    print(f"\n{'='*80}")
    print(f"测试物品: {item_name}")
    print(f"期望描述: {expected_desc[:100]}...")
    print(f"{'='*80}")
    
    # 方法1: 查找所有包含关键字的元素
    keywords = ['9.0', '7.0', '5.0', '摧毁', '充能', '使用', '造成', '伤害', '护盾']
    found_elements = []
    
    for keyword in keywords:
        if keyword in expected_desc:
            # 查找包含该关键字的元素
            elements = soup.find_all(string=re.compile(re.escape(keyword), re.IGNORECASE))
            for elem in elements[:3]:  # 只显示前3个
                parent = elem.parent
                if parent:
                    tag_name = parent.name
                    classes = parent.get('class', [])
                    text = parent.get_text(strip=True)[:200]
                    found_elements.append({
                        'keyword': keyword,
                        'tag': tag_name,
                        'class': classes,
                        'text': text
                    })
    
    if found_elements:
        print(f"\n找到 {len(found_elements)} 个包含关键字的元素:")
        for i, elem in enumerate(found_elements[:5], 1):
            print(f"  [{i}] 关键字: {elem['keyword']}")
            print(f"      Tag: {elem['tag']}, Class: {elem['class']}")
            print(f"      文本: {elem['text'][:150]}")
            print()
    
    # 方法2: 查找所有可能的描述容器
    print("\n查找所有可能的描述容器:")
    
    # 查找 _bM 类
    desc_divs = soup.find_all('div', class_='_bM')
    print(f"  _bM divs: {len(desc_divs)} 个")
    for i, div in enumerate(desc_divs[:3], 1):
        text = div.get_text(strip=True)
        print(f"    [{i}] {text[:150]}")
    
    # 查找 _bq 类
    desc_divs_bq = soup.find_all('div', class_=lambda x: x and '_bq' in str(x) if x else False)
    print(f"  _bq divs: {len(desc_divs_bq)} 个")
    for i, div in enumerate(desc_divs_bq[:3], 1):
        text = div.get_text(strip=True)
        print(f"    [{i}] {text[:150]}")
    
    # 查找包含数字和秒的元素
    print("\n查找包含 '数字.数字秒' 格式的元素:")
    cooldown_pattern = r'\d+\.\d+\s*»?\s*\d*\.?\d*\s*秒'
    all_text = soup.get_text()
    matches = re.finditer(cooldown_pattern, all_text)
    for i, match in enumerate(list(matches)[:3], 1):
        start = max(0, match.start() - 50)
        end = min(len(all_text), match.end() + 100)
        context = all_text[start:end]
        print(f"    [{i}] ...{context}...")
    
    # 方法3: 查找所有div，检查哪些包含描述特征
    print("\n查找包含描述特征的div:")
    description_keywords = ['摧毁', '充能', '减速', '加速', '伤害', '护盾', '使用', '造成', '获得']
    desc_divs_all = soup.find_all('div')
    found_desc_divs = []
    
    for div in desc_divs_all:
        text = div.get_text(strip=True)
        if len(text) > 20 and len(text) < 500:
            keyword_count = sum(1 for kw in description_keywords if kw in text)
            if keyword_count >= 2:  # 包含至少2个描述关键词
                classes = div.get('class', [])
                found_desc_divs.append({
                    'class': classes,
                    'text': text[:200]
                })
    
    if found_desc_divs:
        print(f"  找到 {len(found_desc_divs)} 个可能的描述div:")
        for i, div_info in enumerate(found_desc_divs[:5], 1):
            print(f"    [{i}] Class: {div_info['class']}")
            print(f"        文本: {div_info['text']}")
            print()


def main():
    """主函数"""
    for item in test_items:
        url = item['url']
        # 添加中文参数
        if '?lang=' not in url and '&lang=' not in url:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}lang=zh"
        
        try:
            print(f"\n正在访问: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            find_description_in_html(response.text, item['name'], item['expected_desc'])
            
        except Exception as e:
            print(f"❌ 访问失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
