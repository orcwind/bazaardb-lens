"""
下载事件页面的HTML用于分析结构
"""

import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By

def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def load_event_names():
    """加载事件名称"""
    with open('unique_events.json', 'r', encoding='utf-8') as f:
        names = [line.strip().strip('"') for line in f if line.strip()]
    return names

def get_event_url(driver, event_name):
    """搜索并获取事件URL"""
    search_url = f"https://bazaardb.gg/search?q={event_name.replace(' ', '+')}&c=events"
    driver.get(search_url)
    time.sleep(3)
    
    try:
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        return card_link.get_attribute('href')
    except:
        return None

def download_event_html():
    """下载前3个事件的HTML"""
    print("=" * 80)
    print("下载前3个事件的HTML文件")
    print("=" * 80)
    
    event_names = load_event_names()[:3]
    output_dir = Path('event_html_samples')
    output_dir.mkdir(exist_ok=True)
    
    driver = setup_driver()
    
    try:
        for i, event_name in enumerate(event_names, 1):
            print(f"\n[{i}/3] {event_name}")
            
            # 获取URL
            print(f"  搜索事件...")
            event_url = get_event_url(driver, event_name)
            
            if not event_url:
                print(f"  ✗ 未找到")
                continue
            
            print(f"  ✓ 找到: {event_url}")
            
            # 访问页面
            print(f"  访问页面...")
            driver.get(event_url)
            time.sleep(5)
            
            # 保存HTML
            html_content = driver.page_source
            safe_name = event_name.replace(' ', '_').replace("'", '')
            html_file = output_dir / f"{safe_name}.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"  ✓ 已保存到: {html_file}")
            print(f"  文件大小: {len(html_content):,} 字节")
    
    finally:
        driver.quit()
        print("\n关闭浏览器...")

if __name__ == "__main__":
    download_event_html()
