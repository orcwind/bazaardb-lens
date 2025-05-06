import os
import json
import logging
from bs4 import BeautifulSoup
import re
from pathlib import Path
import requests

def natural_key(s):
    """用于文件名自然排序"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

# 物品尺寸与宽高比映射
SIZE_RATIO = {
    "small": "0.5:1",
    "medium": "1:1",
    "large": "1.5:1"
}

def parse_item_size(item_text):
    """根据物品描述判断尺寸，返回尺寸和宽高比"""
    for size in SIZE_RATIO:
        if size in item_text.lower():
            return size, SIZE_RATIO[size]
    # 默认medium
    return "medium", SIZE_RATIO["medium"]

def extract_desc_from_card(card_tag):
    """从技能或物品卡片结构中提取功能描述"""
    if card_tag is None:
        return ""
    desc_div = card_tag.find('div', class_='_bq')
    if desc_div:
        desc_text = desc_div.get_text(strip=True)
        if desc_text and desc_text != "Avail.":
            return desc_text
    parent_div = card_tag.find_parent('div', class_='_aD')
    if parent_div:
        desc_div = parent_div.find('div', class_='_bq')
        if desc_div:
            desc_text = desc_div.get_text(strip=True)
            if desc_text and desc_text != "Avail.":
                return desc_text
    return ""

def parse_monster_html(file_path):
    """新版HTML结构统一提取技能和物品信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    result = {}
    # 怪物名称
    monster_name = soup.find('h1').text.strip() if soup.find('h1') else Path(file_path).stem
    if monster_name.startswith('monster_detail_'):
        monster_name = monster_name.split('_', 3)[-1]
    result['name'] = monster_name
    # 技能
    skills = []
    skill_section = soup.find('h3', string=lambda t: t and 'skill' in t.lower())
    if skill_section:
        skill_list_div = skill_section.find_next_sibling('div')
        if skill_list_div:
            for skill_div in skill_list_div.find_all('div', class_='_w', recursive=False):
                skill = {}
                # 图标
                img = skill_div.find('img')
                if img:
                    skill['icon'] = img['src']
                # 名称
                h3 = skill_div.find('h3', class_='_ac')
                if h3:
                    span = h3.find('span')
                    if span:
                        skill['name'] = span.text.strip()
                # 描述
                desc_div = skill_div.find('div', class_='_bi')
                if desc_div:
                    skill['description'] = desc_div.get_text(strip=True)
                # aspect-ratio
                ap_div = skill_div.find('div', class_='_ap')
                if ap_div and 'aspect-ratio' in ap_div.get('style', ''):
                    m = re.search(r'aspect-ratio\s*:\s*([\d\.]+)', ap_div['style'])
                    if m:
                        skill['aspect_ratio'] = float(m.group(1))
                skills.append(skill)
    result['skills'] = skills
    # 物品
    items = []
    item_section = soup.find('h3', string=lambda t: t and 'item' in t.lower())
    if item_section:
        item_list_div = item_section.find_next_sibling('div')
        if item_list_div:
            for item_div in item_list_div.find_all('div', class_='_w', recursive=False):
                item = {}
                # 图标
                img = item_div.find('img')
                if img:
                    item['icon'] = img['src']
                # 名称
                h3 = item_div.find('h3', class_='_ac')
                if h3:
                    span = h3.find('span')
                    if span:
                        item['name'] = span.text.strip()
                # 描述
                desc_div = item_div.find('div', class_='_bi')
                if desc_div:
                    item['description'] = desc_div.get_text(strip=True)
                # aspect-ratio
                ap_div = item_div.find('div', class_='_ap')
                if ap_div and 'aspect-ratio' in ap_div.get('style', ''):
                    m = re.search(r'aspect-ratio\s*:\s*([\d\.]+)', ap_div['style'])
                    if m:
                        item['aspect_ratio'] = float(m.group(1))
                items.append(item)
    result['items'] = items
    return result

def download_icon(url, icon_dir='icons'):
    if not url:
        return
    from urllib.parse import urlparse
    filename = os.path.basename(urlparse(url).path)
    icon_path = os.path.join(icon_dir, filename)
    if not os.path.exists(icon_path):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                os.makedirs(icon_dir, exist_ok=True)
                with open(icon_path, "wb") as f:
                    f.write(resp.content)
                print(f"已下载图标: {filename}")
        except Exception as e:
            print(f"下载图标失败: {filename}，错误: {e}")

def main():
    html_dir = 'dev/html/monsters'
    all_htmls = sorted(
        [f for f in os.listdir(html_dir) if f.endswith('.html') and f != 'debug.html'],
        key=natural_key
    )
    monsters = []
    for f in all_htmls:
        html_path = os.path.join(html_dir, f)
        monsters.append(parse_monster_html(html_path))
    # 统一name字段去前缀
    for m in monsters:
        if m['name'].startswith('monster_detail_'):
            m['name'] = m['name'].split('_', 3)[-1]
        # 统一所有技能和物品的描述字段为 description
        for skill in m['skills']:
            if 'desc' in skill:
                skill['description'] = skill.pop('desc')
            if 'aspect_ratio' not in skill:
                skill['aspect_ratio'] = 1.0
        for i, item in enumerate(m['items']):
            if 'desc' in item:
                item['description'] = item.pop('desc')
            if 'aspect_ratio' not in item:
                item['aspect_ratio'] = 1.0
            new_item = {}
            new_item['name'] = item.get('name', '')
            new_item['icon'] = item.get('icon', '')
            new_item['description'] = item.get('description', '')
            new_item['aspect_ratio'] = item.get('aspect_ratio', 1.0)
            m['items'][i] = new_item
    # 保存到 data/monsters.json
    os.makedirs('data', exist_ok=True)
    with open('data/monsters.json', 'w', encoding='utf-8') as f:
        json.dump({'monsters': monsters}, f, ensure_ascii=False, indent=2)
    print(f"已完成，合并共{len(monsters)}个怪物，结果已保存到 data/monsters.json")
    # 批量下载所有图标
    all_icons = set()
    for m in monsters:
        for entry in m.get('skills', []) + m.get('items', []):
            icon_url = entry.get('icon', '')
            if icon_url:
                all_icons.add(icon_url)
    for url in all_icons:
        download_icon(url)

if __name__ == '__main__':
    main()
