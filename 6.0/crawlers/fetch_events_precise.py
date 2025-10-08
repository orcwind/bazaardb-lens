"""
精确提取事件名称 - 只提取真正的事件卡片
"""

import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def get_all_events():
    """获取所有事件名称"""
    print("=" * 80)
    print("精确提取事件列表")
    print("=" * 80)
    
    driver = setup_driver()
    
    try:
        # 访问事件搜索页
        url = "https://bazaardb.gg/search?c=events"
        print(f"\n访问: {url}")
        driver.get(url)
        
        # 等待页面完全加载
        print("等待页面加载...")
        time.sleep(5)
        
        # 方法：查找所有指向 /card/ 的链接
        print("\n提取事件卡片链接...")
        card_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
        
        event_names = []
        seen_urls = set()
        
        for link in card_links:
            href = link.get_attribute('href')
            
            # 过滤：只要 /card/ 链接，排除其他链接
            if href and '/card/' in href and href not in seen_urls:
                seen_urls.add(href)
                
                # 尝试获取卡片标题
                try:
                    # 查找链接内的标题元素
                    title_element = link.find_element(By.CSS_SELECTOR, 'h3 span, .card-title, span')
                    title = title_element.text.strip()
                    
                    if title and title not in event_names:
                        event_names.append(title)
                        print(f"  {len(event_names):2d}. {title}")
                except:
                    # 如果找不到标题，从URL中提取
                    url_parts = href.split('/')
                    if len(url_parts) > 0:
                        name_slug = url_parts[-1]
                        name = name_slug.replace('-', ' ')
                        if name and name not in event_names and len(name) > 3:
                            event_names.append(name)
                            print(f"  {len(event_names):2d}. {name} (从URL提取)")
        
        print(f"\n总共找到 {len(event_names)} 个事件")
        
        # 保存结果
        output_file = 'unique_events.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            for event in event_names:
                f.write(f'"{event}"\n')
        
        print(f"\n✓ 已保存到: {output_file}")
        
        return event_names
        
    finally:
        driver.quit()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    events = get_all_events()
    
    print("\n" + "=" * 80)
    print(f"完成！共提取 {len(events)} 个事件")
    print("=" * 80)
