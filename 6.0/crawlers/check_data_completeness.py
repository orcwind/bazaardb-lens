"""
检查 monsters_v3.json 的数据完整性
"""

import json
from pathlib import Path

def check_completeness():
    """检查数据完整性"""
    json_file = Path('monster_details_v3/monsters_v3.json')
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("怪物数据完整性检查")
    print("=" * 80)
    
    # 基本统计
    total_monsters = len(data)
    total_skills = sum(len(m['skills']) for m in data)
    total_items = sum(len(m['items']) for m in data)
    
    print(f"\n基本统计:")
    print(f"  怪物总数: {total_monsters}")
    print(f"  技能总数: {total_skills}")
    print(f"  物品总数: {total_items}")
    
    # 检查缺失项
    missing_icons = []
    missing_desc = []
    empty_icons_url = []
    empty_skills = []
    empty_items = []
    
    for monster in data:
        # 检查技能
        for skill in monster['skills']:
            if not skill.get('icon'):
                missing_icons.append(f"{monster['name']} - {skill['name']} (技能)")
            if not skill.get('icon_url'):
                empty_icons_url.append(f"{monster['name']} - {skill['name']} (技能)")
            if not skill.get('description'):
                missing_desc.append(f"{monster['name']} - {skill['name']} (技能)")
        
        # 检查物品
        for item in monster['items']:
            if not item.get('icon'):
                missing_icons.append(f"{monster['name']} - {item['name']} (物品)")
            if not item.get('icon_url'):
                empty_icons_url.append(f"{monster['name']} - {item['name']} (物品)")
            if not item.get('description'):
                missing_desc.append(f"{monster['name']} - {item['name']} (物品)")
        
        # 检查空列表
        if len(monster['skills']) == 0:
            empty_skills.append(monster['name'])
        if len(monster['items']) == 0:
            empty_items.append(monster['name'])
    
    # 输出结果
    print(f"\n完整性检查:")
    print(f"  缺少图标文件: {len(missing_icons)}")
    print(f"  缺少图标URL: {len(empty_icons_url)}")
    print(f"  缺少描述: {len(missing_desc)}")
    print(f"  无技能怪物: {len(empty_skills)}")
    print(f"  无物品怪物: {len(empty_items)}")
    
    if missing_icons:
        print(f"\n缺少图标文件的项 (前10个):")
        for item in missing_icons[:10]:
            print(f"  - {item}")
        if len(missing_icons) > 10:
            print(f"  ... 还有 {len(missing_icons) - 10} 个")
    
    if empty_icons_url:
        print(f"\n缺少图标URL的项:")
        for item in empty_icons_url:
            print(f"  - {item}")
    
    if missing_desc:
        print(f"\n缺少描述的项 (前10个):")
        for item in missing_desc[:10]:
            print(f"  - {item}")
        if len(missing_desc) > 10:
            print(f"  ... 还有 {len(missing_desc) - 10} 个")
    
    if empty_skills:
        print(f"\n无技能的怪物:")
        for name in empty_skills:
            print(f"  - {name}")
    
    if empty_items:
        print(f"\n无物品的怪物:")
        for name in empty_items:
            print(f"  - {name}")
    
    # 计算完整度
    total_cards = total_skills + total_items
    complete_cards = total_cards - len(missing_icons)
    completeness = (complete_cards / total_cards * 100) if total_cards > 0 else 0
    
    print(f"\n{'=' * 80}")
    print(f"完整度评估:")
    print(f"  总卡片数: {total_cards}")
    print(f"  完整卡片数: {complete_cards}")
    print(f"  完整度: {completeness:.2f}%")
    print("=" * 80)
    
    return {
        'total_monsters': total_monsters,
        'total_skills': total_skills,
        'total_items': total_items,
        'missing_icons': len(missing_icons),
        'missing_desc': len(missing_desc),
        'completeness': completeness
    }

if __name__ == "__main__":
    check_completeness()
