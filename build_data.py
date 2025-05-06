import os
import json
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# 配置
html_dir_monster = 'dev/html/monsters'
html_dir_event = 'dev/html/events'
output_monster_json = 'data/monsters.json'
output_event_json = 'data/events.json'
icon_dir = 'icons'

def download_icon(url):
    if not url or not url.startswith('http'):
        return url
    filename = os.path.basename(urlparse(url).path)
    local_path = os.path.join(icon_dir, filename)
    if not os.path.exists(local_path):
        try:
            os.makedirs(icon_dir, exist_ok=True)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(resp.content)
                print(f'已下载: {filename}')
            else:
                print(f'下载失败: {filename} 状态码: {resp.status_code}')
        except Exception as e:
            print(f'下载异常: {filename} 错误: {e}')
    return os.path.join('icons', filename).replace('\\', '/')

def process_icon_fields(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'icon' and isinstance(v, str) and v.startswith('http'):
                obj[k] = download_icon(v)
            else:
                process_icon_fields(v)
    elif isinstance(obj, list):
        for item in obj:
            process_icon_fields(item)

def parse_monster_htmls():
    monsters = []
    for fname in sorted(os.listdir(html_dir_monster)):
        if fname.endswith('.html'):
            # 这里可调用你原有的html解析逻辑
            # 假设parse_monster_html_local返回dict
            with open(os.path.join(html_dir_monster, fname), 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                # 这里只做简单示例，实际请用你原有的解析函数
                name = soup.find('h1').text if soup.find('h1') else fname
                monsters.append({'name': name, 'icon': '', 'skills': [], 'items': []})
    return monsters

def parse_event_htmls():
    events = []
    for fname in sorted(os.listdir(html_dir_event)):
        if fname.endswith('.html'):
            with open(os.path.join(html_dir_event, fname), 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                name = soup.find('h1').text if soup.find('h1') else fname
                events.append({'name': name, 'icon': '', 'options': []})
    return events

def main():
    # 1. 解析怪物
    monsters = parse_monster_htmls()
    process_icon_fields(monsters)
    os.makedirs('data', exist_ok=True)
    with open(output_monster_json, 'w', encoding='utf-8') as f:
        json.dump({'monsters': monsters}, f, ensure_ascii=False, indent=2)
    print(f'怪物数据已保存到 {output_monster_json}')

    # 2. 解析事件
    events = parse_event_htmls()
    process_icon_fields(events)
    with open(output_event_json, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f'事件数据已保存到 {output_event_json}')

if __name__ == '__main__':
    main()
