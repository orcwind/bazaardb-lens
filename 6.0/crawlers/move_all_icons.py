"""
移动所有图标到统一目录 data/icon
功能：
1. 扫描所有图标目录
2. 统一命名规则（处理空格、引号等特殊字符）
3. 移动到 data/icon 目录
4. 更新JSON文件中的icon字段
"""

import os
import json
import shutil
import re
from pathlib import Path

def sanitize_filename(name):
    """统一文件名规则：处理空格、引号等特殊字符"""
    if not isinstance(name, str):
        return ""
    
    # 替换引号为下划线
    name = name.replace('"', '_').replace("'", '_')
    # 替换多个空格为单个下划线
    name = re.sub(r'\s+', '_', name)
    # 移除其他非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 移除首尾下划线和空格
    name = name.strip('_').strip()
    
    return name

def find_all_icons():
    """查找所有图标文件"""
    icons = []
    
    # 扫描的目录
    search_dirs = [
        Path('monster_details_v3/icons'),
        Path('event_details_final/icons'),
        Path('items_details/icons'),
        Path('skills_details/icons'),
        Path('icons'),  # 根目录下的icons
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        # 递归查找所有webp文件
        for icon_file in search_dir.rglob('*.webp'):
            icons.append(icon_file)
    
    return icons

def move_icons_to_unified_dir():
    """移动所有图标到统一目录"""
    target_dir = Path('../../data/icon')
    target_dir.mkdir(parents=True, exist_ok=True)
    
    icons = find_all_icons()
    print(f"找到 {len(icons)} 个图标文件")
    
    moved_count = 0
    skipped_count = 0
    error_count = 0
    
    for icon_file in icons:
        try:
            # 获取原始文件名（不含路径）
            original_name = icon_file.name
            
            # 如果文件名已经符合规范，直接使用
            # 否则需要根据路径信息重命名
            if icon_file.parent.name in ['icons']:
                # 如果是在icons目录下，可能是 怪物名_卡片名.webp 格式
                new_name = sanitize_filename(original_name)
            else:
                # 如果是在子目录中，需要包含父目录名
                # 例如: event_details_final/icons/A Strange Mushroom/Trade It for Something.webp
                # 应该变成: A_Strange_Mushroom_Trade_It_for_Something.webp
                parts = []
                for part in icon_file.parts:
                    if part not in ['icons', 'event_details_final', 'monster_details_v3', 'items_details', 'skills_details']:
                        parts.append(part)
                
                # 移除扩展名，合并所有部分
                name_without_ext = '.'.join(parts[:-1]) if len(parts) > 1 else parts[0]
                new_name = sanitize_filename(name_without_ext) + '.webp'
            
            target_path = target_dir / new_name
            
            # 如果目标文件已存在，检查是否相同
            if target_path.exists():
                if target_path.stat().st_size == icon_file.stat().st_size:
                    # 文件大小相同，跳过
                    skipped_count += 1
                    continue
                else:
                    # 文件不同，添加序号
                    base_name = new_name.rsplit('.', 1)[0]
                    ext = new_name.rsplit('.', 1)[1]
                    counter = 1
                    while target_path.exists():
                        new_name = f"{base_name}_{counter}.webp"
                        target_path = target_dir / new_name
                        counter += 1
            
            # 移动文件
            shutil.move(str(icon_file), str(target_path))
            moved_count += 1
            print(f"  ✓ {icon_file} -> {target_path.name}")
            
        except Exception as e:
            print(f"  ✗ 移动失败 {icon_file}: {e}")
            error_count += 1
    
    print(f"\n移动完成:")
    print(f"  移动: {moved_count} 个")
    print(f"  跳过: {skipped_count} 个")
    print(f"  错误: {error_count} 个")
    print(f"  目标目录: {target_dir.absolute()}")

def update_json_files():
    """更新JSON文件中的icon字段，移除icon_url，只保留文件名"""
    json_files = [
        Path('monster_details_v3/monsters_v3.json'),
        Path('event_details_final/events_final.json'),
        Path('items_details/items.json'),
        Path('skills_details/skills.json'),
    ]
    
    for json_file in json_files:
        if not json_file.exists():
            continue
        
        print(f"\n更新 {json_file}...")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            updated = False
            
            if isinstance(data, list):
                for item in data:
                    if update_item_icon_fields(item):
                        updated = True
            elif isinstance(data, dict):
                if update_item_icon_fields(data):
                    updated = True
            
            if updated:
                # 保存到新位置
                target_dir = Path('../../data/Json')
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / json_file.name
                
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"  ✓ 已更新并保存到 {target_file}")
            else:
                print(f"  - 无需更新")
                
        except Exception as e:
            print(f"  ✗ 更新失败: {e}")

def update_item_icon_fields(item):
    """更新单个item的icon字段"""
    updated = False
    
    # 处理技能和物品
    for field in ['skills', 'items', 'choices']:
        if field in item and isinstance(item[field], list):
            for sub_item in item[field]:
                if update_icon_field(sub_item):
                    updated = True
    
    # 处理直接包含icon的item（物品和技能）
    if update_icon_field(item):
        updated = True
    
    return updated

def update_icon_field(item):
    """更新icon字段：移除icon_url，规范化icon字段"""
    updated = False
    
    if 'icon_url' in item:
        # 移除icon_url字段
        del item['icon_url']
        updated = True
    
    if 'icon' in item:
        icon_path = item['icon']
        if isinstance(icon_path, str):
            # 提取文件名
            filename = os.path.basename(icon_path)
            # 规范化文件名
            item['icon'] = sanitize_filename(filename.replace('.webp', '')) + '.webp'
            updated = True
    
    return updated

def main():
    """主函数"""
    print("=" * 80)
    print("移动所有图标到统一目录")
    print("=" * 80)
    
    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 移动图标
    print("\n[1/2] 移动图标文件...")
    move_icons_to_unified_dir()
    
    # 更新JSON文件
    print("\n[2/2] 更新JSON文件...")
    update_json_files()
    
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()


