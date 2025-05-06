import os
import json
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

def parse_event_options(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # 获取事件名称 - 使用新的选择器
    title = soup.find('h1')
    if not title:
        print(f"警告: {html_file} 中未找到事件名称")
        return None
    
    event_name = title.text.strip()
    
    # 获取事件描述 - 使用新的选择器
    description = soup.find('div', class_='_bq')
    if not description:
        print(f"警告: {html_file} 中未找到事件描述")
        return None
    
    event_description = description.text.strip()
    
    # 获取所有选项 - 使用新的选择器
    options = []
    option_divs = soup.find_all('div', class_='_w')
    
    for div in option_divs:
        option = {}
        
        # 获取选项名称 - 在 h3 span 中
        name_span = div.find('h3').find('span') if div.find('h3') else None
        if name_span:
            option['name'] = name_span.text.strip()
        
        # 获取选项描述 - 在 _bq class 中
        desc_div = div.find('div', class_='_bq')
        if desc_div:
            option['description'] = desc_div.text.strip()
        
        # 获取选项图片（保留原始URL）
        img = div.find('img')
        if img:
            option['icon'] = img.get('src', '')
        
        if 'name' in option and 'description' in option:
            options.append(option)
        else:
            print(f"警告: {html_file} 中的选项缺少名称或描述")
    
    if not options:
        print(f"警告: {html_file} 中未找到任何选项")
        return None
    
    return {
        'name': event_name,
        'description': event_description,
        'options': options
    }

def download_icon(url, icon_dir='icons'):
    if not url or not url.startswith('http'):
        return
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
    events_dir = 'dev/html/events'
    output_file = os.path.join('data', 'events.json')
    
    events = []
    
    # 遍历所有事件HTML文件
    for filename in os.listdir(events_dir):
        if filename.endswith('.html'):
            html_file = os.path.join(events_dir, filename)
            event_data = parse_event_options(html_file)
            if event_data:
                events.append(event_data)
    
    # 保存到JSON文件
    os.makedirs('data', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    print(f"已完成，共处理{len(events)}个事件，结果已保存到 {output_file}")
    
    # 批量下载所有选项icon
    all_icons = set()
    for event in events:
        for option in event.get('options', []):
            icon_url = option.get('icon', '')
            if icon_url and icon_url.startswith('http'):
                all_icons.add(icon_url)
    for url in all_icons:
        download_icon(url)

if __name__ == '__main__':
    main() 