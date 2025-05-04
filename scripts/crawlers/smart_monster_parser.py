import os
import json
import logging
from bs4 import BeautifulSoup
import re
from pathlib import Path

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
    
    # 在卡片结构中查找描述文本
    desc_div = card_tag.find('div', class_='_bq')
    if desc_div:
        desc_text = desc_div.get_text(strip=True)
        if desc_text and desc_text != "Avail.":
            return desc_text
    
    # 如果没有找到，尝试在父节点中查找
    parent_div = card_tag.find_parent('div', class_='_aD')
    if parent_div:
        desc_div = parent_div.find('div', class_='_bq')
        if desc_div:
            desc_text = desc_div.get_text(strip=True)
            if desc_text and desc_text != "Avail.":
                return desc_text
    
    return ""

def parse_monster_html_local(file_path):
    """提取skills和items的名称、图标、描述和宽高比"""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    result = {}
    # 获取怪物名称
    monster_name = soup.find('h1').text if soup.find('h1') else Path(file_path).stem
    if monster_name.startswith('monster_detail_'):
        monster_name = monster_name.split('_', 3)[-1]
    result['name'] = monster_name
    
    # 解析技能
    skills = []
    skill_section = soup.find('h3', string=lambda text: text and 'skill' in text.lower())
    if skill_section:
        skill_divs = skill_section.find_next_sibling('div').find_all('div', style=lambda s: s and 'aspect-ratio' in s)
        for skill_div in skill_divs:
            skill = {}
            # 图标
            img_tag = skill_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                skill['icon'] = img_tag['src']
            # 名称和描述递归查找
            name = None
            desc = None
            for parent in skill_div.parents:
                if not parent or not hasattr(parent, 'find_all'):
                    break
                if not name:
                    h3s = parent.find_all('h3')
                    for h in h3s:
                        t = h.text.strip()
                        if t:
                            name = t
                            break
                if not desc:
                    bys = parent.find_all('div', class_=lambda c: c and '_by' in c)
                    for d in bys:
                        t = d.text.strip()
                        if t:
                            desc = t
                            break
                if name and desc:
                    break
            if not name or not desc:
                siblings = list(skill_div.parent.children) if skill_div.parent else []
                for sib in siblings:
                    if sib == skill_div:
                        continue
                    if not name and hasattr(sib, 'find_all'):
                        h3s = sib.find_all('h3')
                        for h in h3s:
                            t = h.text.strip()
                            if t:
                                name = t
                                break
                    if not desc and hasattr(sib, 'find_all'):
                        bys = sib.find_all('div', class_=lambda c: c and '_by' in c)
                        for d in bys:
                            t = d.text.strip()
                            if t:
                                desc = t
                                break
                    if name and desc:
                        break
            if name:
                skill['name'] = name
            if desc:
                skill['description'] = desc
            if skill:
                skills.append(skill)
    result['skills'] = skills

    # 解析物品
    items = []
    item_section = soup.find('h3', string=lambda text: text and 'item' in text.lower())
    if item_section:
        item_divs = item_section.find_next_sibling('div').find_all('div', style=lambda s: s and 'aspect-ratio' in s)
        for item_div in item_divs:
            item = {}
            # 图标
            img_tag = item_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                item['icon'] = img_tag['src']
            # aspect-ratio
            style = item_div.get('style', '')
            aspect_ratio = None
            match = re.search(r'aspect-ratio\s*:\s*([\d\.]+)', style)
            if match:
                aspect_ratio = float(match.group(1))
            if aspect_ratio:
                item['aspect_ratio'] = aspect_ratio
            # 名称和描述递归查找
            name = None
            desc = None
            for parent in item_div.parents:
                if not parent or not hasattr(parent, 'find_all'):
                    break
                if not name:
                    h3s = parent.find_all('h3')
                    for h in h3s:
                        t = h.text.strip()
                        if t:
                            name = t
                            break
                if not desc:
                    bys = parent.find_all('div', class_=lambda c: c and '_by' in c)
                    for d in bys:
                        t = d.text.strip()
                        if t:
                            desc = t
                            break
                if name and desc:
                    break
            if not name or not desc:
                siblings = list(item_div.parent.children) if item_div.parent else []
                for sib in siblings:
                    if sib == item_div:
                        continue
                    if not name and hasattr(sib, 'find_all'):
                        h3s = sib.find_all('h3')
                        for h in h3s:
                            t = h.text.strip()
                            if t:
                                name = t
                                break
                    if not desc and hasattr(sib, 'find_all'):
                        bys = sib.find_all('div', class_=lambda c: c and '_by' in c)
                        for d in bys:
                            t = d.text.strip()
                            if t:
                                desc = t
                                break
                    if name and desc:
                        break
            if name:
                item['name'] = name
            if desc:
                item['description'] = desc
            if item:
                items.append(item)
    result['items'] = items
    return result

