#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Selenium（Chrome）渲染搜索页并下载怪物详情页 HTML（渲染后）。

用法：
  python download_monsters_selenium.py --limit 3
  python download_monsters_selenium.py --limit 10 --headless False

输出目录：data/html/monster/
"""
from pathlib import Path
import argparse
import json
import time
import re
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = Path(__file__).resolve().parents[0]
MONSTERS_JSON = BASE_DIR / 'data' / 'Json' / 'monsters.json'
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'

def safe_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    s = re.sub(r'\s+', '_', s).strip('_')
    return s[:150]

def load_monsters():
    with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'monsters' in data:
        arr = data['monsters']
    else:
        arr = data
    monsters = []
    for entry in arr:
        name = entry.get('name') or entry.get('name_en')
        url = entry.get('url') or ''
        if name:
            monsters.append({'name': name, 'url': url})
    return monsters

def setup_driver(headless=True):
    options = Options()
    if headless:
        # new headless mode if supported
        try:
            options.add_argument('--headless=new')
        except Exception:
            options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # 强制使用英文
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    driver = webdriver.Chrome(options=options)
    return driver

def find_card_link_from_search(driver, name, timeout=10):
    """在搜索页中等待并返回第一个 /card/ 链接（绝对 URL）"""
    try:
        # 等待结果区域出现
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/card/'], a[href*='/monster/']"))
        )
        elems = driver.find_elements(By.CSS_SELECTOR, "a[href*='/card/'], a[href*='/monster/']")
        if elems:
            return elems[0].get_attribute('href')
    except Exception:
        # 尝试从页面中查找文本匹配的卡片链接
        try:
            elems = driver.find_elements(By.TAG_NAME, "a")
            for a in elems:
                href = a.get_attribute('href') or ''
                if '/card/' in href or '/monster/' in href:
                    return href
        except Exception:
            return None
    return None

def force_english_url(url):
    """强制 URL 使用英文版本"""
    # 移除语言后缀，如 /zh-CN
    if '/zh-CN' in url:
        url = url.replace('/zh-CN', '')
    # 移除其他语言后缀
    url = re.sub(r'/[a-z]{2}-[A-Z]{2}$', '', url)
    # 确保 URL 以英文版本结尾（如果没有语言参数）
    if '?' in url:
        # 如果有查询参数，检查是否有 lang 参数
        base, query = url.split('?', 1)
        params = query.split('&')
        # 移除 lang 参数，确保使用默认英文
        params = [p for p in params if not p.startswith('lang=')]
        url = base + ('?' + '&'.join(params) if params else '')
    return url

def download_monster_detail(driver, monster, idx, delay=1.0, force_english=True):
    name = monster['name']
    search_url = f"https://bazaardb.gg/search?q={quote_plus(name)}&c=monsters"
    print(f"[{idx}] 搜索: {name}")
    driver.get(search_url)
    # give some time for dynamic load
    time.sleep(1.0)
    link = find_card_link_from_search(driver, name, timeout=8)
    if not link:
        print(f"  ✗ 未在搜索页找到详情链接: {name}")
        return False
    
    # 强制使用英文 URL
    if force_english:
        link = force_english_url(link)
    
    print(f"  ✓ 详情页: {link}")
    try:
        driver.get(link)
        # 等待详情主要内容加载（h1 或 .card-title）
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        # 额外等待一下，确保页面完全渲染
        time.sleep(0.5)
    except Exception:
        # 仍然保存当前 page_source
        pass
    html = driver.page_source
    safe_name = safe_filename(f"{idx:04d}_{name}")
    out = HTML_DIR / f"{safe_name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✓ 已保存: {out}")
    time.sleep(delay)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 个怪物（0=全部）')
    ap.add_argument('--headless', type=str, default='true', help='是否无头模式: true/false')
    ap.add_argument('--delay', type=float, default=1.0, help='每个请求间隔秒数')
    ap.add_argument('--force', action='store_true', help='强制重新下载，删除已存在的 HTML 文件')
    args = ap.parse_args()

    headless = args.headless.lower() != 'false'
    limit = args.limit
    delay = args.delay
    force = args.force

    monsters = load_monsters()
    if limit > 0:
        monsters = monsters[:limit]

    # 如果需要强制重新下载，删除已存在的文件
    if force:
        print("清理已存在的 HTML 文件...")
        for html_file in HTML_DIR.glob('*.html'):
            html_file.unlink()
            print(f"  已删除: {html_file.name}")
        print(f"清理完成，共删除 {len(list(HTML_DIR.glob('*.html')))} 个文件\n")

    driver = setup_driver(headless=headless)
    success = 0
    try:
        for i, m in enumerate(monsters, 1):
            ok = download_monster_detail(driver, m, i, delay=delay, force_english=True)
            if ok:
                success += 1
    finally:
        driver.quit()

    print(f"\n完成：共处理 {len(monsters)}，成功保存 {success}")

if __name__ == '__main__':
    main()

