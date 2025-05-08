import json
import os
import requests
from PIL import Image
from io import BytesIO
import logging
import re
from urllib.parse import urlparse
import concurrent.futures
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

def download_and_check_ratio(url):
    """下载图标并检查其实际宽高比"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            width, height = img.size
            return width / height if height != 0 else 1.0
    except Exception as e:
        logging.error(f"检查图标 {url} 失败: {e}")
    return 1.0

def extract_size_from_url(url):
    """从URL中提取尺寸信息"""
    try:
        # 检查URL中是否包含@数字
        size_match = re.search(r'@(\d+)', url)
        if size_match:
            size = int(size_match.group(1))
            return size, size  # 返回宽度和高度
    except Exception as e:
        logging.error(f"从URL提取尺寸失败: {url}, 错误: {e}")
    return None, None

def check_and_fix_ratios():
    """检查并修复monsters.json中的aspect_ratio"""
    try:
        # 读取monsters.json
        with open('data/monsters.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 用于存储所有需要检查的图标URL
        icons_to_check = []
        
        # 收集所有图标URL
        for monster in data['monsters']:
            for skill in monster['skills']:
                if skill.get('icon'):
                    icons_to_check.append((skill['icon'], skill))
            for item in monster['items']:
                if item.get('icon'):
                    icons_to_check.append((item['icon'], item))
        
        logging.info(f"总共找到 {len(icons_to_check)} 个图标需要检查")
        
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {
                executor.submit(download_and_check_ratio, url): (url, item)
                for url, item in icons_to_check
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url, item = future_to_url[future]
                try:
                    ratio = future.result()
                    if ratio != 1.0:
                        logging.info(f"更新图标比例: {url} -> {ratio:.2f}")
                        item['aspect_ratio'] = ratio
                except Exception as e:
                    logging.error(f"处理图标失败 {url}: {e}")
        
        # 保存修改后的数据
        with open('data/monsters.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logging.info("完成图标比例检查和修复")
        
    except Exception as e:
        logging.error(f"处理过程中出错: {e}")

def get_aspect_ratio_from_html(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
    # 查找包含图标的div元素
    icon_div = soup.find('div', {'class': '_aA'})
    if icon_div and 'style' in icon_div.attrs:
        style = icon_div['style']
        # 检查是否直接设置了aspect-ratio
        aspect_match = re.search(r'aspect-ratio:\s*([\d.]+)', style)
        if aspect_match:
            return float(aspect_match.group(1))
        
        # 如果没有直接设置aspect-ratio，尝试从图片尺寸计算
        img = icon_div.find('img')
        if img and img.get('width') and img.get('height'):
            width = float(img['width'])
            height = float(img['height'])
            return width / height if height != 0 else 1.0
    
    return 1.0  # 默认值

def update_monsters_json():
    # 读取monsters.json
    with open('data/monsters.json', 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    # 遍历html文件目录
    html_dir = 'dev/html/monsters'
    for filename in os.listdir(html_dir):
        if filename.startswith('monster_detail_') and filename.endswith('.html'):
            # 从文件名中提取monster ID
            monster_id = filename.split('_')[2].split('.')[0]
            
            # 获取aspect-ratio
            html_path = os.path.join(html_dir, filename)
            aspect_ratio = get_aspect_ratio_from_html(html_path)
            
            # 更新monsters.json中的aspect-ratio
            if monster_id in monsters:
                monsters[monster_id]['aspect_ratio'] = aspect_ratio

    # 保存更新后的monsters.json
    with open('data/monsters.json', 'w', encoding='utf-8') as f:
        json.dump(monsters, f, indent=2)

if __name__ == "__main__":
    check_and_fix_ratios()
    update_monsters_json()
    print("已完成monsters.json的aspect-ratio更新") 