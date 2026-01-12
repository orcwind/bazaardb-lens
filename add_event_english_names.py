#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为events_from_html.json补充事件的英文名称
"""

import json
import urllib.parse
import re

def load_english_names():
    """加载英文名称列表"""
    with open('data/Json/events_only_list.json', 'r', encoding='utf-8') as f:
        content = f.read().strip()
        # 尝试解析为JSON数组
        try:
            english_names = json.loads(content)
            if isinstance(english_names, list):
                return english_names
        except:
            pass
        
        # 如果不是JSON数组，可能是每行一个字符串的格式
        # 格式可能是: "A Strange Mushroom"\n"Advanced Training"...
        lines = content.split('\n')
        english_names = []
        for line in lines:
            line = line.strip()
            if line:
                # 移除引号
                if line.startswith('"') and line.endswith('"'):
                    english_names.append(line[1:-1])
                elif line.startswith("'") and line.endswith("'"):
                    english_names.append(line[1:-1])
                else:
                    english_names.append(line)
        return english_names

def extract_name_from_url(url):
    """从URL中提取名称（可能是中文或英文）"""
    try:
        # URL格式: https://bazaardb.gg/card/{id}/{name}
        parts = url.split('/')
        if len(parts) >= 5:
            name_part = parts[-1]
            # URL解码
            decoded = urllib.parse.unquote(name_part)
            return decoded
    except:
        pass
    return None

def match_chinese_to_english(chinese_name, url, english_names_list):
    """匹配中文名称到英文名称"""
    # 方法1: 从URL中提取（如果URL包含英文名称）
    url_name = extract_name_from_url(url)
    if url_name:
        # 检查是否是英文（不包含中文字符）
        if not any('\u4e00' <= c <= '\u9fff' for c in url_name):
            # 将URL格式转换为正常格式（替换-为空格，首字母大写）
            english_name = url_name.replace('-', ' ').replace('_', ' ')
            # 尝试在列表中查找匹配
            for en_name in english_names_list:
                if en_name.replace("'", "").replace(" ", "-").lower() == url_name.lower():
                    return en_name
                # 也尝试直接匹配
                if en_name.lower().replace("'", "").replace(" ", "-") == url_name.lower():
                    return en_name
    
    # 方法2: 通过URL中的ID匹配（如果有其他数据源）
    # 这里我们主要依赖events_only_list.json的顺序和events_from_html.json的顺序
    # 但由于顺序可能不同，我们需要更智能的匹配
    
    return None

def add_english_names_to_events():
    """为events_from_html.json添加英文名称"""
    # 加载英文名称列表
    english_names = load_english_names()
    print(f"加载了 {len(english_names)} 个英文事件名称\n")
    
    # 加载当前的事件数据
    with open('data/Json/events_from_html.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    print(f"需要处理 {len(events)} 个事件\n")
    
    # 创建一个映射：中文名称 -> 英文名称
    # 由于顺序可能不同，我们需要通过URL或其他方式匹配
    
    # 方法：通过URL中的名称部分匹配
    matched_count = 0
    unmatched = []
    
    for i, event in enumerate(events):
        chinese_name = event.get('name', '')
        url = event.get('url', '')
        
        # 从URL中提取可能的英文名称
        url_name = extract_name_from_url(url)
        english_name = None
        
        if url_name:
            # 如果URL中的名称是英文（不包含中文）
            if not any('\u4e00' <= c <= '\u9fff' for c in url_name):
                # 转换为正常格式
                # URL格式通常是: A-Strange-Mushroom 或 A_Strange_Mushroom
                # 需要转换为: "A Strange Mushroom"
                name_parts = re.split(r'[-_]', url_name)
                english_name = ' '.join(word.capitalize() for word in name_parts)
                
                # 处理特殊情况（如 "Jules' Cafe"）
                english_name = english_name.replace("'S", "'s").replace("'S ", "'s ")
                
                # 验证是否在英文名称列表中
                found = False
                for en_name in english_names:
                    # 比较时忽略大小写和空格/连字符
                    en_normalized = en_name.lower().replace("'", "").replace(" ", "").replace("-", "")
                    url_normalized = english_name.lower().replace("'", "").replace(" ", "").replace("-", "")
                    if en_normalized == url_normalized:
                        english_name = en_name  # 使用列表中的准确格式
                        found = True
                        break
                
                if not found:
                    # 如果没找到精确匹配，尝试模糊匹配
                    for en_name in english_names:
                        if en_name.lower().replace("'", "").replace(" ", "-") == url_name.lower():
                            english_name = en_name
                            found = True
                            break
        
        # 如果还没找到，尝试通过中文名称的拼音或其他方式匹配
        # 这里我们可以使用一个简单的映射表
        if not english_name:
            # 创建一个中文到英文的映射（基于已知数据）
            name_mapping = {
                "奇异蘑菇": "A Strange Mushroom",
                "进阶特训": "Advanced Training",
                "航空站": "Aerodrome",
                "阿尔德里科": "Aldric",
                "工匠沙丘": "Artisan Dunes",
                "大巴扎嘉年华": "BazaarCON",
                "贝克斯": "Bex",
                "波图": "Botul",
                "赏金猎人": "Bounty Hunters",
                "布罗林大厨": "Chef Brolin",
                "德弗莱克": "D'flek",
                "杜利的小屋": "Dooley's Crib",
                "大胃王竞赛": "Eating Contest",
                "经济研讨会": "Economic Seminar",
                "家庭团聚": "Family Reunion",
                "芬恩饱餐餐厅": "Finn's Big Bite",
                "烈焰料理": "Flambe",
                "弗尔姆": "Form",
                "宗师": "Grandmaster",
                "口香糖球贩售机": "Gumball Machine",
                "哈迪": "Haddy",
                "理财推销": "Investment Pitch",
                "朱尔斯的咖啡店": "Jules' Cafe",
                "丛林遗迹": "Jungle Ruins",
                "劳雷尔的梦魇": "Laurel's Night Terrors",
                "糖果蛇丽基特": "Likit",
                "疯狂麦蒂": "Mad Maddie",
                "曼荼罗": "Mandala",
                "珍珠的考古发掘场": "Pearl's Dig Site",
                "倒影池": "Reflecting Pool",
                "复元酊剂": "Regenerative Tincture",
                "长袍怪商": "Shrouded Figure",
                "街头庆典": "Street Festival",
                "教团": "The Cult",
                "码头": "The Docks",
                "失落宝箱": "The Lost Crate",
                "盗贼行会": "Thieves Guild",
                "茸茸小怪兽": "Tiny Furry Monster",
                "灵光一闪": "Wink"
            }
            
            if chinese_name in name_mapping:
                english_name = name_mapping[chinese_name]
        
        # 添加到事件数据中
        if english_name:
            event['name_en'] = english_name
            matched_count += 1
            print(f"✓ [{i+1}/{len(events)}] {chinese_name} -> {english_name}")
        else:
            unmatched.append(chinese_name)
            print(f"✗ [{i+1}/{len(events)}] {chinese_name} - 未找到英文名称")
    
    print(f"\n匹配结果: {matched_count}/{len(events)} 个事件找到了英文名称")
    if unmatched:
        print(f"未匹配的事件: {len(unmatched)} 个")
        for name in unmatched:
            print(f"  - {name}")
    
    # 保存更新后的文件
    output_file = 'data/Json/events_from_html.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")
    
    return events

if __name__ == '__main__':
    print("为events_from_html.json补充英文名称")
    print("="*70 + "\n")
    add_english_names_to_events()

