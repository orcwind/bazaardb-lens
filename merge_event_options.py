import os
import json
from bs4 import BeautifulSoup

events_dir = 'data/events'
output_file = os.path.join(events_dir, 'all_events_options.json')

# 读取标准事件名映射
events_json_path = os.path.join(events_dir, 'events.json')
event_name_map = {}
if os.path.exists(events_json_path):
    with open(events_json_path, 'r', encoding='utf-8') as f:
        events_list = json.load(f)
        # key: 去掉空格和标点、全部小写，value: 标准事件名
        for event in events_list:
            key = ''.join(filter(str.isalnum, event['name'].lower()))
            event_name_map[key] = event['name']

all_events = []

def extract_option_info(option_div):
    """从单个选项大块div中提取名称、图标、描述"""
    # 图标
    img_tag = option_div.find('img')
    icon = img_tag['src'] if img_tag and img_tag.has_attr('src') else ''
    # 名称
    h3_tag = option_div.find('h3')
    name = ''
    if h3_tag:
        span = h3_tag.find('span')
        name = span.get_text(strip=True) if span else h3_tag.get_text(strip=True)
    # 描述
    desc = ''
    desc_div = option_div.find('div', class_='_bq')
    if desc_div:
        desc = desc_div.get_text(separator=' ', strip=True)
    return {
        'name': name,
        'icon': icon,
        'description': desc
    }

for filename in os.listdir(events_dir):
    if filename.startswith('event_detail_') and filename.endswith('.html'):
        # 事件名从文件名中提取
        parts = filename.split('_')[2:]
        event_name_raw = '_'.join(parts).replace('.html', '').replace('_', ' ')
        # 去掉前缀数字
        event_name_no_num = ' '.join(event_name_raw.split(' ')[1:]) if event_name_raw.split(' ')[0].isdigit() else event_name_raw
        # 用标准事件名映射还原
        key = ''.join(filter(str.isalnum, event_name_no_num.lower()))
        event_name = event_name_map.get(key, event_name_no_num)
        html_path = os.path.join(events_dir, filename)
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            # 事件图标
            event_icon = None
            h1 = soup.find('h1')
            if h1:
                # 事件主图标通常在h1附近
                img = h1.find_next('img')
                if img and img.has_attr('src'):
                    event_icon = img['src']
            # 选项提取
            options = []
            for option_div in soup.find_all('div', class_='_as'):
                option = extract_option_info(option_div)
                options.append(option)
            # 检查字段完整性
            if not event_icon:
                print(f"警告：事件 {event_name} 缺少图标")
            if not options:
                print(f"警告：事件 {event_name} 没有选项")
            for option in options:
                if not option['name']:
                    print(f"警告：事件 {event_name} 的选项缺少名称")
                if not option['icon']:
                    print(f"警告：事件 {event_name} 的选项 {option['name']} 缺少图标")
                if not option['description']:
                    print(f"警告：事件 {event_name} 的选项 {option['name']} 缺少描述")
            all_events.append({
                'name': event_name,
                'icon': event_icon,
                'options': options
            })

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_events, f, ensure_ascii=False, indent=2)

print(f"已合并所有事件选项到 {output_file}") 