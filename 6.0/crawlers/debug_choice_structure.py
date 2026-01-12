"""调试选择卡片和描述的关系"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def debug_choice_structure():
    """调试选择卡片结构"""
    driver = setup_driver()
    try:
        url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/%E5%A5%87%E5%BC%82%E8%98%91%E8%8F%87"
        print(f"访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 查找所有h3元素
        h3_elements = driver.find_elements(By.TAG_NAME, 'h3')
        print(f"\n找到 {len(h3_elements)} 个h3元素\n")
        
        for i, h3 in enumerate(h3_elements[:10], 1):
            try:
                span = h3.find_element(By.TAG_NAME, 'span')
                name = span.text.strip()
                if not name:
                    continue
                    
                print(f"{i}. {name}")
                
                # 尝试查找描述
                # 方法1: 查找父元素中的描述
                try:
                    parent = h3.find_element(By.XPATH, './ancestor::div[contains(@class, "_")][1]')
                    try:
                        desc = parent.find_element(By.CSS_SELECTOR, 'div._bk, div._bq')
                        print(f"   ✓ 描述（父元素）: {desc.text.strip()[:80]}")
                        continue
                    except:
                        pass
                except:
                    pass
                
                # 方法2: 查找下一个兄弟元素
                try:
                    next_div = h3.find_element(By.XPATH, './following-sibling::div[contains(@class, "_bk") or contains(@class, "_bq")][1]')
                    print(f"   ✓ 描述（兄弟元素）: {next_div.text.strip()[:80]}")
                    continue
                except:
                    pass
                
                # 方法3: 查找h3后面的所有div._bk和div._bq
                try:
                    all_descs = driver.find_elements(By.CSS_SELECTOR, 'div._bk, div._bq')
                    # 找到h3在页面中的位置
                    h3_y = h3.location['y']
                    for desc in all_descs:
                        desc_y = desc.location['y']
                        # 如果描述在h3后面，且距离不太远
                        if desc_y > h3_y and desc_y < h3_y + 500:
                            print(f"   ✓ 描述（附近）: {desc.text.strip()[:80]}")
                            break
                except:
                    pass
                
                print(f"   ✗ 未找到描述")
                
            except Exception as e:
                print(f"   ✗ 错误: {e}")
            
            print()
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_choice_structure()

