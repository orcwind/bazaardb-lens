"""
简单爬虫 - 抓取物品和技能的HTML文件（使用Selenium，因为页面是动态加载的）
"""

import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """设置Chrome驱动，强制使用英文语言"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # 强制设置语言为英文
    options.add_argument('--lang=en-US')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    
    # 设置Accept-Language header
    options.add_argument('--accept-lang=en-US,en')
    
    return webdriver.Chrome(options=options)

def fetch_html_with_scroll(driver, url, output_file, category_name):
    """使用Selenium访问页面，滚动加载所有内容，然后保存HTML"""
    print(f"\n[{category_name}] 抓取 {category_name} 数据")
    print(f"  访问: {url}")
    
    try:
        # 设置Accept-Language header强制使用英文
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": driver.execute_script("return navigator.userAgent;"),
            "acceptLanguage": "en-US,en;q=0.9"
        })
        
        driver.get(url)
        time.sleep(5)  # 等待页面加载
        
        # 尝试通过JavaScript设置语言偏好
        driver.execute_script("""
            if (window.localStorage) {
                localStorage.setItem('language', 'en');
                localStorage.setItem('locale', 'en-US');
            }
        """)
        
        # 重新加载页面以应用语言设置
        driver.refresh()
        time.sleep(3)
        
        # 滚动加载所有内容
        print("  滚动页面加载所有内容...")
        no_change_count = 0
        max_no_change = 3
        scroll_count = 0
        max_scrolls = 100
        
        while scroll_count < max_scrolls:
            # 先尝试点击"Load more"按钮（如果有）
            try:
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load more') or contains(text(), '加载更多')]")
                for btn in load_more_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        break
            except:
                pass
            
            # 滚动到底部
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 检查是否有新内容加载
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    print(f"  连续 {max_no_change} 次无新内容，停止滚动")
                    break
            else:
                no_change_count = 0
            
            scroll_count += 1
            if scroll_count % 10 == 0:
                print(f"  已滚动 {scroll_count} 次...")
        
        # 等待最后的内容加载
        print("  等待内容加载完成...")
        time.sleep(5)
        
        # 保存HTML到data/html目录
        html_content = driver.page_source
        
        # 确保目录存在
        html_dir = Path(__file__).parent.parent.parent / "data" / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = html_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_size = len(html_content)
        print(f"  ✓ 文件大小: {file_size:,} 字符")
        print(f"  ✓ 已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ 抓取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """抓取物品、技能、怪物和事件的HTML文件"""
    print("=" * 80)
    print("开始抓取物品、技能、怪物和事件HTML文件...")
    print("=" * 80)
    
    driver = setup_driver()
    
    try:
        # 抓取物品HTML
        items_url = "https://bazaardb.gg/search?c=items"
        fetch_html_with_scroll(driver, items_url, 'items.html', '物品')
        
        # 抓取技能HTML
        skills_url = "https://bazaardb.gg/search?c=skills"
        fetch_html_with_scroll(driver, skills_url, 'skills.html', '技能')
        
        # 抓取怪物HTML
        monsters_url = "https://bazaardb.gg/search?c=monsters"
        fetch_html_with_scroll(driver, monsters_url, 'monsters.html', '怪物')
        
        # 抓取事件HTML
        events_url = "https://bazaardb.gg/search?c=events"
        fetch_html_with_scroll(driver, events_url, 'events.html', '事件')
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")
    
    print("\n" + "=" * 80)
    print("抓取完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

