"""
名称对比脚本
功能：
1. 对比新旧 unique_monsters.json，找出新增怪物
2. 对比新旧 unique_events.json，找出新增事件
3. 生成只包含新增项的列表文件
"""

import json
from pathlib import Path


def load_names(file_path):
    """加载名称列表"""
    try:
        if not Path(file_path).exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            # 处理不同格式
            if content.startswith('['):
                # JSON数组格式
                return json.loads(content)
            else:
                # 纯文本格式（每行一个）
                return [line.strip().strip('"') for line in content.split('\n') if line.strip()]
    except Exception as e:
        print(f"加载文件失败 {file_path}: {e}")
        return []


def load_existing_monsters():
    """从 monsters_v3.json 加载已有的怪物名称"""
    monster_file = Path('monster_details_v3/monsters_v3.json')
    if not monster_file.exists():
        return []
    
    try:
        with open(monster_file, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
            return [m['name'] for m in monsters if 'name' in m]
    except Exception as e:
        print(f"加载已有怪物数据失败: {e}")
        return []


def load_existing_events():
    """从 events_final.json 加载已有的事件名称"""
    event_file = Path('event_details_final/events_final.json')
    if not event_file.exists():
        return []
    
    try:
        with open(event_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
            return [e['name'] for e in events if 'name' in e]
    except Exception as e:
        print(f"加载已有事件数据失败: {e}")
        return []


def compare_and_generate():
    """对比并生成新增项列表"""
    
    print("=" * 80)
    print("名称对比工具 - 查找新增项")
    print("=" * 80)
    
    # 对比怪物
    print("\n[1/2] 对比怪物名称...")
    
    # 从最新抓取的 unique_monsters.json 加载
    new_monsters = load_names('unique_monsters.json')
    # 从已有数据中加载
    existing_monsters = load_existing_monsters()
    
    if not new_monsters:
        print("  ⚠ 警告: 未找到新的怪物名称列表 (unique_monsters.json)")
        print("  提示: 请先运行 fetch_monster_name.py 生成最新名称列表")
        added_monsters = []
    else:
        # 找出新增的怪物
        new_monster_set = set(new_monsters)
        existing_monster_set = set(existing_monsters)
        added_monsters = sorted(list(new_monster_set - existing_monster_set))
        
        print(f"  总怪物数: {len(new_monsters)}")
        print(f"  已有怪物: {len(existing_monsters)}")
        print(f"  新增怪物: {len(added_monsters)}")
        
        if added_monsters:
            print(f"\n  新增的怪物:")
            for name in added_monsters:
                print(f"    + {name}")
        else:
            print(f"  ✓ 没有新增怪物")
    
    # 对比事件
    print("\n[2/2] 对比事件名称...")
    
    # 从最新抓取的 unique_events.json 加载
    new_events = load_names('unique_events.json')
    # 从已有数据中加载
    existing_events = load_existing_events()
    
    if not new_events:
        print("  ⚠ 警告: 未找到新的事件名称列表 (unique_events.json)")
        print("  提示: 请先运行 fetch_event_name.py 生成最新名称列表")
        added_events = []
    else:
        # 找出新增的事件
        new_event_set = set(new_events)
        existing_event_set = set(existing_events)
        added_events = sorted(list(new_event_set - existing_event_set))
        
        print(f"  总事件数: {len(new_events)}")
        print(f"  已有事件: {len(existing_events)}")
        print(f"  新增事件: {len(added_events)}")
        
        if added_events:
            print(f"\n  新增的事件:")
            for name in added_events:
                print(f"    + {name}")
        else:
            print(f"  ✓ 没有新增事件")
    
    # 生成新增项列表文件
    print("\n" + "=" * 80)
    print("生成新增项列表文件...")
    print("=" * 80)
    
    # 保存新增怪物列表
    if added_monsters:
        new_monsters_file = Path('new_monsters.json')
        with open(new_monsters_file, 'w', encoding='utf-8') as f:
            json.dump(added_monsters, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 新增怪物列表已保存: {new_monsters_file}")
        print(f"  包含 {len(added_monsters)} 个新怪物")
    else:
        print(f"\n⊘ 无新增怪物，未生成文件")
    
    # 保存新增事件列表
    if added_events:
        new_events_file = Path('new_events.json')
        with open(new_events_file, 'w', encoding='utf-8') as f:
            json.dump(added_events, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 新增事件列表已保存: {new_events_file}")
        print(f"  包含 {len(added_events)} 个新事件")
    else:
        print(f"\n⊘ 无新增事件，未生成文件")
    
    # 总结
    print("\n" + "=" * 80)
    print("对比完成！")
    print("=" * 80)
    
    total_new_items = len(added_monsters) + len(added_events)
    
    if total_new_items > 0:
        print(f"\n总计发现 {total_new_items} 个新增项:")
        print(f"  - 新怪物: {len(added_monsters)}")
        print(f"  - 新事件: {len(added_events)}")
        print(f"\n下一步:")
        print(f"  1. 检查生成的 new_monsters.json 和 new_events.json")
        print(f"  2. 如果需要手动修正事件名称，请编辑 new_events.json")
        print(f"  3. 运行爬虫脚本只抓取新增项:")
        print(f"     - python selenium_monster_v3.py --input new_monsters.json")
        print(f"     - python selenium_event_final.py --input new_events.json")
    else:
        print(f"\n✓ 数据已是最新，无需更新")
    
    print("\n" + "=" * 80)
    
    return added_monsters, added_events


if __name__ == "__main__":
    try:
        compare_and_generate()
    except Exception as e:
        print(f"\n✗ 对比过程出现错误: {e}")
        import traceback
        traceback.print_exc()




