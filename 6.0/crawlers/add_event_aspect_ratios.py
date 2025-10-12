"""
为events_final.json中的所有选项添加aspect_ratio
所有事件图标都是1.0（正方形）
"""

import json
from pathlib import Path


def add_aspect_ratios(events_file):
    """为所有事件选项添加aspect_ratio"""
    print("="*80)
    print("为事件选项添加长宽比")
    print("="*80)
    
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    added_count = 0
    
    for event in events:
        event_name = event.get('name')
        
        for choice in event.get('choices', []):
            choice_name = choice.get('name')
            
            if 'aspect_ratio' not in choice:
                choice['aspect_ratio'] = 1.0
                added_count += 1
                print(f"  ✓ {event_name} - {choice_name}")
    
    # 保存更新后的数据
    with open(events_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 添加了 {added_count} 个aspect_ratio")
    print(f"✓ 已保存到: {events_file}")
    
    return added_count


def verify_completeness(events_file):
    """验证数据完整性"""
    print("\n" + "="*80)
    print("验证数据完整性")
    print("="*80)
    
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    total_choices = 0
    missing_ar = 0
    empty_desc = 0
    
    for event in events:
        for choice in event.get('choices', []):
            total_choices += 1
            
            if 'aspect_ratio' not in choice:
                missing_ar += 1
            
            if not choice.get('description', '').strip():
                empty_desc += 1
    
    print(f"\n总计:")
    print(f"  事件数: {len(events)}")
    print(f"  选项数: {total_choices}")
    print(f"  空描述: {empty_desc}")
    print(f"  缺失长宽比: {missing_ar}")
    
    if missing_ar == 0 and empty_desc == 0:
        print(f"\n✅ 数据完整！")
    else:
        print(f"\n⚠ 存在问题需要修复")


def main():
    """主函数"""
    print("="*80)
    print("事件数据长宽比补充")
    print("="*80)
    
    events_file = Path('events_final.json')
    
    # 1. 添加aspect_ratio
    added = add_aspect_ratios(events_file)
    
    # 2. 验证完整性
    verify_completeness(events_file)
    
    print("\n" + "="*80)
    print("完成")
    print("="*80)


if __name__ == "__main__":
    main()

