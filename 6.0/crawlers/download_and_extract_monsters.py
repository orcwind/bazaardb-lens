#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载所有怪物的 HTML 页面并从 HTML 中提取技能与物品信息。

用法:
  python download_and_extract_monsters.py --download   # 只下载 HTML
  python download_and_extract_monsters.py --extract    # 只从已有 HTML 提取
  python download_and_extract_monsters.py --all        # 下载并提取（默认间隔与重试）

输出：
  - HTML 文件保存在: data/html/monster/
  - 提取结果保存为: data/Json/monsters_detail.json
"""
import argparse
import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
MONSTERS_JSON = BASE_DIR / 'data' / 'Json' / 'monsters.json'
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN = 1.0
RETRIES = 2


def safe_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    s = re.sub(r'\s+', '_', s).strip('_')
    return s[:150]


def load_monster_list():
    if not MONSTERS_JSON.exists():
        raise FileNotFoundError(f"找不到怪物列表: {MONSTERS_JSON}")
    with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 支持两种结构：list 或 dict
    if isinstance(data, dict) and 'monsters' in data:
        arr = data['monsters']
    else:
        arr = data
    monsters = []
    for entry in arr:
        name = entry.get('name') or entry.get('name_en') or entry.get('name_en')
        url = entry.get('url') or entry.get('link') or ''
        if name:
            monsters.append({'name': name, 'url': url})
    return monsters


def ensure_dirs():
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'data' / 'Json').mkdir(parents=True, exist_ok=True)


def fetch_url(url: str) -> str:
    for attempt in range(1, RETRIES + 2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt <= RETRIES:
                time.sleep(1.0 + attempt)
                continue
            raise


def find_detail_url_from_search(html: str) -> str:
    """从搜索页面尝试定位怪物详情页 URL（优先 card/monster 路径）"""
    # 先尝试 canonical / og:url
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    m2 = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]*content=["\']([^"\']+)["\']', html)
    if m2:
        return m2.group(1)

    # 寻找第一个 a[href*="/card/"] 或 href 包含 "/monster/" 的链接
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/card/' in href or '/monster/' in href or '/card/' in href:
            if href.startswith('http'):
                return href
            else:
                # 绝对化常见站点
                return requests.compat.urljoin('https://bazaardb.gg', href)

    # 备用：从 JS 内提取 /card/xx
    m3 = re.search(r'href=["\'](/card/[^"\']+)["\']', html)
    if m3:
        return 'https://bazaardb.gg' + m3.group(1)

    return ''


def download_all_html(monsters):
    ensure_dirs()
    summary = {'downloaded': 0, 'skipped': 0, 'failed': 0}
    for idx, m in enumerate(monsters, 1):
        name = m['name']
        url = m.get('url') or ''
        safe_name = safe_filename(f"{idx:04d}_{name}")
        out_file = HTML_DIR / f"{safe_name}.html"
        if out_file.exists():
            summary['skipped'] += 1
            continue

        try:
            if url:
                # 先请求列表/搜索页
                html = fetch_url(url)
                detail = find_detail_url_from_search(html)
                if detail:
                    # 若能定位详情页则下载详情页
                    html = fetch_url(detail)
                # 保存最终 HTML（详情页优先，若未找到则保存搜索页）
            else:
                # 没有 URL，跳过
                raise ValueError("缺少 url")

            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(html)
            summary['downloaded'] += 1
            time.sleep(SLEEP_BETWEEN)
        except Exception as e:
            summary['failed'] += 1
            # 保存错误页面为空白以便后续排查
            try:
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- FAILED: {e} -->")
            except Exception:
                pass
            time.sleep(0.5)
    return summary


def extract_from_single_html(path: Path):
    """从单个 HTML 提取 name, skills 和 items（尽量保守）"""
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')

    # 名称：优先 h1，再用文件名后缀回退
    h1 = soup.find('h1')
    if h1 and h1.text.strip():
        name = h1.text.strip()
    else:
        name = path.stem
        # 若文件名包含下划线编号，尝试恢复原名
        parts = name.split('_', 1)
        if len(parts) == 2:
            name = parts[1]

    skills = []
    items = []

    # 方法1: 从 meta description 提取 Skills: ... Items: ...
    meta = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html)
    if meta:
        desc = meta.group(1)
        skills_match = re.search(r'Skills:\s*([^.]+)\.', desc)
        if skills_match:
            skills = [s.strip() for s in skills_match.group(1).split(',') if s.strip()]
        items_match = re.search(r'Items:\s*([^.]+)\.', desc)
        if items_match:
            items = [s.strip() for s in items_match.group(1).split(',') if s.strip()]

    # 方法2: 从 DOM 结构查找 h3 / div 卡片（补充名称或描述）
    # 查找包含技能或物品关键词的 h3（英文或中文）
    for h3 in soup.find_all('h3'):
        text = h3.get_text(strip=True)
        if not text:
            continue
        tl = text.lower()
        if 'skill' in tl or '技能' in text:
            # 下一个兄弟 div 里可能包含多个 card
            div = h3.find_next_sibling('div')
            if div:
                for card in div.find_all('div', recursive=False):
                    nm = card.find('h3')
                    if nm:
                        span = nm.find('span')
                        nm_text = (span.text if span else nm.text).strip()
                        if nm_text:
                            skills.append(nm_text)
        if 'item' in tl or '物品' in text:
            div = h3.find_next_sibling('div')
            if div:
                for card in div.find_all('div', recursive=False):
                    nm = card.find('h3')
                    if nm:
                        span = nm.find('span')
                        nm_text = (span.text if span else nm.text).strip()
                        if nm_text:
                            items.append(nm_text)

    # 去重并保持顺序
    def uniq(seq):
        seen = set()
        res = []
        for x in seq:
            if x and x not in seen:
                seen.add(x)
                res.append(x)
        return res

    skills = uniq(skills)
    items = uniq(items)

    # 返回结构化数据（只包含 name 与条目名称）
    return {
        'name': name,
        'skills': [{'name': s} for s in skills],
        'items': [{'name': i} for i in items]
    }


def extract_all_from_html():
    ensure_dirs()
    files = sorted([p for p in HTML_DIR.glob('*.html')])
    results = []
    for p in files:
        try:
            rec = extract_from_single_html(p)
            results.append(rec)
        except Exception as e:
            print(f"提取失败: {p.name} -> {e}")
    # 保存为 monsters_detail.json（覆盖）
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return {'parsed': len(results)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--download', action='store_true', help='只下载 HTML')
    ap.add_argument('--extract', action='store_true', help='只从 HTML 提取')
    ap.add_argument('--all', action='store_true', help='下载并提取（默认）')
    args = ap.parse_args()

    monsters = load_monster_list()
    if not (args.download or args.extract or args.all):
        args.all = True

    if args.download or args.all:
        print(f"开始下载 {len(monsters)} 个怪物的 HTML 到: {HTML_DIR}")
        dsum = download_all_html(monsters)
        print(f"下载完成: {dsum}")

    if args.extract or args.all:
        print("开始从 HTML 提取怪物信息...")
        r = extract_all_from_html()
        print(f"提取完成: {r}")


if __name__ == '__main__':
    main()

