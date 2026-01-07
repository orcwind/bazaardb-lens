"""
使用Selenium获取技能搜索页面的HTML
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def main():
    """主函数"""
    print("=" * 80)
    print("获取技能搜索页面HTML")
    print("=" * 80)
    
    driver = setup_driver()
    
    try:
        url = "https://bazaardb.gg/search?c=skills"
        print(f"\n访问: {url}")
        driver.get(url)
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(5)
        
        # 滚动页面加载所有内容
        print("滚动页面加载内容...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 10:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
        
        # 再次等待内容加载
        time.sleep(3)
        
        # 保存HTML
        html_content = driver.page_source
        output_file = "debug_skills.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✓ HTML已保存到: {output_file}")
        print(f"  文件大小: {len(html_content)} 字符")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")

if __name__ == "__main__":
    main()

