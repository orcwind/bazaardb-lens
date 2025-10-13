"""
备份当前数据脚本
功能：
1. 自动备份 monsters_v3.json 和 events_final.json
2. 备份所有图标文件
3. 创建带时间戳的备份目录
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def backup_data():
    """备份当前所有数据"""
    
    # 创建备份目录（带时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path(f'backups/backup_{timestamp}')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print(f"开始备份数据到: {backup_dir}")
    print("=" * 80)
    
    backup_summary = {
        'timestamp': timestamp,
        'files_backed_up': [],
        'errors': []
    }
    
    # 备份怪物数据
    print("\n[1/4] 备份怪物数据...")
    monster_source = Path('monster_details_v3')
    if monster_source.exists():
        monster_backup = backup_dir / 'monster_details_v3'
        try:
            shutil.copytree(monster_source, monster_backup)
            
            # 统计
            json_file = monster_backup / 'monsters_v3.json'
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    monsters = json.load(f)
                    monster_count = len(monsters)
                    
            icon_count = len(list((monster_backup / 'icons').glob('*.webp')))
            
            print(f"  ✓ 已备份: {monster_count} 个怪物")
            print(f"  ✓ 已备份: {icon_count} 个图标")
            backup_summary['files_backed_up'].append(f"monsters_v3.json ({monster_count} monsters, {icon_count} icons)")
            
        except Exception as e:
            error_msg = f"备份怪物数据失败: {e}"
            print(f"  ✗ {error_msg}")
            backup_summary['errors'].append(error_msg)
    else:
        print("  ⚠ 未找到怪物数据目录")
        backup_summary['errors'].append("monster_details_v3 目录不存在")
    
    # 备份事件数据
    print("\n[2/4] 备份事件数据...")
    event_source = Path('event_details_final')
    if event_source.exists():
        event_backup = backup_dir / 'event_details_final'
        try:
            shutil.copytree(event_source, event_backup)
            
            # 统计
            json_file = event_backup / 'events_final.json'
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
                    event_count = len(events)
                    
            # 统计所有子目录的图标
            icon_count = len(list((event_backup / 'icons').rglob('*.webp')))
            
            print(f"  ✓ 已备份: {event_count} 个事件")
            print(f"  ✓ 已备份: {icon_count} 个图标")
            backup_summary['files_backed_up'].append(f"events_final.json ({event_count} events, {icon_count} icons)")
            
        except Exception as e:
            error_msg = f"备份事件数据失败: {e}"
            print(f"  ✗ {error_msg}")
            backup_summary['errors'].append(error_msg)
    else:
        print("  ⚠ 未找到事件数据目录")
        backup_summary['errors'].append("event_details_final 目录不存在")
    
    # 备份名称列表
    print("\n[3/4] 备份名称列表...")
    name_files = ['unique_monsters.json', 'unique_events.json']
    for name_file in name_files:
        source = Path(name_file)
        if source.exists():
            try:
                shutil.copy2(source, backup_dir / name_file)
                print(f"  ✓ 已备份: {name_file}")
                backup_summary['files_backed_up'].append(name_file)
            except Exception as e:
                error_msg = f"备份 {name_file} 失败: {e}"
                print(f"  ✗ {error_msg}")
                backup_summary['errors'].append(error_msg)
        else:
            print(f"  ⚠ 未找到: {name_file}")
    
    # 保存备份摘要
    print("\n[4/4] 保存备份摘要...")
    summary_file = backup_dir / 'backup_summary.json'
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(backup_summary, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 备份摘要已保存")
    except Exception as e:
        print(f"  ✗ 保存备份摘要失败: {e}")
    
    # 最终报告
    print("\n" + "=" * 80)
    print("备份完成！")
    print("=" * 80)
    print(f"\n备份位置: {backup_dir.absolute()}")
    print(f"备份文件数: {len(backup_summary['files_backed_up'])}")
    
    if backup_summary['errors']:
        print(f"\n⚠ 警告: 发现 {len(backup_summary['errors'])} 个错误:")
        for error in backup_summary['errors']:
            print(f"  - {error}")
    else:
        print("\n✓ 所有数据备份成功！")
    
    print("\n" + "=" * 80)
    
    return backup_dir


if __name__ == "__main__":
    try:
        backup_dir = backup_data()
        print(f"\n提示: 如需恢复，请从 {backup_dir} 复制文件到相应位置")
    except Exception as e:
        print(f"\n✗ 备份过程出现严重错误: {e}")
        import traceback
        traceback.print_exc()




