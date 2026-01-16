#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根目录版：下载并从 HTML 提取怪物信息，支持 --limit 控制只处理前 N 个怪物（便于测试）。
"""
from pathlib import Path
import argparse
import json
import re
import time
from urllib.parse import unquote
import requests
from bs4 import BeautifulSoup

# 复用 6.0 脚本的主要逻辑（简化版）
BASE_DIR = Path(__file__).resolve().parents[0]
MONSTERS_JSON = BASE_DIR / 'data' / 'Json' / 'monsters.json'
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'

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
    with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'monsters' in data:
        arr = data['monsters']
    else:
        arr = data
    monsters = []
    for entry in arr:
        name = entry.get('name') or entry.get('name_en')
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
        except Exception:
            if attempt <= RETRIES:
                time.sleep(1.0 + attempt)
                continue
            raise

def find_detail_url_from_search(html: str) -> str:
    # 优先 canonical / og:url
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    m2 = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]*content=["\']([^"\']+)["\']', html)
    if m2:
        return m2.group(1)

    # 尝试从 href 属性中找到第一个 /card/ 链接（更宽松的正则，兼容转义与无引号情形）
    card_matches = re.findall(r'(/card/[^"\'\\s<>\\)\\(]+)', html)
    if card_matches:
        # 去重并返回第一个绝对 URL
        for cm in card_matches:
            cm_clean = cm.replace('\\u002F', '/')
            if cm_clean.startswith('/'):
                return requests.compat.urljoin('https://bazaardb.gg', cm_clean)
            if cm_clean.startswith('http'):
                return cm_clean

    # 再用 DOM 查找 a[href]
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/card/' in href or '/monster/' in href:
            if href.startswith('http'):
                return href
            else:
                return requests.compat.urljoin('https://bazaardb.gg', href)

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
                html = fetch_url(url)
                detail = find_detail_url_from_search(html)
                if detail:
                    html = fetch_url(detail)
            else:
                raise ValueError("缺少 url")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(html)
            summary['downloaded'] += 1
            time.sleep(SLEEP_BETWEEN)
        except Exception as e:
            summary['failed'] += 1
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(f"<!-- FAILED: {e} -->")
            time.sleep(0.5)
    return summary

def extract_from_single_html(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    h1 = soup.find('h1')
    if h1 and h1.text.strip():
        name = h1.text.strip()
    else:
        name = path.stem
        parts = name.split('_', 1)
        if len(parts) == 2:
            name = parts[1]
    
    # 方法：从 HTML 中提取所有 /card/随机码/name 路径中的 name
    card_names = []
    # 匹配 /card/随机码/name 格式（name 可能是 URL 编码的）
    # 更精确的模式：匹配 /card/ 后跟随机字符（字母数字），然后是 /，最后是 name
    card_pattern = r'/card/[a-zA-Z0-9]+/([^/<>"\'\s?&#]+)'
    matches = re.findall(card_pattern, html)
    for match in matches:
        try:
            # URL 解码
            decoded = unquote(match)
            # 清理可能的查询参数或片段
            decoded = decoded.split('?')[0].split('#')[0].split('/')[0]
            if decoded:  # 移除去重检查，保留重复项
                card_names.append(decoded)
        except Exception:
            pass
    
    # 也从 DOM 的 a[href] 中提取
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if '/card/' in href and href.count('/card/') == 1:
            # 提取 /card/xxx/name 中的 name
            parts = href.split('/card/')
            if len(parts) > 1:
                rest = parts[1]
                # 分割随机码和 name
                path_parts = rest.split('/')
                if len(path_parts) >= 2:
                    name_part = path_parts[1]
                    try:
                        decoded = unquote(name_part.split('?')[0].split('#')[0].split('/')[0])
                        if decoded:  # 移除去重检查，保留重复项
                            card_names.append(decoded)
                    except Exception:
                        pass
    
    # 注意：不过滤重复项，保留所有重复的物品以统计数量
    
    # 过滤：只保留英文名称（排除中文、转义字符、无效名称）
    def is_english_only(text):
        if not text:
            return False
        # 排除包含中文字符的
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return False
        # 排除包含转义字符的（如 \、\\、page-xxx.js 等）
        if '\\' in text or text.startswith('page-') or '.js' in text:
            return False
        # 排除太短或太长的
        if len(text) < 2 or len(text) > 100:
            return False
        # 排除纯数字或特殊符号
        if text.replace('-', '').replace('_', '').replace(' ', '').isalnum() == False:
            return False
        return True
    
    # 清理名称：移除末尾转义字符
    def clean_name(n):
        # 移除末尾的转义字符
        n = n.rstrip('\\').strip()
        return n.strip()
    
    # 标准化名称：统一处理空格、中横线、下划线，用于比较
    def normalize_name(n):
        """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
        if not n:
            return ''
        # 统一转换为小写，并将空格、中横线、下划线都替换为单个空格
        normalized = n.lower().replace('-', ' ').replace('_', ' ').replace(' ', ' ')
        # 合并多个空格为单个空格
        normalized = ' '.join(normalized.split())
        return normalized
    
    english_names = [clean_name(n) for n in card_names if is_english_only(n)]
    # 注意：不过滤重复项，保留所有重复的物品以统计数量
    
    # 从 meta description 中获取技能和物品信息（用于区分）
    meta_skills = []
    meta_items = []
    meta = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html)
    if meta:
        desc = meta.group(1)
        skills_match = re.search(r'Skills:\s*([^.]+)\.', desc)
        if skills_match:
            meta_skills = [s.strip() for s in skills_match.group(1).split(',') if s.strip()]
        items_match = re.search(r'Items:\s*([^.]+)\.', desc)
        if items_match:
            meta_items = [s.strip() for s in items_match.group(1).split(',') if s.strip()]
    
    # 排除怪物名称本身（如果存在）
    # 注意：name 可能是中文，需要从 monsters.json 中获取英文名
    # 使用标准化名称进行比较
    normalized_monster_name = normalize_name(name)
    other_names = [n for n in english_names if normalize_name(n) != normalized_monster_name]
    
    # 不再区分技能和物品，两个怪物名称中间的所有名称都当做掉落物
    items = []
    
    # 从 HTML 结构中查找所有掉落物
    # 方法：以怪物名字作为开始标记，往后查找，再次遇到怪物名字时结束
    # 找到所有包含怪物名称的元素（按文档顺序）
    all_elements = soup.find_all(['h1', 'h2', 'h3'])
    monster_name_positions = []
    for i, elem in enumerate(all_elements):
        text = elem.get_text(strip=True)
        if text and name in text:
            monster_name_positions.append(i)
    
    # 确定收集范围：从第一个怪物名称到第二个怪物名称（如果存在）
    start_idx = monster_name_positions[0] if monster_name_positions else 0
    end_idx = monster_name_positions[1] if len(monster_name_positions) > 1 else len(all_elements)
    
    # 只处理在范围内的 h3 元素
    collecting = False
    for i, elem in enumerate(all_elements):
        # 检查是否到达开始标记
        if i == start_idx:
            collecting = True
            continue
        
        # 检查是否到达结束标记
        if i == end_idx:
            collecting = False
            break
        
        # 如果在收集范围内且是 h3，处理该元素
        if collecting and elem.name == 'h3':
            text = elem.get_text(strip=True)
            if not text:
                continue
            div = elem.find_next_sibling('div')
            if div:
                # 查找该区域下的所有 /card/ 链接（不再区分技能和物品）
                for a in div.find_all('a', href=True):
                    href = a.get('href', '')
                    if '/card/' in href:
                        parts = href.split('/card/')
                        if len(parts) > 1:
                            rest = parts[1]
                            path_parts = rest.split('/')
                            if len(path_parts) >= 2:
                                name_part = path_parts[1]
                                try:
                                    decoded = unquote(name_part.split('?')[0].split('#')[0].split('/')[0])
                                    cleaned = clean_name(decoded)
                                    if is_english_only(cleaned):
                                        # 所有名称都作为掉落物
                                        items.append({'name': cleaned})
                                except Exception:
                                    pass
    
    # 处理N倍重复：智能检测并去除各种倍数的重复
    def remove_multiple_duplicates(items_list):
        """智能检测列表是否重复了N次（N可以是2、3、4、5、6等），只保留第一次出现的完整列表（保留套内的重复项）"""
        if not items_list or len(items_list) < 2:
            return items_list
        
        total_len = len(items_list)
        
        # 尝试不同的重复倍数（从2到总长度的一半）
        # 优先尝试常见的倍数：2, 3, 4, 5, 6, 7, 10, 12等
        test_multiples = [2, 3, 4, 5, 6, 7, 10, 12, 13, 18, 20, 34, 36, 40, 50]
        # 也尝试其他可能的倍数
        for n in range(2, min(total_len // 2 + 1, 100)):
            if n not in test_multiples:
                test_multiples.append(n)
        
        for multiplier in test_multiples:
            if total_len % multiplier != 0:
                continue
            
            segment_len = total_len // multiplier
            if segment_len < 1:
                continue
            
            # 获取第一段
            first_segment = items_list[:segment_len]
            
            # 检查是否所有段都相同
            all_segments_same = True
            for i in range(1, multiplier):
                start_idx = i * segment_len
                end_idx = start_idx + segment_len
                current_segment = items_list[start_idx:end_idx]
                
                # 比较两段是否完全相同（使用标准化名称比较）
                if len(first_segment) != len(current_segment):
                    all_segments_same = False
                    break
                
                for j in range(len(first_segment)):
                    name1 = normalize_name(first_segment[j]['name'])
                    name2 = normalize_name(current_segment[j]['name'])
                    if name1 != name2:
                        all_segments_same = False
                        break
                
                if not all_segments_same:
                    break
            
            if all_segments_same:
                # 发现重复N次，只返回第一段
                return first_segment
        
        return items_list
    
    # 去除N倍重复（智能检测）
    items = remove_multiple_duplicates(items)
    
    # 如果从 HTML 结构中没有找到，使用 other_names 作为 items（保留重复项）
    if not items:
        # 将所有 other_names 作为 items（保留重复项，用于统计数量）
        items = [{'name': n} for n in other_names]
        # 对 other_names 也进行去除N倍重复处理
        items = remove_multiple_duplicates(items)
    else:
        # HTML 结构提取成功，已经包含了重复项
        # 如果 other_names 中有不在已提取列表中的项，也添加（但保留 other_names 中的重复）
        # 注意：使用标准化名称进行比较
        existing_item_names_normalized = {normalize_name(i['name']) for i in items}
        for n in other_names:
            # 如果不在已提取的物品中，则添加
            # 注意：使用标准化名称比较，避免空格、中横线、下划线的差异
            n_normalized = normalize_name(n)
            if n_normalized not in existing_item_names_normalized:
                items.append({'name': n})
        # 再次去除N倍重复（因为可能添加了 other_names）
        items = remove_multiple_duplicates(items)
    
    return {
        'name': name,  # 保持原样（可能是中文，但输出时会用英文）
        'skills': [],  # 不再区分技能，保持为空
        'items': items
    }

def extract_all_from_html(allow_prefixes=None):
    ensure_dirs()
    
    # 标准化名称函数（与 extract_from_single_html 中的相同）
    def normalize_name(n):
        """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
        if not n:
            return ''
        normalized = n.lower().replace('-', ' ').replace('_', ' ').replace(' ', ' ')
        normalized = ' '.join(normalized.split())
        return normalized
    
    # 加载怪物列表以匹配英文名称
    monsters_map = {}
    try:
        with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
            monsters_data = json.load(f)
        if isinstance(monsters_data, dict) and 'monsters' in monsters_data:
            monsters_list = monsters_data['monsters']
        else:
            monsters_list = monsters_data
        for m in monsters_list:
            name_en = m.get('name', '')
            name_zh = m.get('name_zh', '')
            if name_zh:
                monsters_map[name_zh] = name_en
    except Exception as e:
        print(f"加载怪物列表失败: {e}")
    
    files = sorted([p for p in HTML_DIR.glob('*.html')])
    results = []
    for p in files:
        if allow_prefixes:
            if not any(p.name.startswith(pref) for pref in allow_prefixes):
                continue
        try:
            rec = extract_from_single_html(p)
            # 匹配英文名称（使用标准化名称进行比较）
            name_zh = rec.get('name', '')
            name_en = monsters_map.get(name_zh, name_zh)  # 如果找不到，使用原名称
            
            # 如果仍然找不到，尝试使用标准化名称匹配
            if name_en == name_zh:
                normalized_zh = normalize_name(name_zh)
                for zh, en in monsters_map.items():
                    if normalize_name(zh) == normalized_zh:
                        name_en = en
                        break
            
            # 构建最终结果（只保留英文的技能和物品）
            final_rec = {
                'name': name_en,  # 英文名称
                'name_zh': name_zh,  # 中文名称
                'skills': rec.get('skills', []),
                'items': rec.get('items', [])
            }
            results.append(final_rec)
        except Exception as e:
            print(f"提取失败: {p.name} -> {e}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return {'parsed': len(results)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--extract', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 个怪物（测试用）')
    args = ap.parse_args()
    monsters = load_monster_list()
    if args.limit and args.limit > 0:
        monsters = monsters[:args.limit]
    if not (args.download or args.extract or args.all):
        args.all = True
    if args.download or args.all:
        print(f"下载 {len(monsters)} 个怪物 HTML 到: {HTML_DIR}")
        dsum = download_all_html(monsters)
        print(f"下载完成: {dsum}")
    if args.extract or args.all:
        allow_prefixes = None
        if args.limit and args.limit > 0:
            allow_prefixes = [f"{i:04d}_" for i in range(1, args.limit+1)]
        print("开始提取 HTML 中的信息...")
        r = extract_all_from_html(allow_prefixes=allow_prefixes)
        print(f"提取完成: {r}")

if __name__ == '__main__':
    main()

