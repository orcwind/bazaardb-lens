"""测试怪物搜索页面的HTML结构"""
import sys
from pathlib import Path
from selenium import webdriver
import time

sys.path.insert(0, str(Path(__file__).parent))
from selenium_items_skills import setup_driver

def test_monster_page(monster_name="Banannibal"):
    """测试怪物搜索页面"""
    print(f"测试怪物: {monster_name}")
    
    driver = setup_driver()
    try:
        search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
        print(f"URL: {search_url}")
        driver.get(search_url)
        time.sleep(5)  # 等待更长时间
        
        html = driver.page_source
        
        # 检查关键字段
        print(f"\n页面检查:")
        print(f"  - HTML长度: {len(html)}")
        print(f"  - 包含 'initialData': {'initialData' in html}")
        print(f"  - 包含 'pageCards': {'pageCards' in html}")
        print(f"  - 包含 'CombatEncounter': {'CombatEncounter' in html}")
        print(f"  - 包含怪物名称: {monster_name in html}")
        
        # 保存HTML用于调试
        debug_file = Path(__file__).parent.parent.parent / "data" / "Json" / f"debug_monster_{monster_name}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\nHTML已保存到: {debug_file}")
        
        # 查找 initialData 的位置
        if 'initialData' in html:
            pos = html.find('initialData')
            print(f"\n找到 initialData 在位置: {pos}")
            print(f"前后500字符:")
            print(html[max(0, pos-200):min(len(html), pos+500)])
        else:
            print(f"\n未找到 initialData，查找其他可能的关键字...")
            # 查找可能的JSON数据位置
            keywords = ['pageCards', 'CombatEncounter', 'Type', 'Title']
            for keyword in keywords:
                if keyword in html:
                    pos = html.find(keyword)
                    print(f"  找到 '{keyword}' 在位置: {pos}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    monster = sys.argv[1] if len(sys.argv) > 1 else "Banannibal"
    test_monster_page(monster)

