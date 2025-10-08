"""
使用Selenium从bazaardb.gg获取完整的事件列表
"""

import json
import time
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def extract_event_names_from_page(driver):
    """从当前页面提取事件名称"""
    event_names = []
    
    try:
        # 等待卡片加载
        time.sleep(3)
        
        # 获取页面源码
        html = driver.page_source
        
        # 方法1: 从meta描述中提取
        meta_matches = re.findall(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
        for meta_desc in meta_matches:
            # 事件描述格式: "Event Name. Choices: ..."
            event_match = re.match(r'^([^.]+)\.', meta_desc)
            if event_match and 'Choices:' in meta_desc:
                event_name = event_match.group(1).strip()
                if event_name and event_name not in event_names:
                    event_names.append(event_name)
        
        # 方法2: 从卡片链接中提取（备用）
        card_links = re.findall(r'href="/card/[^/]+/([^"]+)"', html)
        for link in card_links:
            # 将URL slug转换为名称
            name = link.replace('-', ' ')
            # 简单验证：事件名称通常是标题格式
            if name and len(name) > 3:
                if name not in event_names:
                    event_names.append(name)
        
        print(f"  本页找到 {len(event_names)} 个事件")
        
    except Exception as e:
        print(f"  ✗ 提取出错: {e}")
    
    return event_names


def get_all_events():
    """获取所有事件名称"""
    print("=" * 80)
    print("从bazaardb.gg获取完整事件列表")
    print("=" * 80)
    
    driver = setup_driver()
    all_events = []
    
    try:
        # 访问事件搜索页
        url = "https://bazaardb.gg/search?c=events"
        print(f"\n访问: {url}")
        driver.get(url)
        
        # 等待页面完全加载
        print("等待页面加载...")
        time.sleep(5)
        
        # 提取事件名称
        print("\n提取事件名称...")
        events = extract_event_names_from_page(driver)
        all_events.extend(events)
        
        # 检查是否有分页（bazaardb.gg通常会显示所有结果）
        html = driver.page_source
        
        # 尝试从页面中提取所有卡片标题
        print("\n使用备用方法：查找所有事件卡片...")
        
        # 查找所有事件卡片的标题
        # 事件卡片通常有特定的class和结构
        title_matches = re.findall(r'<h3[^>]*class="_au"[^>]*>.*?<span>([^<]+)</span>', html, re.DOTALL)
        
        for title in title_matches:
            title = title.strip()
            if title and title not in all_events:
                all_events.append(title)
        
        print(f"  备用方法找到 {len(title_matches)} 个标题")
        
        # 去重
        unique_events = list(dict.fromkeys(all_events))
        
        print(f"\n总共找到 {len(unique_events)} 个唯一事件")
        
        # 保存结果
        output_file = 'unique_events.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            for event in unique_events:
                f.write(f'"{event}"\n')
        
        print(f"\n✓ 已保存到: {output_file}")
        
        # 显示事件列表
        print("\n事件列表:")
        for i, event in enumerate(unique_events, 1):
            print(f"  {i:2d}. {event}")
        
        return unique_events
        
    finally:
        driver.quit()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    events = get_all_events()
    
    print("\n" + "=" * 80)
    print(f"完成！共提取 {len(events)} 个事件")
    print("=" * 80)
