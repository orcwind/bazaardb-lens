#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 bazaardb.gg 抓取所有怪物的 HTML 页面
- 直接从网页获取怪物列表（支持无限滚动/分页）
- 支持重试机制
- 保存到 data/html/monster 目录

用法:
    python fetch_html.py
"""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / 'data' / 'html' / 'monster'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'monsters_list_from_web.json'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN = 1.0
RETRIES = 3
SCROLL_PAUSE_TIME = 2.0
MAX_SCROLL_ATTEMPTS = 20


def safe_filename(name: str) -> str:
    """将名称转换为安全的文件名"""
    s = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    s = re.sub(r'\s+', '_', s).strip('_')
    return s[:150]


def ensure_dirs():
    """确保输出目录存在"""
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'data' / 'Json').mkdir(parents=True, exist_ok=True)


def setup_driver(headless=True):
    """设置 Chrome 驱动"""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


def scroll_to_load_all(driver, max_attempts=MAX_SCROLL_ATTEMPTS):
    """滚动页面直到加载所有内容"""
    print("📜 开始滚动页面加载所有怪物...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    
    while scroll_attempts < max_attempts:
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # 检查是否有新内容加载
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # 尝试再等待一下，可能还在加载
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print(f"✓ 已加载所有内容（滚动 {scroll_attempts + 1} 次）")
                break
        
        last_height = new_height
        scroll_attempts += 1
        print(f"  滚动中... ({scroll_attempts}/{max_attempts})")
    
    if scroll_attempts >= max_attempts:
        print(f"⚠ 达到最大滚动次数 ({max_attempts})，可能还有内容未加载")


def extract_monster_links(driver):
    """从页面提取所有怪物链接"""
    print("🔍 正在提取怪物链接...")
    monsters = []
    
    try:
        # 等待页面加载完成
        time.sleep(2)
        
        # 方法1: 使用 JavaScript 直接提取链接（避免 DOM 元素失效问题）
        try:
            print("  📋 使用方法1: JavaScript 提取...")
            js_code = """
            var links = [];
            var elements = document.querySelectorAll('a[href*="/card/"]');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var href = el.getAttribute('href');
                if (!href) continue;
                
                // 确保 URL 完整
                if (!href.startsWith('http')) {
                    href = 'https://bazaardb.gg' + (href.startsWith('/') ? href : '/' + href);
                }
                
                // 检查是否是怪物卡片
                // 方法1: 检查父元素或卡片容器是否有怪物标识
                var isMonster = false;
                var parent = el;
                for (var j = 0; j < 5; j++) {  // 向上查找5层
                    if (!parent) break;
                    var classList = parent.className || '';
                    var dataset = parent.dataset || {};
                    var text = parent.textContent || '';
                    
                    // 检查是否有怪物相关标识
                    if (classList.toLowerCase().includes('monster') || 
                        (dataset.type && dataset.type.toLowerCase() === 'monster') ||
                        text.toLowerCase().includes('monster')) {
                        isMonster = true;
                        break;
                    }
                    parent = parent.parentElement;
                }
                
                // 方法2: 检查页面URL是否包含怪物筛选
                if (!isMonster) {
                    var currentUrl = window.location.href;
                    if (currentUrl.includes('c=monsters') || currentUrl.includes('?c=monsters')) {
                        // 如果页面是怪物筛选页面，假设所有卡片都是怪物
                        // 但我们需要进一步验证
                        isMonster = true;
                    }
                }
                
                // 方法3: 检查卡片的meta信息（如果可用）
                // 由于我们在列表页，可能无法直接判断，先通过URL和上下文判断
                
                // 提取名称
                var name = '';
                var h3 = el.querySelector('h3');
                if (h3) {
                    name = h3.textContent.trim();
                } else {
                    name = el.textContent.trim();
                }
                
                // 从 URL 提取名称作为备用
                if (!name) {
                    var parts = href.split('/');
                    if (parts.length >= 2) {
                        name = parts[parts.length - 1];
                    }
                }
                
                // 只有确定为怪物时才添加
                // 由于在 ?c=monsters 页面，暂时认为都是怪物，后续可以通过访问详情页验证
                if (name && href && (isMonster || window.location.href.includes('c=monsters'))) {
                    links.push({name: name, url: href, isMonster: isMonster});
                }
            }
            return links;
            """
            js_results = driver.execute_script(js_code)
            
            if js_results:
                seen_urls = set()
                monster_count = 0
                for item in js_results:
                    url = item.get('url')
                    if not url or url in seen_urls:
                        continue
                    
                    # 由于在 ?c=monsters 页面，我们假设所有卡片都是怪物
                    # 但为了确保，我们可以通过访问详情页验证
                    # 这里先收集所有链接，后续在下载时验证
                    monsters.append({
                        'name': item.get('name', ''),
                        'url': url
                    })
                    seen_urls.add(url)
                    monster_count += 1
                
                print(f"  ✓ JavaScript 方法提取到 {monster_count} 个链接")
                
                # 如果数量明显过多（超过150个），可能需要进一步过滤
                if monster_count > 150:
                    print(f"  ⚠ 警告: 提取到的链接数量 ({monster_count}) 可能包含非怪物卡片")
                    print(f"  💡 将在下载时通过页面内容验证是否为怪物")
        
        except Exception as e:
            print(f"  ⚠ JavaScript 方法失败: {e}")
        
        # 如果 JavaScript 方法提取的数量不足，尝试 DOM 方法
        if len(monsters) < 50:
            try:
                print("  📋 使用方法2: DOM 提取...")
                card_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
                seen_urls = {m['url'] for m in monsters}
                
                for link in card_links:
                    try:
                        # 检查元素是否仍然有效
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            time.sleep(0.1)
                        except Exception:
                            continue
                        
                        href = link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # 确保 URL 完整
                        if not href.startswith('http'):
                            href = urljoin('https://bazaardb.gg', href)
                        
                        # 提取怪物名称（从链接文本或 h3 标签）
                        name = None
                        try:
                            h3 = link.find_element(By.TAG_NAME, 'h3')
                            name = h3.text.strip()
                        except (NoSuchElementException, Exception):
                            try:
                                name = link.text.strip()
                            except Exception:
                                pass
                        
                        # 如果还是找不到名称，从 URL 中提取
                        if not name:
                            url_parts = href.split('/')
                            if len(url_parts) >= 2:
                                name = url_parts[-1]
                        
                        if name and href:
                            monsters.append({
                                'name': name,
                                'url': href
                            })
                            seen_urls.add(href)
                    
                    except Exception as e:
                        # 忽略单个元素的错误，继续处理下一个
                        continue
            
            except Exception as e:
                print(f"  ⚠ DOM 方法失败: {e}")
        
        # 方法3: 如果前两种方法提取的数量不足，尝试从页面源码中提取
        if len(monsters) < 50:
            try:
                print("  📋 使用方法3: 页面源码提取...")
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                seen_urls = {m['url'] for m in monsters}
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/card/' in href and href not in seen_urls:
                        if not href.startswith('http'):
                            href = urljoin('https://bazaardb.gg', href)
                        
                        name = None
                        h3 = a.find('h3')
                        if h3:
                            name = h3.get_text(strip=True)
                        else:
                            name = a.get_text(strip=True)
                        
                        # 从 URL 提取名称
                        if not name:
                            url_parts = href.split('/')
                            if len(url_parts) >= 2:
                                name = url_parts[-1]
                        
                        if name:
                            monsters.append({
                                'name': name,
                                'url': href
                            })
                            seen_urls.add(href)
                
                print(f"  ✓ 页面源码方法补充了 {len([m for m in monsters if m['url'] in seen_urls])} 个链接")
            
            except Exception as e:
                print(f"  ⚠ 页面源码方法失败: {e}")
    
    except Exception as e:
        print(f"  ❌ 提取怪物链接失败: {e}")
    
    # 去重（按 URL）
    unique_monsters = []
    seen = set()
    for m in monsters:
        if m['url'] not in seen:
            unique_monsters.append(m)
            seen.add(m['url'])
    
    print(f"✓ 提取到 {len(unique_monsters)} 个唯一怪物")
    return unique_monsters


def fetch_url(url: str, retries=RETRIES) -> str:
    """获取 URL 内容，支持重试"""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt < retries:
                wait_time = 1.0 + attempt
                print(f"  ⚠ 请求失败，{wait_time:.1f}秒后重试 ({attempt}/{retries})...")
                time.sleep(wait_time)
            else:
                raise


def get_monster_list_from_web(driver=None, use_selenium=True):
    """从网页获取所有怪物列表"""
    if use_selenium:
        if driver is None:
            driver = setup_driver(headless=True)
        
        try:
            print("🌐 正在访问怪物列表页面...")
            driver.get('https://bazaardb.gg/search?c=monsters')
            time.sleep(3)  # 等待页面初始加载
            
            # 滚动加载所有内容
            scroll_to_load_all(driver)
            
            # 提取所有怪物链接
            monsters = extract_monster_links(driver)
            
            return monsters, driver
        
        except Exception as e:
            print(f"❌ 获取怪物列表失败: {e}")
            if driver:
                driver.quit()
            raise
    else:
        # 使用 requests（可能无法获取动态加载的内容）
        print("⚠ 使用 requests 可能无法获取所有动态加载的内容，建议使用 Selenium")
        html = fetch_url('https://bazaardb.gg/search?c=monsters')
        soup = BeautifulSoup(html, 'html.parser')
        
        monsters = []
        seen = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/card/' in href and href not in seen:
                if not href.startswith('http'):
                    href = urljoin('https://bazaardb.gg', href)
                
                name = None
                h3 = a.find('h3')
                if h3:
                    name = h3.get_text(strip=True)
                else:
                    name = a.get_text(strip=True)
                
                if not name:
                    url_parts = href.split('/')
                    if len(url_parts) >= 2:
                        name = url_parts[-1]
                
                if name:
                    monsters.append({
                        'name': name,
                        'url': href
                    })
                    seen.add(href)
        
        return monsters, None


def is_monster_page(html_content):
    """检查 HTML 内容是否为怪物页面"""
    html_lower = html_content.lower()
    
    # 首先检查是否明确是技能或物品类型（优先检查）
    # 检查 JSON 中的 type 字段，而不是简单的字符串匹配
    if re.search(r'["\']type["\']\s*:\s*["\']skill["\']', html_lower):
        return False
    if re.search(r'["\']type["\']\s*:\s*["\']item["\']', html_lower):
        return False
    
    # 检查标题中是否明确是技能或物品（不包含 Monster）
    title_match = re.search(r'<title>([^<]+)</title>', html_content, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).lower()
        # 如果标题包含 "Skill" 或 "Item"，但不包含 "Monster"，则是技能/物品
        if ('skill' in title or 'item' in title) and 'monster' not in title:
            return False
        # 如果标题包含 "Monster"，则是怪物
        if 'monster' in title:
            return True
    
    # 检查 meta description（最可靠的判断方法）
    meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
    if meta_match:
        desc = meta_match.group(1)
        desc_lower = desc.lower()
        
        # 最可靠：检查是否包含 "Day X Monster" 模式
        # 格式通常是: "Name. Day X Monster. Skills: ... Items: ..."
        if re.search(r'day\s+\d+\s+monster', desc_lower):
            return True
        
        # 检查描述中是否明确标识为技能或物品（但没有 Monster 标识）
        # 如果包含 "Skill" 或 "Item" 但格式不是怪物页面的格式，可能是技能/物品
        # 怪物页面通常格式是: "...Monster. Skills: ... Items: ..."
        # 技能/物品页面格式可能是: "...Skill." 或 "...Item."
        if re.search(r'\b(skill|item)\b', desc_lower):
            # 如果包含 "Day X Monster"，肯定是怪物
            if 'monster' in desc_lower:
                return True
            # 如果只是简单的 "Skill" 或 "Item"，且没有 Monster，则不是怪物
            if 'monster' not in desc_lower:
                return False
    
    # 检查 JSON-LD 结构化数据中的类型
    if re.search(r'["\']type["\']\s*:\s*["\']monster["\']', html_lower):
        return True
    
    # 检查面包屑导航（JSON-LD）
    if re.search(r'["\']name["\']\s*:\s*["\']monsters["\']', html_lower):
        return True
    
    # 如果从 ?c=monsters 页面提取的，且没有明确的反向标识，默认为可能是怪物
    # 但如果完全没有任何怪物标识，返回 None（不确定）
    if 'monster' not in html_lower and 'encounter' not in html_lower:
        return None
    
    # 如果包含 monster 相关的关键词，但没有明确的类型标识，可能是怪物
    return True


def download_monster_html(monster, idx, total, retries=RETRIES, verify_type=True):
    """下载单个怪物的 HTML 页面"""
    name = monster['name']
    url = monster.get('url', '')
    safe_name = safe_filename(f"{idx:04d}_{name}")
    out_file = HTML_DIR / f"{safe_name}.html"
    
    # 如果文件已存在且不是失败标记，跳过
    if out_file.exists():
        try:
            content = out_file.read_text(encoding='utf-8')
            if not content.startswith('<!-- FAILED'):
                return True, 'skipped'
        except Exception:
            pass
    
    if not url:
        error_msg = f"缺少 URL: {name}"
        print(f"  ❌ [{idx}/{total}] {name}: {error_msg}")
        try:
            out_file.write_text(f"<!-- FAILED: {error_msg} -->", encoding='utf-8')
        except Exception:
            pass
        return False, 'failed'
    
    try:
        html = fetch_url(url, retries=retries)
        
        # 验证是否为怪物页面
        if verify_type:
            is_monster = is_monster_page(html)
            if is_monster is False:
                # 不是怪物，跳过
                print(f"  ⏭ [{idx}/{total}] {name}: 不是怪物（技能/物品），跳过")
                return False, 'skipped_not_monster'
            elif is_monster is None:
                # 不确定，但仍然保存（可能是新格式或特殊情况）
                # 但给出警告
                pass
        
        out_file.write_text(html, encoding='utf-8')
        print(f"  ✓ [{idx}/{total}] {name}")
        time.sleep(SLEEP_BETWEEN)
        return True, 'downloaded'
    
    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ [{idx}/{total}] {name}: {error_msg}")
        try:
            out_file.write_text(f"<!-- FAILED: {error_msg} -->", encoding='utf-8')
        except Exception:
            pass
        time.sleep(0.5)
        return False, 'failed'


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从网页抓取所有怪物的 HTML')
    parser.add_argument('--no-selenium', action='store_true', 
                       help='不使用 Selenium（使用 requests，可能遗漏动态内容）')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='使用无头模式（默认开启）')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='不使用无头模式（显示浏览器）')
    parser.add_argument('--download', action='store_true',
                       help='下载 HTML（默认只提取列表）')
    args = parser.parse_args()
    
    ensure_dirs()
    
    print("=" * 80)
    if args.download:
        print("开始从网页获取怪物列表并下载 HTML")
    else:
        print("开始从网页获取怪物列表")
    print("=" * 80)
    
    driver = None
    try:
        # 从网页获取怪物列表
        if args.no_selenium:
            monsters, driver = get_monster_list_from_web(use_selenium=False)
        else:
            driver = setup_driver(headless=args.headless)
            monsters, driver = get_monster_list_from_web(driver, use_selenium=True)
        
        if not monsters:
            print("❌ 未找到任何怪物，退出")
            return
        
        # 保存怪物列表到 JSON
        print(f"\n💾 保存怪物列表到 {OUTPUT_JSON}")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 成功提取 {len(monsters)} 个怪物链接")
        print(f"✓ 列表已保存到: {OUTPUT_JSON}")
        
        # 如果只提取列表，不下载
        if not args.download:
            print("\n" + "=" * 80)
            print("怪物列表提取完成")
            print("=" * 80)
            print(f"总计: {len(monsters)} 个怪物链接")
            print(f"\n要下载 HTML，请运行: python fetch_html.py --download")
            return
        
        print(f"\n📥 开始下载 {len(monsters)} 个卡片的 HTML...")
        print("  💡 将在下载时验证是否为怪物页面，非怪物将被跳过")
        summary = {'downloaded': 0, 'skipped': 0, 'skipped_not_monster': 0, 'failed': 0}
        
        for idx, monster in enumerate(monsters, 1):
            success, status = download_monster_html(monster, idx, len(monsters), verify_type=True)
            if status == 'downloaded':
                summary['downloaded'] += 1
            elif status == 'skipped':
                summary['skipped'] += 1
            elif status == 'skipped_not_monster':
                summary['skipped_not_monster'] += 1
            else:
                summary['failed'] += 1
        
        print("\n" + "=" * 80)
        print("下载完成")
        print("=" * 80)
        print(f"总计卡片: {len(monsters)}")
        print(f"怪物页面（新下载）: {summary['downloaded']}")
        print(f"已存在（跳过）: {summary['skipped']}")
        print(f"非怪物（跳过）: {summary['skipped_not_monster']}")
        print(f"失败: {summary['failed']}")
        print(f"实际怪物数量: {summary['downloaded'] + summary['skipped']}")
        print(f"保存目录: {HTML_DIR}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()
