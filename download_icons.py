import json
import os
import requests
from urllib.parse import urlparse
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_dir(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_icon(url, save_path):
    """下载单个图标"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            logging.error(f"下载失败 {url}: HTTP {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"下载出错 {url}: {e}")
        return False

def main():
    # 创建图标目录
    icons_dir = "icons"
    ensure_dir(icons_dir)
    
    # 读取怪物数据
    with open('monsters_detailed.json', 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    # 收集所有图标URL
    icons_to_download = set()
    for monster in monsters:
        # 怪物图标
        if 'icon' in monster:
            icons_to_download.add(monster['icon'])
        
        # 技能图标
        for skill in monster.get('skills', []):
            if 'icon' in skill:
                icons_to_download.add(skill['icon'])
        
        # 物品图标
        for item in monster.get('items', []):
            if 'icon' in item:
                icons_to_download.add(item['icon'])
    
    logging.info(f"找到 {len(icons_to_download)} 个唯一图标")
    
    # 下载图标
    success_count = 0
    for url in icons_to_download:
        # 从URL中提取文件名
        filename = os.path.basename(urlparse(url).path)
        save_path = os.path.join(icons_dir, filename)
        
        if os.path.exists(save_path):
            logging.info(f"跳过已存在的图标: {filename}")
            success_count += 1
            continue
            
        logging.info(f"下载图标: {filename}")
        if download_icon(url, save_path):
            success_count += 1
    
    logging.info(f"下载完成: {success_count}/{len(icons_to_download)} 个图标成功")

if __name__ == "__main__":
    main() 