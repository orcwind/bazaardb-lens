"""抓取英文版本的monsters HTML页面"""
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def setup_driver():
    """设置Chrome驱动，强制英文语言"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--lang=en-US')
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # 通过CDP设置Accept-Language头
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": driver.execute_script("return navigator.userAgent;"),
        "acceptLanguage": "en-US,en;q=0.9"
    })
    
    # 设置localStorage强制英文
    driver.get("https://bazaardb.gg")
    driver.execute_script("""
        localStorage.setItem('locale', 'en-US');
        localStorage.setItem('language', 'en');
    """)
    
    return driver

def fetch_monsters_html():
    """抓取monsters总列表页面的HTML（英文版）"""
    output_dir = Path(__file__).parent.parent.parent / "data" / "html"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "monsters_list_page_en.html"
    
    print("=" * 80)
    print("抓取英文版Monsters HTML页面")
    print("=" * 80)
    
    driver = setup_driver()
    
    try:
        url = "https://bazaardb.gg/search?c=monsters"
        print(f"\n访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 再次确保语言设置
        driver.execute_script("""
            localStorage.setItem('locale', 'en-US');
            localStorage.setItem('language', 'en');
        """)
        driver.refresh()
        time.sleep(5)
        
        # 滚动加载所有内容
        print("滚动页面加载所有怪物...")
        no_change_count = 0
        max_no_change = 3
        scroll_count = 0
        max_scrolls = 100
        
        while scroll_count < max_scrolls:
            # 尝试点击"Load more"按钮
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
        
        print("  等待内容加载完成...")
        time.sleep(5)
        
        # 保存HTML
        html = driver.page_source
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✓ HTML已保存到: {output_file}")
        print(f"  HTML长度: {len(html)} 字符")
        
        # 检查是否包含英文内容
        if 'Monsters in The Bazaar' in html or 'CombatEncounter' in html:
            print("  ✓ 确认包含英文内容")
        else:
            print("  ⚠ 警告: 可能不是英文版本")
        
        return output_file
        
    except Exception as e:
        print(f"\n✗ 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_monsters_html()

