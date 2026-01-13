"""调试选择卡片页面，查看实际的HTML结构"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import re

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {'intl.accept_languages': 'en-US,en'})
    return webdriver.Chrome(options=options)

def debug_choice_page(choice_url, choice_name):
    """调试选择卡片页面"""
    driver = setup_driver()
    try:
        print(f"访问: {choice_name}")
        print(f"URL: {choice_url}")
        print("=" * 80)
        
        driver.get(choice_url)
        time.sleep(5)
        
        html = driver.page_source
        
        # 保存HTML到文件
        with open(f'debug_choice_{choice_name.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML已保存到: debug_choice_{choice_name.replace(' ', '_')}.html")
        
        # 查找所有可能的描述容器
        print("\n尝试查找描述...")
        
        # 方法1: _bM 类
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        print(f"\n1. div._bM 找到 {len(desc_matches)} 个匹配:")
        for i, match in enumerate(desc_matches[:5], 1):
            text = re.sub(r'<[^>]+>', '', match)
            text = text.strip()[:200]
            print(f"   {i}. {text}")
        
        # 方法2: 查找所有包含描述的div
        all_divs = re.findall(r'<div[^>]*>(.*?)</div>', html, re.DOTALL)
        print(f"\n2. 所有div（前10个）:")
        for i, div in enumerate(all_divs[:10], 1):
            text = re.sub(r'<[^>]+>', '', div)
            text = text.strip()
            if text and len(text) > 10:
                print(f"   {i}. {text[:100]}")
        
        # 方法3: 获取页面文本
        page_text = driver.execute_script("return document.body.innerText;")
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        print(f"\n3. 页面文本（前20行）:")
        for i, line in enumerate(lines[:20], 1):
            print(f"   {i}. {line}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    # 测试一个选择
    choice_url = "https://bazaardb.gg/card/6zsxdwjvusw7j4vse7486pm6c/Trade-It-for-Something"
    choice_name = "Trade It for Something"
    debug_choice_page(choice_url, choice_name)


