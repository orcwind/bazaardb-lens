"""调试pool数据结构，查看是否包含description或tooltip字段"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re
import json

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def debug_pool_data(event_url, event_name):
    """调试pool数据结构"""
    driver = setup_driver()
    try:
        print(f"访问: {event_name}")
        print(f"URL: {event_url}")
        print("=" * 80)
        
        driver.get(event_url)
        time.sleep(5)
        
        html = driver.page_source
        
        # 找到 "pool":[ 的位置
        pattern = r'\\"pool\\":\['
        match = re.search(pattern, html)
        
        if not match:
            print("未找到pool数据")
            return
        
        start_pos = match.end()
        bracket_count = 1
        i = start_pos
        
        while i < len(html) and bracket_count > 0:
            if html[i] == '[':
                bracket_count += 1
            elif html[i] == ']':
                bracket_count -= 1
            i += 1
        
        if bracket_count == 0:
            pool_str = html[start_pos:i-1]
            pool_json_str = '[' + pool_str + ']'
            pool_json_str = pool_json_str.replace('\\"', '"')
            
            try:
                pool_data = json.loads(pool_json_str)
                print(f"\n找到 {len(pool_data)} 个选择")
                
                # 打印第一个选择的完整数据结构
                if pool_data:
                    print("\n第一个选择的数据结构:")
                    print(json.dumps(pool_data[0], indent=2, ensure_ascii=False))
                    print("\n所有字段:")
                    for key in pool_data[0].keys():
                        value = pool_data[0][key]
                        value_str = str(value)[:100] if value else "None"
                        print(f"  {key}: {value_str}")
                
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    event_url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/%E5%A5%87%E5%BC%82%E8%98%91%E8%8F%87"
    event_name = "A Strange Mushroom"
    debug_pool_data(event_url, event_name)

