"""
调试脚本：查看实际的页面HTML结构
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawlers'))

import time
from selenium import webdriver
from selenium.webdriver.common.by import By


def debug_monster_list():
    """调试怪物列表页面结构"""
    print("=" * 60)
    print("调试怪物列表页面")
    print("=" * 60)
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://bazaardb.gg/search?c=monsters"
        print(f"\n访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 滚动一下
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)
        
        # 查找卡片
        cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
        print(f"\n找到 {len(cards)} 个卡片")
        
        if cards:
            print("\n【分析前3个卡片的结构】")
            for i, card in enumerate(cards[:3], 1):
                print(f"\n--- 卡片 {i} ---")
                print(f"标签名: {card.tag_name}")
                print(f"href: {card.get_attribute('href')}")
                
                # 获取卡片的HTML
                html = card.get_attribute('outerHTML')[:500]
                print(f"HTML片段: {html}")
                
                # 尝试多种方式查找名称
                print("\n尝试查找名称:")
                
                # 方法1: h3
                try:
                    h3 = card.find_element(By.TAG_NAME, 'h3')
                    print(f"  ✓ h3.text = '{h3.text}'")
                except:
                    print(f"  ✗ 未找到h3标签")
                
                # 方法2: h2
                try:
                    h2 = card.find_element(By.TAG_NAME, 'h2')
                    print(f"  ✓ h2.text = '{h2.text}'")
                except:
                    print(f"  ✗ 未找到h2标签")
                
                # 方法3: h1
                try:
                    h1 = card.find_element(By.TAG_NAME, 'h1')
                    print(f"  ✓ h1.text = '{h1.text}'")
                except:
                    print(f"  ✗ 未找到h1标签")
                
                # 方法4: span
                try:
                    spans = card.find_elements(By.TAG_NAME, 'span')
                    print(f"  找到 {len(spans)} 个span标签")
                    for j, span in enumerate(spans[:3], 1):
                        text = span.text.strip()
                        if text:
                            print(f"    span{j}: '{text}'")
                except:
                    print(f"  ✗ 未找到span标签")
                
                # 方法5: div
                try:
                    divs = card.find_elements(By.TAG_NAME, 'div')
                    print(f"  找到 {len(divs)} 个div标签")
                    for j, div in enumerate(divs[:3], 1):
                        text = div.text.strip()
                        if text and len(text) < 50:  # 只显示短文本
                            print(f"    div{j}: '{text}'")
                except:
                    print(f"  ✗ 未找到div标签")
                
                # 方法6: 直接获取文本
                print(f"  card.text = '{card.text[:100] if card.text else 'Empty'}'")
                
                # 方法7: 查找图片
                try:
                    imgs = card.find_elements(By.TAG_NAME, 'img')
                    print(f"  找到 {len(imgs)} 个图片")
                    for j, img in enumerate(imgs[:2], 1):
                        alt = img.get_attribute('alt')
                        src = img.get_attribute('src')
                        print(f"    img{j}: alt='{alt}', src='{src[:80]}...'")
                except:
                    print(f"  ✗ 未找到图片")
        
        print("\n\n保存完整页面HTML...")
        with open('6.0/debug_monsters_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("已保存到: 6.0/debug_monsters_page.html")
        
        input("\n按Enter键继续...")
        
    finally:
        driver.quit()


def debug_event_list():
    """调试事件列表页面结构"""
    print("\n" + "=" * 60)
    print("调试事件列表页面")
    print("=" * 60)
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://bazaardb.gg/search?c=events"
        print(f"\n访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 查找卡片
        cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
        print(f"\n找到 {len(cards)} 个卡片")
        
        if cards:
            print("\n【分析前2个卡片的结构】")
            for i, card in enumerate(cards[:2], 1):
                print(f"\n--- 卡片 {i} ---")
                print(f"href: {card.get_attribute('href')}")
                
                # 获取卡片的文本
                print(f"card.text = '{card.text[:100] if card.text else 'Empty'}'")
                
                # 查找所有子元素
                children = card.find_elements(By.XPATH, './*')
                print(f"子元素数量: {len(children)}")
                for j, child in enumerate(children[:5], 1):
                    print(f"  子元素{j}: {child.tag_name}, text='{child.text[:50] if child.text else 'Empty'}'")
        
        print("\n\n保存完整页面HTML...")
        with open('6.0/debug_events_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("已保存到: 6.0/debug_events_page.html")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    print("这个脚本会打开浏览器并分析页面结构")
    print("用于调试为什么爬虫无法提取名称\n")
    input("按Enter键开始...")
    
    try:
        debug_monster_list()
        # debug_event_list()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()





