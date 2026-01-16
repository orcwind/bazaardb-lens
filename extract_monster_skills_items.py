#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从HTML文件中提取怪物的技能和物品信息
这些信息存放在 /card/随机码/name 路径中
技能会去重，物品保留所有重复项（因为掉落物品可能有多个）
"""
from pathlib import Path
import re
import json
from urllib.parse import unquote
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_detail.json'


def normalize_name(n):
    """标准化名称，将空格、中横线、下划线统一处理，用于比较"""
    if not n:
        return ''
    normalized = n.lower().replace('-', ' ').replace('_', ' ').replace(' ', ' ')
    normalized = ' '.join(normalized.split())
    return normalized


def is_english_only(text):
    """检查是否只包含英文"""
    if not text:
        return False
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return False
    if '\\' in text or text.startswith('page-') or '.js' in text:
        return False
    if len(text) < 2 or len(text) > 100:
        return False
    if text.replace('-', '').replace('_', '').replace(' ', '').isalnum() == False:
        return False
    return True


def clean_name(n):
    """清理名称"""
    n = n.rstrip('\\').strip()
    return n.strip()


def extract_card_names_from_html(html_content):
    """从HTML内容中提取所有 /card/随机码/name 模式"""
    card_names = []
    
    # 方法1: 使用正则表达式提取
    card_pattern = r'/card/[a-zA-Z0-9]+/([^/<>"\'\s?&#]+)'
    matches = re.findall(card_pattern, html_content)
    for match in matches:
        try:
            decoded = unquote(match)
            decoded = decoded.split('?')[0].split('#')[0].split('/')[0]
            if decoded:
                card_names.append(decoded)
        except Exception:
            pass
    
    # 方法2: 从 DOM 的 a[href] 中提取
    soup = BeautifulSoup(html_content, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if '/card/' in href and href.count('/card/') == 1:
            parts = href.split('/card/')
            if len(parts) > 1:
                rest = parts[1]
                path_parts = rest.split('/')
                if len(path_parts) >= 2:
                    name_part = path_parts[1]
                    try:
                        decoded = unquote(name_part.split('?')[0].split('#')[0].split('/')[0])
                        if decoded and decoded not in card_names:
                            card_names.append(decoded)
                    except Exception:
                        pass
    
    # 过滤和清理
    english_names = []
    for n in card_names:
        cleaned = clean_name(n)
        if is_english_only(cleaned):
            english_names.append(cleaned)
    
    return english_names


def extract_skills_and_items(html_path):
    """从单个HTML文件中提取技能和物品"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 获取怪物名称
    h1 = soup.find('h1')
    if h1 and h1.text.strip():
        monster_name = h1.text.strip()
    else:
        monster_name = html_path.stem
        parts = monster_name.split('_', 1)
        if len(parts) == 2:
            monster_name = parts[1]
    
    skills = []
    items = []
    
    # 方法1: 从 meta description 提取 Skills: ... Items: ...
    meta = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html)
    meta_skills = []
    meta_items = []
    if meta:
        desc = meta.group(1)
        skills_match = re.search(r'Skills:\s*([^.]+)\.', desc)
        if skills_match:
            meta_skills = [s.strip() for s in skills_match.group(1).split(',') if s.strip()]
        items_match = re.search(r'Items:\s*([^.]+)\.', desc)
        if items_match:
            meta_items = [s.strip() for s in items_match.group(1).split(',') if s.strip()]
    
    # 方法2: 从 DOM 结构查找 h3 / div 卡片
    # 查找包含技能或物品关键词的 h3（英文或中文）
    for h3 in soup.find_all('h3'):
        text = h3.get_text(strip=True)
        if not text:
            continue
        tl = text.lower()
        
        # 检查是否是技能部分
        if 'skill' in tl or '技能' in text:
            # 下一个兄弟 div 里可能包含多个 card
            div = h3.find_next_sibling('div')
            if div:
                # 提取该div下所有 /card/ 链接
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
                                        skills.append(cleaned)
                                except Exception:
                                    pass
        
        # 检查是否是物品部分
        if 'item' in tl or '物品' in text:
            div = h3.find_next_sibling('div')
            if div:
                # 提取该div下所有 /card/ 链接
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
                                        items.append(cleaned)
                                except Exception:
                                    pass
    
    # 如果从DOM结构中没有找到，使用meta信息
    if not skills and meta_skills:
        skills = meta_skills
    if not items and meta_items:
        items = meta_items
    
    # 如果仍然没有找到，从所有 /card/ 链接中提取（排除怪物名称本身）
    if not skills and not items:
        all_card_names = extract_card_names_from_html(html)
        normalized_monster_name = normalize_name(monster_name)
        other_names = [n for n in all_card_names if normalize_name(n) != normalized_monster_name]
        # 如果无法区分，都作为物品
        items = other_names
    
    # 技能去重（技能通常不会重复）
    def uniq_skills(seq):
        seen = set()
        res = []
        for x in seq:
            normalized = normalize_name(x)
            if x and normalized not in seen:
                seen.add(normalized)
                res.append(x)
        return res
    
    # 物品不去重，保留所有重复项
    def clean_items(seq):
        res = []
        for x in seq:
            if x:
                res.append(x)
        return res
    
    skills = uniq_skills(skills)
    items = clean_items(items)  # 保留所有重复的物品
    
    return {
        'name': monster_name,
        'name_zh': monster_name,  # 如果没有中文名，使用英文名
        'skills': [{'name': s} for s in skills],
        'items': [{'name': i} for i in items]  # 保留重复项
    }


def extract_all_monsters():
    """从所有HTML文件中提取怪物信息"""
    html_files = sorted(HTML_DIR.glob('*.html'))
    
    results = []
    for html_file in html_files:
        try:
            print(f"处理: {html_file.name}")
            monster_data = extract_skills_and_items(html_file)
            results.append(monster_data)
        except Exception as e:
            print(f"处理失败: {html_file.name} -> {e}")
            import traceback
            traceback.print_exc()
    
    # 保存结果
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n提取完成！结果保存到: {OUTPUT_JSON}")
    print(f"总共处理: {len(results)} 个怪物")
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in results)
    total_items = sum(len(m['items']) for m in results)
    print(f"总技能数: {total_skills}")
    print(f"总物品数: {total_items}")
    
    return results


if __name__ == '__main__':
    extract_all_monsters()
