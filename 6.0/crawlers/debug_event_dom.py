"""调试事件详情页的DOM结构"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def debug_event_dom(event_url, event_name):
    """调试事件详情页的DOM结构"""
    driver = setup_driver()
    try:
        print(f"访问: {event_name}")
        print(f"URL: {event_url}")
        print("=" * 80)
        
        driver.get(event_url)
        time.sleep(5)
        
        html = driver.page_source
        
        # 保存HTML
        with open(f'debug_event_{event_name.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML已保存")
        
        # 方法1: 查找 div._ah
        print("\n查找 div._ah 容器...")
        try:
            containers = driver.find_elements(By.CSS_SELECTOR, 'div._ah')
            print(f"找到 {len(containers)} 个 div._ah 容器")
            
            for i, container in enumerate(containers[:3], 1):
                print(f"\n容器 {i}:")
                try:
                    # 查找 h3 span
                    name_elem = container.find_element(By.CSS_SELECTOR, 'h3 span')
                    print(f"  名称: {name_elem.text.strip()}")
                except Exception as e:
                    print(f"  未找到名称: {e}")
                
                # 查找所有可能的描述容器
                for selector in ['div._bk', 'div._bq', 'div._bM', 'div._dM']:
                    try:
                        desc_elem = container.find_element(By.CSS_SELECTOR, selector)
                        text = desc_elem.text.strip()
                        if text:
                            print(f"  {selector}: {text[:100]}")
                    except:
                        pass
        except Exception as e:
            print(f"查找 div._ah 失败: {e}")
        
        # 方法2: 查找所有包含选择名称的div
        print("\n查找包含选择名称的元素...")
        try:
            # 查找所有h3元素
            h3_elements = driver.find_elements(By.TAG_NAME, 'h3')
            print(f"找到 {len(h3_elements)} 个 h3 元素")
            
            for i, h3 in enumerate(h3_elements[:5], 1):
                try:
                    span = h3.find_element(By.TAG_NAME, 'span')
                    name = span.text.strip()
                    if name:
                        print(f"\nh3 {i}: {name}")
                        # 查找父容器
                        parent = h3.find_element(By.XPATH, './ancestor::div[contains(@class, "_")]')
                        print(f"  父容器class: {parent.get_attribute('class')}")
                        
                        # 查找同级的描述元素
                        try:
                            desc = parent.find_element(By.CSS_SELECTOR, 'div._bk, div._bq, div._bM')
                            print(f"  描述: {desc.text.strip()[:100]}")
                        except:
                            print(f"  未找到描述")
                except:
                    pass
        except Exception as e:
            print(f"查找h3失败: {e}")
        
        # 方法3: 查找所有包含描述的div
        print("\n查找所有可能的描述元素...")
        for selector in ['div._bk', 'div._bq', 'div._bM']:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"\n{selector}: 找到 {len(elems)} 个")
                for i, elem in enumerate(elems[:3], 1):
                    text = elem.text.strip()
                    if text and len(text) > 10:
                        print(f"  {i}. {text[:100]}")
            except:
                pass
        
    finally:
        input("按Enter键关闭浏览器...")
        driver.quit()

if __name__ == "__main__":
    event_url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/%E5%A5%87%E5%BC%82%E8%98%91%E8%8F%87"
    event_name = "A Strange Mushroom"
    debug_event_dom(event_url, event_name)


