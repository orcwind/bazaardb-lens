#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一步：从网站下载所有物品的 HTML 页面

从 https://bazaardb.gg/search?c=items 获取物品列表
然后下载每个物品的详情页 HTML

用法:
    python fetch_items_html.py
"""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException


BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / 'data' / 'html' / 'item'
OUTPUT_JSON = BASE_DIR / 'data' / 'Json' / 'items_list_from_web.json'
INDEX_HTML = BASE_DIR / 'data' / 'html' / 'items_list_page.html'

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN = 0.5
RETRIES = 3
SCROLL_PAUSE_TIME = 2.0
MAX_SCROLL_ATTEMPTS = 50


def safe_filename(name):
    """生成安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '_', name)
    name = re.sub(r'\s+', '_', name).strip('_')
    return name[:150]


def ensure_dirs():
    """确保输出目录存在"""
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    INDEX_HTML.parent.mkdir(parents=True, exist_ok=True)


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
    """滚动页面直到加载所有物品"""
    print("📜 开始滚动页面加载所有物品...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    no_change_count = 0
    last_item_count = 0
    
    while scroll_attempts < max_attempts:
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # 检查当前物品数量
        try:
            current_item_count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
            if current_item_count == last_item_count:
                no_change_count += 1
                if no_change_count >= 3:
                    print(f"✓ 已加载所有内容（滚动 {scroll_attempts + 1} 次，共 {current_item_count} 个物品）")
                    break
            else:
                no_change_count = 0
                last_item_count = current_item_count
        except:
            pass
        
        # 检查页面高度变化
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:
                print(f"✓ 已加载所有内容（滚动 {scroll_attempts + 1} 次）")
                break
        else:
            last_height = new_height
        
        scroll_attempts += 1
        if scroll_attempts % 5 == 0:
            try:
                count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
                print(f"  滚动中... ({scroll_attempts}/{max_attempts}) - 已找到 {count} 个物品")
            except:
                print(f"  滚动中... ({scroll_attempts}/{max_attempts})")
    
    if scroll_attempts >= max_attempts:
        print(f"⚠ 达到最大滚动次数 ({max_attempts})")
        try:
            final_count = driver.execute_script("return document.querySelectorAll('a[href*=\"/card/\"]').length;")
            print(f"⚠ 最终找到 {final_count} 个链接")
        except:
            pass


def extract_item_links(driver):
    """从页面提取所有物品链接"""
    print("🔍 正在提取物品链接...")
    items = []
    
    try:
        time.sleep(2)
        
        # 使用 JavaScript 提取所有唯一链接
        js_code = """
        var items = [];
        var seenUrls = new Set();
        var elements = document.querySelectorAll('a[href*="/card/"]');
        
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var href = el.getAttribute('href');
            if (!href) continue;
            
            // 确保 URL 完整
            if (!href.startsWith('http')) {
                href = 'https://bazaardb.gg' + (href.startsWith('/') ? href : '/' + href);
            }
            
            // 规范化 URL
            var urlParts = href.split('?');
            var baseUrl = urlParts[0].split('#')[0].replace(/\\/$/, '');
            
            // 跳过重复
            if (seenUrls.has(baseUrl)) continue;
            
            // 只提取 /card/ 格式的URL（物品详情页）
            if (baseUrl.includes('/card/')) {
                var parts = baseUrl.split('/card/');
                if (parts.length > 1) {
                    var cardPart = parts[1];
                    // 排除技能和怪物路径
                    if (!cardPart.includes('/skill') && !cardPart.includes('/monster')) {
                        // 提取名称
                        var name = '';
                        var h3 = el.querySelector('h3');
                        if (h3) {
                            name = h3.textContent.trim();
                        } else {
                            name = el.textContent.trim().replace(/\\s+/g, ' ');
                        }
                        
                        // 从URL提取名称
                        if (!name || name.length < 2) {
                            var nameParts = cardPart.split('/');
                            if (nameParts.length >= 2) {
                                var lastPart = nameParts[nameParts.length - 1];
                                try {
                                    name = decodeURIComponent(lastPart);
                                } catch(e) {
                                    name = lastPart;
                                }
                                name = name.replace(/-/g, ' ').trim();
                            }
                        }
                        
                        if (name && name.length >= 1) {
                            items.push({
                                name: name,
                                url: baseUrl
                            });
                            seenUrls.add(baseUrl);
                        }
                    }
                }
            }
        }
        return items;
        """
        
        items_list = driver.execute_script(js_code)
        print(f"  ✓ JavaScript 方法提取到 {len(items_list)} 个物品链接")
        
        # 再次去重（按 URL）
        seen_urls = set()
        unique_items = []
        for item in items_list:
            clean_url = item['url'].rstrip('/')
            # 提取唯一标识（ID+名称部分）
            url_key = clean_url
            if '/card/' in clean_url:
                match = re.search(r'/card/([^/]+/[^/]+)', clean_url)
                if match:
                    url_key = match.group(1)
            
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                item['url'] = clean_url
                unique_items.append(item)
        
        items = unique_items
        
    except Exception as e:
        print(f"  ⚠ JavaScript 方法失败: {e}")
    
    print(f"✓ 最终提取到 {len(items)} 个唯一物品链接")
    return items


def fetch_url(url, retries=RETRIES):
    """获取 URL 内容（带重试）"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise


def download_item_html(item_info, idx, total):
    """下载单个物品的 HTML"""
    name = item_info['name']
    url = item_info['url']
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
    
    try:
        html = fetch_url(url, retries=RETRIES)
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


def save_index_html(driver):
    """保存搜索首页的完整 HTML"""
    try:
        html_content = driver.page_source
        INDEX_HTML.write_text(html_content, encoding='utf-8')
        print(f"\n💾 已保存搜索首页 HTML 到: {INDEX_HTML}")
        print(f"  文件大小: {len(html_content) / 1024:.2f} KB")
        return True
    except Exception as e:
        print(f"\n⚠️ 保存首页 HTML 失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='下载物品搜索首页的 HTML 页面')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='使用无头模式（默认开启）')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                        help='不使用无头模式（显示浏览器）')
    args = parser.parse_args()
    
    ensure_dirs()
    
    print("=" * 80)
    print("下载物品搜索首页 HTML")
    print("=" * 80)
    
    driver = None
    try:
        # 从网页获取物品列表
        driver = setup_driver(headless=args.headless)
        search_url = "https://bazaardb.gg/search?c=items"
        print(f"\n🌐 访问: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 滚动加载所有物品
        scroll_to_load_all(driver)
        
        # 保存搜索首页的完整 HTML
        save_index_html(driver)
        
        # 提取物品链接（仅用于统计和验证）
        items_list = extract_item_links(driver)
        
        if items_list:
            # 保存物品列表到 JSON（用于后续处理）
            print(f"\n💾 保存物品列表到 {OUTPUT_JSON}")
            with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                json.dump(items_list, f, ensure_ascii=False, indent=2)
            
            # 统计
            print(f"\n📊 统计信息:")
            print(f"  - 提取的物品数: {len(items_list)}")
            print(f"  - 网站统计应有: 899 个")
            if len(items_list) < 899:
                print(f"  ⚠️  缺少 {899 - len(items_list)} 个物品")
        else:
            print("⚠️ 未找到任何物品链接")
        
        print("\n" + "=" * 80)
        print("完成")
        print("=" * 80)
        print(f"搜索首页 HTML 已保存到: {INDEX_HTML}")
    
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
