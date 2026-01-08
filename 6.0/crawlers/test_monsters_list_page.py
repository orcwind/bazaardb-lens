"""测试怪物总列表页面是否包含 initialData.pageCards"""
import sys
from pathlib import Path
from selenium import webdriver
import time

sys.path.insert(0, str(Path(__file__).parent))
from selenium_items_skills import setup_driver

def test_monsters_list_page():
    """测试怪物总列表页面"""
    print("测试怪物总列表页面: https://bazaardb.gg/search?c=monsters")
    
    driver = setup_driver()
    try:
        url = "https://bazaardb.gg/search?c=monsters"
        driver.get(url)
        time.sleep(5)
        
        # 滚动加载所有内容
        print("滚动页面加载所有怪物...")
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        html = driver.page_source
        
        # 检查关键字段
        print(f"\n页面检查:")
        print(f"  - HTML长度: {len(html)}")
        print(f"  - 包含 'initialData': {'initialData' in html}")
        print(f"  - 包含 'pageCards': {'pageCards' in html}")
        print(f"  - 包含 'CombatEncounter': {'CombatEncounter' in html}")
        
        # 保存HTML用于调试
        debug_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\nHTML已保存到: {debug_file}")
        
        # 如果找到 initialData，检查 pageCards
        if 'initialData' in html:
            pos = html.find('initialData')
            print(f"\n找到 initialData 在位置: {pos}")
            search_area = html[pos:min(len(html), pos + 100000)]
            if 'pageCards' in search_area:
                print(f"  ✓ 找到 pageCards 在 initialData 区域内")
                # 尝试提取 pageCards 数组
                pagecards_pos = search_area.find('pageCards')
                bracket_start = search_area.find('[', pagecards_pos)
                if bracket_start != -1:
                    print(f"  ✓ 找到数组开始标记 [ 在位置 {bracket_start}")
            else:
                print(f"  ✗ 未找到 pageCards 在 initialData 区域内")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_monsters_list_page()

