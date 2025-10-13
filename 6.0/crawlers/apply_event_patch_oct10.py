"""
应用2025年10月10日补丁更新到事件数据
"""

import json
from pathlib import Path

# 事件选项描述更新
EVENT_UPDATES = {
    "The Docks": {
        "Work as Navigator": {
            "old": "(if you have an Astrolabe) Gain 5 Gold and 1 XP.",
            "new": "(if you have a Star Chart) Gain 2 Gold and 1 XP."
        }
    },
    "BazaarCON": {
        "Networking": {
            "old": "Gain 2 Income and 1 XP.",
            "new": "Gain 2 Income and 1 XP."  # 已经是正确的
        },
        "Swag Collector": {
            "old": "Get 3 Small Enchanted items from the Bazaar.",
            "new": "Get 3 Small Enchanted items from the Bazaar."  # 已经是正确的
        }
    },
    "Investment Pitch": {
        "Mentor's Guidance": {
            "old": "Gain 2 XP and +10% Max Health.",
            "new": "Gain 2 XP and +10% Max Health."  # 已经是正确的
        }
    }
}


def update_events(events_file):
    """更新事件数据"""
    print("="*80)
    print("更新事件数据")
    print("="*80)
    
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    update_count = 0
    
    for event in events:
        event_name = event.get('name')
        
        if event_name in EVENT_UPDATES:
            event_update_rules = EVENT_UPDATES[event_name]
            
            for choice in event.get('choices', []):
                choice_name = choice.get('name')
                
                if choice_name in event_update_rules:
                    update_rule = event_update_rules[choice_name]
                    old_desc = choice.get('description', '')
                    
                    if old_desc == update_rule['old']:
                        choice['description'] = update_rule['new']
                        update_count += 1
                        print(f"✓ 更新: {event_name} - {choice_name}")
                    elif old_desc == update_rule['new']:
                        print(f"⚪ 已是新版本: {event_name} - {choice_name}")
                    else:
                        print(f"⚠ 描述不匹配: {event_name} - {choice_name}")
                        print(f"  当前: {old_desc}")
                        print(f"  期望: {update_rule['old']}")
    
    # 保存更新后的数据
    with open(events_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 更新了 {update_count} 个事件选项")
    print(f"✓ 已保存到: {events_file}")
    
    return update_count


def check_event_completeness(events_file):
    """检查事件数据完整性"""
    print("\n" + "="*80)
    print("事件数据完整性检查")
    print("="*80)
    
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    print(f"\n当前事件数: {len(events)}")
    print(f"\n事件列表:")
    for i, event in enumerate(events, 1):
        choice_count = len(event.get('choices', []))
        print(f"  {i:2d}. {event['name']:30s} - {choice_count} 选项")
    
    # 检查缺失的aspect_ratio
    missing_ar = []
    for event in events:
        for choice in event.get('choices', []):
            if 'aspect_ratio' not in choice:
                missing_ar.append((event['name'], choice['name']))
    
    if missing_ar:
        print(f"\n⚠ 缺失长宽比: {len(missing_ar)} 个")
        for event_name, choice_name in missing_ar[:5]:
            print(f"  - {event_name} - {choice_name}")
        if len(missing_ar) > 5:
            print(f"  ... 还有 {len(missing_ar) - 5} 个")
    else:
        print(f"\n✓ 所有选项都有长宽比")


def main():
    """主函数"""
    print("="*80)
    print("应用事件数据补丁 - 2025年10月10日")
    print("="*80)
    
    events_file = Path('events_final.json')
    
    # 1. 更新事件描述
    update_count = update_events(events_file)
    
    # 2. 检查完整性
    check_event_completeness(events_file)
    
    # 3. 总结
    print("\n" + "="*80)
    print("补丁应用完成")
    print("="*80)
    print(f"\n✓ 更新事件选项: {update_count} 个")
    print(f"\n📝 说明:")
    print(f"  - 当前events_final.json有15个事件")
    print(f"  - unique_events.json有37个事件")
    print(f"  - 缺少22个新事件（多为角色专属遭遇）")
    print(f"  - 建议: 保持当前数据，避免爬虫脚本失败问题")


if __name__ == "__main__":
    main()


