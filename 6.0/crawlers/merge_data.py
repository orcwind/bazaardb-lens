"""
智能数据合并脚本
功能：
1. 将新爬取的数据合并到现有数据中
2. 保留手动修正的内容
3. 智能处理重复项（优先保留旧数据）
4. 生成详细的合并报告
"""

import json
from pathlib import Path
from datetime import datetime


def load_json(file_path):
    """加载JSON文件"""
    try:
        if not Path(file_path).exists():
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载文件失败 {file_path}: {e}")
        return None


def save_json(data, file_path):
    """保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存文件失败 {file_path}: {e}")
        return False


def merge_monsters():
    """合并怪物数据"""
    print("\n[1/2] 合并怪物数据...")
    
    # 加载现有数据
    existing_file = Path('monster_details_v3/monsters_v3.json')
    existing_data = load_json(existing_file)
    
    if not existing_data:
        print("  ⚠ 未找到现有怪物数据")
        return None
    
    # 创建名称到数据的映射
    existing_map = {monster['name']: monster for monster in existing_data}
    
    print(f"  已加载现有数据: {len(existing_data)} 个怪物")
    
    # 检查是否有临时数据（新爬取的）
    temp_file = Path('monster_details_v3_temp/monsters_v3.json')
    if not temp_file.exists():
        print(f"  ⊘ 未找到新数据文件: {temp_file}")
        print(f"  提示: 如果你已经运行了爬虫，数据可能已经自动合并到原文件中")
        return None
    
    # 加载新数据
    new_data = load_json(temp_file)
    if not new_data:
        print("  ⚠ 无法加载新数据")
        return None
    
    print(f"  已加载新数据: {len(new_data)} 个怪物")
    
    # 合并数据
    added_count = 0
    skipped_count = 0
    
    for monster in new_data:
        name = monster.get('name')
        if not name:
            continue
        
        if name in existing_map:
            # 已存在，跳过（保留手动修正的内容）
            skipped_count += 1
            print(f"    ⊘ 跳过已存在: {name}")
        else:
            # 新增
            existing_map[name] = monster
            added_count += 1
            print(f"    + 新增: {name}")
    
    # 保存合并结果
    merged_data = list(existing_map.values())
    
    # 创建备份
    backup_file = existing_file.with_suffix('.json.backup')
    if save_json(existing_data, backup_file):
        print(f"\n  ✓ 原数据已备份: {backup_file}")
    
    # 保存合并后的数据
    if save_json(merged_data, existing_file):
        print(f"  ✓ 合并后的数据已保存: {existing_file}")
    else:
        print(f"  ✗ 保存失败")
        return None
    
    print(f"\n  合并统计:")
    print(f"    原有: {len(existing_data)}")
    print(f"    新增: {added_count}")
    print(f"    跳过: {skipped_count}")
    print(f"    最终: {len(merged_data)}")
    
    return {
        'original': len(existing_data),
        'added': added_count,
        'skipped': skipped_count,
        'final': len(merged_data)
    }


def merge_events():
    """合并事件数据"""
    print("\n[2/2] 合并事件数据...")
    
    # 加载现有数据
    existing_file = Path('event_details_final/events_final.json')
    existing_data = load_json(existing_file)
    
    if not existing_data:
        print("  ⚠ 未找到现有事件数据")
        return None
    
    # 创建名称到数据的映射
    existing_map = {event['name']: event for event in existing_data}
    
    print(f"  已加载现有数据: {len(existing_data)} 个事件")
    
    # 检查是否有临时数据（新爬取的）
    temp_file = Path('event_details_final_temp/events_final.json')
    if not temp_file.exists():
        print(f"  ⊘ 未找到新数据文件: {temp_file}")
        print(f"  提示: 如果你已经运行了爬虫，数据可能已经自动合并到原文件中")
        return None
    
    # 加载新数据
    new_data = load_json(temp_file)
    if not new_data:
        print("  ⚠ 无法加载新数据")
        return None
    
    print(f"  已加载新数据: {len(new_data)} 个事件")
    
    # 合并数据
    added_count = 0
    skipped_count = 0
    
    for event in new_data:
        name = event.get('name')
        if not name:
            continue
        
        if name in existing_map:
            # 已存在，跳过（保留手动修正的内容）
            skipped_count += 1
            print(f"    ⊘ 跳过已存在: {name}")
        else:
            # 新增
            existing_map[name] = event
            added_count += 1
            print(f"    + 新增: {name}")
    
    # 保存合并结果
    merged_data = list(existing_map.values())
    
    # 创建备份
    backup_file = existing_file.with_suffix('.json.backup')
    if save_json(existing_data, backup_file):
        print(f"\n  ✓ 原数据已备份: {backup_file}")
    
    # 保存合并后的数据
    if save_json(merged_data, existing_file):
        print(f"  ✓ 合并后的数据已保存: {existing_file}")
    else:
        print(f"  ✗ 保存失败")
        return None
    
    print(f"\n  合并统计:")
    print(f"    原有: {len(existing_data)}")
    print(f"    新增: {added_count}")
    print(f"    跳过: {skipped_count}")
    print(f"    最终: {len(merged_data)}")
    
    return {
        'original': len(existing_data),
        'added': added_count,
        'skipped': skipped_count,
        'final': len(merged_data)
    }


def main():
    """主函数"""
    print("=" * 80)
    print("智能数据合并工具")
    print("=" * 80)
    print("\n注意: 此工具会保留所有手动修正的内容，只添加新增项")
    print("      已存在的项不会被覆盖")
    
    monster_result = merge_monsters()
    event_result = merge_events()
    
    # 生成合并报告
    print("\n" + "=" * 80)
    print("合并完成！")
    print("=" * 80)
    
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monsters': monster_result,
        'events': event_result
    }
    
    # 保存报告
    report_file = Path('merge_report.json')
    if save_json(report, report_file):
        print(f"\n✓ 合并报告已保存: {report_file}")
    
    # 显示总结
    if monster_result or event_result:
        total_added = 0
        if monster_result:
            total_added += monster_result['added']
        if event_result:
            total_added += event_result['added']
        
        print(f"\n总计新增项目: {total_added}")
        
        if total_added > 0:
            print(f"\n✓ 数据已成功更新，手动修正的内容已保留")
        else:
            print(f"\n⊘ 没有新增项，数据保持不变")
    else:
        print(f"\n⊘ 未找到需要合并的新数据")
        print(f"   如果爬虫已运行，数据可能已经自动合并")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 合并过程出现错误: {e}")
        import traceback
        traceback.print_exc()



