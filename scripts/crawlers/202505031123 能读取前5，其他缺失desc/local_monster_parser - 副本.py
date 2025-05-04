import os
import json
import logging
from bs4 import BeautifulSoup
import re

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
    """从技能或物品卡片结构中提取功能描述，优先找 class 包含 _by 的 div"""
    if card_tag is None:
        return ""
    # 优先查找 class 包含 _by 的 div
    desc_div = card_tag.find('div', class_=lambda c: c and '_by' in c)
    if desc_div and desc_div.get_text(strip=True):
        return desc_div.get_text(strip=True)
    # 兜底：找下一个兄弟<p>或<span>
    next_tag = card_tag.find_next_sibling()
    while next_tag and next_tag.name not in ['p', 'span', 'div']:
        next_tag = next_tag.find_next_sibling()
    if next_tag and next_tag.get_text(strip=True):
        return next_tag.get_text(strip=True)
    # 如果没有，尝试找父节点下的文本
    parent = card_tag.parent
    if parent:
        texts = [t for t in parent.stripped_strings if t != card_tag.get_text(strip=True)]
        if texts:
            return texts[0]
    return ""

def parse_monster_html(file_path):
    """提取skills和items的名称、图标、描述和宽高比"""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    result = {}
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
                skill['desc'] = desc
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
                item['desc'] = desc
            if item:
                items.append(item)
    result['items'] = items
    return result

def main():
    # 输入目录
    input_dir = os.path.join('data', 'monsters')
    
    # 获取目录下所有HTML文件
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.html')]
    
    if not input_files:
        print(f"在目录 {input_dir} 中没有找到HTML文件")
        return
    
    print(f"找到 {len(input_files)} 个HTML文件")
    
    # 输出目录和文件
    output_dir = 'output'
    output_file = os.path.join(output_dir, 'monsters_detail.json')
    os.makedirs(output_dir, exist_ok=True)

    # 存储所有怪物的数据
    all_monsters_data = {}

    # 处理每个HTML文件
    for file_name in input_files:
        file_path = os.path.join(input_dir, file_name)
        monster_name = file_name.split('_', 3)[-1].replace('.html', '')
        
        try:
            data = parse_monster_html(file_path)
            all_monsters_data[monster_name] = {
                'skills': data['skills'],
                'items': data['items']
            }
            print(f"已处理 {monster_name}")
        except Exception as e:
            print(f"处理 {monster_name} 时出错: {str(e)}")

    # 将结果保存到JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_monsters_data, f, ensure_ascii=False, indent=2)
    print(f"已保存所有怪物数据到 {output_file}")

if __name__ == "__main__":
    main()
