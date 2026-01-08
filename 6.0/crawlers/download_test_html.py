"""
测试脚本：下载一个物品的搜索页面HTML
"""
import time
from selenium import webdriver
from pathlib import Path

def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # 暂时不隐藏，方便调试
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)

def download_item_search_html(card_name='Landscraper'):
    """下载物品搜索页面的HTML"""
    driver = setup_driver()
    
    try:
        # 构建搜索URL
        search_url = f"https://bazaardb.gg/search?q={card_name.replace(' ', '+')}&c=items"
        print(f"访问: {search_url}")
        driver.get(search_url)
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(5)
        
        # 获取HTML
        html = driver.page_source
        
        # 保存到文件
        output_file = Path(f'test_{card_name}_search.html')
        output_file.write_text(html, encoding='utf-8')
        
        print(f"✓ HTML已保存到: {output_file}")
        print(f"  文件大小: {len(html)} 字符")
        
        # 检查是否包含 pageCards
        if 'pageCards' in html:
            print("✓ 找到 'pageCards' 关键字")
            # 找到 pageCards 的位置
            pos = html.find('pageCards')
            print(f"  'pageCards' 位置: {pos}")
            # 打印前后各200字符
            start = max(0, pos - 200)
            end = min(len(html), pos + 200)
            print(f"  上下文片段:\n{html[start:end]}")
        else:
            print("✗ 未找到 'pageCards' 关键字")
            # 查找类似的键
            similar_keys = ['pageCards', 'pagecards', 'PageCards', 'initialData', 'InitialData']
            for key in similar_keys:
                if key in html:
                    print(f"  找到类似关键字: {key}")
        
        # 检查是否包含 initialData
        if 'initialData' in html:
            print("✓ 找到 'initialData' 关键字")
            pos = html.find('initialData')
            start = max(0, pos - 200)
            end = min(len(html), pos + 500)
            print(f"  'initialData' 上下文片段:\n{html[start:end]}")
        
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("浏览器已关闭")

if __name__ == "__main__":
    download_item_search_html('Landscraper')