# html_parser.py 方式
def extract_item_info(item_div):
    name_element = item_div.find('h3', class_='_aF')
    name = name_element.find('span').text if name_element else ""
    img_element = item_div.find('img')
    icon = img_element.get('src') if img_element else ""
    desc_div = item_div.find('div', class_='_bq')
    description = desc_div.get_text() if desc_div else ""
    aspect_ratio = None
    img_container = item_div.find('div', class_='_as')
    if img_container:
        style = img_container.get('style', '')
        match = re.search(r'aspect-ratio\s*:\s*([\d\.]+)', style)
        if match:
            aspect_ratio = float(match.group(1))
    return {
        "name": name,
        "icon": icon,
        "description": description,
        "aspect_ratio": aspect_ratio
    }

def parse_monster_html_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
    monster_name = soup.find('h1').text if soup.find('h1') else Path(html_path).stem
    skills = []
    skills_section = soup.find_all('div', class_='█ _az')[:2]
    for skill_div in skills_section:
        skill_info = extract_item_info(skill_div)
        skills.append(skill_info)
    items = []
    items_section = soup.find_all('div', class_='█ _az')[2:]
    for item_div in items_section:
        item_info = extract_item_info(item_div)
        items.append(item_info)
    return {
        "name": monster_name,
        "skills": skills,
        "items": items
    }

def main():
    html_dir = 'data/monsters'
    all_htmls = sorted([f for f in os.listdir(html_dir) if f.endswith('.html')], key=natural_key)
    first5_htmls = all_htmls[:5]
    rest_htmls = all_htmls[5:]
    monsters = []
    for f in first5_htmls:
        html_path = os.path.join(html_dir, f)
        monsters.append(parse_monster_html_local(html_path))
    for f in rest_htmls:
        html_path = os.path.join(html_dir, f)
        monsters.append(parse_monster_html_html(html_path))
    # 统一name字段去前缀
    for idx, m in enumerate(monsters):
        if m['name'].startswith('monster_detail_'):
            m['name'] = m['name'].split('_', 3)[-1]
        # 统一所有技能和物品的描述字段为 description
        for skill in m['skills']:
            if 'desc' in skill:
                skill['description'] = skill.pop('desc')
            # 前5个怪物补充 aspect_ratio 字段，优先用已有值，没有时补 1.0
            if idx < 5 and 'aspect_ratio' not in skill:
                skill['aspect_ratio'] = 1.0
        for i, item in enumerate(m['items']):
            if 'desc' in item:
                item['description'] = item.pop('desc')
            # 前5个怪物补充 aspect_ratio 字段，优先用已有值，没有时补 1.0
            if idx < 5 and 'aspect_ratio' not in item:
                item['aspect_ratio'] = 1.0
            # 前5个怪物调整字段顺序为 name, icon, description, aspect_ratio
            if idx < 5:
                new_item = {}
                new_item['name'] = item.get('name', '')
                new_item['icon'] = item.get('icon', '')
                new_item['description'] = item.get('description', '')
                new_item['aspect_ratio'] = item.get('aspect_ratio', 1.0)
                m['items'][i] = new_item
    with open('output/smart_all_monsters.json', 'w', encoding='utf-8') as f:
        json.dump({'monsters': monsters}, f, ensure_ascii=False, indent=2)
    print(f"已完成，合并共{len(monsters)}个怪物，结果已保存到 output/smart_all_monsters.json")

if __name__ == '__main__':
    main()
