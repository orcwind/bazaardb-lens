"""快速测试 - 只检测前30个URL"""
import sys
sys.path.insert(0, 'crawlers')

from monster_crawler import MonsterCrawler

crawler = MonsterCrawler(headless=False)
try:
    crawler.init_driver()
    
    # 只获取怪物列表
    print("开始获取怪物列表...")
    monsters = crawler.fetch_monster_list()
    
    print(f"\n成功！找到 {len(monsters)} 个怪物")
    print("\n前10个怪物:")
    for i, m in enumerate(monsters[:10], 1):
        print(f"  {i}. {m['name']}")
        
finally:
    crawler.close_driver()





