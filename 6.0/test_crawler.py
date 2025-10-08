"""
测试爬虫功能
快速测试爬虫是否能正常工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawlers'))

from monster_crawler import MonsterCrawler
from event_crawler import EventCrawler
from utils import Logger, load_json


def test_monster_crawler():
    """测试怪物爬虫"""
    print("\n" + "=" * 60)
    print("测试怪物爬虫")
    print("=" * 60)
    
    try:
        crawler = MonsterCrawler(headless=False)
        crawler.init_driver()
        
        # 只获取列表，不抓取详细信息
        print("\n测试获取怪物列表...")
        monsters = crawler.fetch_monster_list()
        
        if monsters:
            print(f"✓ 成功获取 {len(monsters)} 个怪物")
            print("\n前5个怪物:")
            for i, monster in enumerate(monsters[:5], 1):
                print(f"  {i}. {monster['name']}")
            
            # 测试获取一个怪物的详细信息
            print("\n测试获取详细信息（只测试第一个怪物）...")
            details = crawler.fetch_monster_details(monsters[0])
            
            if details:
                print(f"✓ 成功获取 {details['name']} 的详细信息")
                print(f"  - 技能数量: {len(details['skills'])}")
                print(f"  - 物品数量: {len(details['items'])}")
                
                if details['skills']:
                    print(f"\n  第一个技能:")
                    skill = details['skills'][0]
                    print(f"    名称: {skill['name']}")
                    print(f"    描述: {skill.get('description', 'N/A')[:50]}...")
                
                return True
            else:
                print("✗ 获取详细信息失败")
                return False
        else:
            print("✗ 获取怪物列表失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if crawler.driver:
            crawler.close_driver()


def test_event_crawler():
    """测试事件爬虫"""
    print("\n" + "=" * 60)
    print("测试事件爬虫")
    print("=" * 60)
    
    try:
        crawler = EventCrawler(headless=False)
        crawler.init_driver()
        
        # 只获取列表，不抓取详细信息
        print("\n测试获取事件列表...")
        events = crawler.fetch_event_list()
        
        if events:
            print(f"✓ 成功获取 {len(events)} 个事件")
            print("\n前5个事件:")
            for i, event in enumerate(events[:5], 1):
                print(f"  {i}. {event['name']}")
            
            # 测试获取一个事件的详细信息
            print("\n测试获取详细信息（只测试第一个事件）...")
            details = crawler.fetch_event_details(events[0])
            
            if details:
                print(f"✓ 成功获取 {details['name']} 的详细信息")
                print(f"  - 选项数量: {len(details['options'])}")
                
                if details['options']:
                    print(f"\n  第一个选项:")
                    option = details['options'][0]
                    print(f"    名称: {option['name']}")
                    print(f"    描述: {option.get('description', 'N/A')[:50]}...")
                
                return True
            else:
                print("✗ 获取详细信息失败")
                return False
        else:
            print("✗ 获取事件列表失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if crawler.driver:
            crawler.close_driver()


def verify_output_files():
    """验证输出文件"""
    print("\n" + "=" * 60)
    print("验证输出文件")
    print("=" * 60)
    
    # 检查怪物数据
    monsters_file = "6.0/data/monsters.json"
    if os.path.exists(monsters_file):
        data = load_json(monsters_file)
        if data and 'monsters' in data:
            print(f"✓ monsters.json 存在，包含 {len(data['monsters'])} 个怪物")
            
            # 检查第一个怪物的结构
            if data['monsters']:
                monster = data['monsters'][0]
                print(f"\n  第一个怪物: {monster['name']}")
                print(f"    - 技能: {len(monster.get('skills', []))} 个")
                print(f"    - 物品: {len(monster.get('items', []))} 个")
        else:
            print(f"✗ monsters.json 格式错误")
    else:
        print(f"✗ monsters.json 不存在")
    
    # 检查事件数据
    events_file = "6.0/data/events.json"
    if os.path.exists(events_file):
        data = load_json(events_file)
        if data and isinstance(data, list):
            print(f"✓ events.json 存在，包含 {len(data)} 个事件")
            
            # 检查第一个事件的结构
            if data:
                event = data[0]
                print(f"\n  第一个事件: {event['name']}")
                print(f"    - 选项: {len(event.get('options', []))} 个")
        else:
            print(f"✗ events.json 格式错误")
    else:
        print(f"✗ events.json 不存在")
    
    # 检查图标目录
    skills_dir = "6.0/icons/skills"
    items_dir = "6.0/icons/items"
    
    if os.path.exists(skills_dir):
        skill_count = len([f for f in os.listdir(skills_dir) if f.endswith(('.webp', '.png', '.jpg'))])
        print(f"✓ 技能图标目录存在，包含 {skill_count} 个图标")
    else:
        print(f"✗ 技能图标目录不存在")
    
    if os.path.exists(items_dir):
        item_count = len([f for f in os.listdir(items_dir) if f.endswith(('.webp', '.png', '.jpg'))])
        print(f"✓ 物品图标目录存在，包含 {item_count} 个图标")
    else:
        print(f"✗ 物品图标目录不存在")


def main():
    """主测试函数"""
    print("=" * 60)
    print("Bazaar爬虫测试工具")
    print("=" * 60)
    print("\n这个测试会:")
    print("1. 测试怪物爬虫（只获取第一个怪物）")
    print("2. 测试事件爬虫（只获取第一个事件）")
    print("3. 验证输出文件（如果存在）")
    print("\n注意: 测试过程会打开浏览器窗口")
    
    input("\n按Enter键开始测试...")
    
    results = {
        'monster': False,
        'event': False
    }
    
    # 测试怪物爬虫
    try:
        results['monster'] = test_monster_crawler()
    except KeyboardInterrupt:
        print("\n用户中断测试")
        return
    
    # 测试事件爬虫
    try:
        results['event'] = test_event_crawler()
    except KeyboardInterrupt:
        print("\n用户中断测试")
        return
    
    # 验证输出文件
    verify_output_files()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"怪物爬虫: {'✓ 通过' if results['monster'] else '✗ 失败'}")
    print(f"事件爬虫: {'✓ 通过' if results['event'] else '✗ 失败'}")
    
    if all(results.values()):
        print("\n✓ 所有测试通过！爬虫可以正常运行")
        print("\n运行完整爬取:")
        print("  cd 6.0/crawlers")
        print("  python main.py")
    else:
        print("\n✗ 部分测试失败，请检查错误信息")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n发生错误: {str(e)}")
        import traceback
        traceback.print_exc()




