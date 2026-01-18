"""
检查 monsters_detail.json 文件的完整性
检查缺失的中文名称、生命值、品质等信息
"""
import json
import os

def check_monsters_detail_completeness():
    """检查 monsters_detail.json 的完整性"""
    json_file = os.path.join('data', 'Json', 'monsters_detail.json')
    
    if not os.path.exists(json_file):
        print(f"错误：未找到文件 {json_file}")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
    except Exception as e:
        print(f"错误：读取文件失败: {e}")
        return
    
    print(f"检查文件：{json_file}")
    print(f"怪物总数：{len(monsters)}\n")
    print("=" * 80)
    
    issues = []
    total_monsters = len(monsters)
    
    for idx, monster in enumerate(monsters, 1):
        monster_name = monster.get('name', f'未知怪物#{idx}')
        monster_name_zh = monster.get('name_zh', '')
        issues_found = []
        
        # 1. 检查怪物中文名称
        if not monster_name_zh:
            issues_found.append(f"缺少中文名称 (name_zh)")
        
        # 2. 检查生命值
        if 'health' not in monster:
            issues_found.append(f"缺少生命值 (health)")
        
        # 3. 检查技能
        skills = monster.get('skills', [])
        for skill_idx, skill in enumerate(skills):
            skill_name = skill.get('name', f'未知技能#{skill_idx+1}')
            skill_name_zh = skill.get('name_zh', '')
            skill_quality = skill.get('quality')
            
            if not skill_name_zh:
                issues_found.append(f"技能 '{skill_name}' 缺少中文名称 (name_zh)")
            if skill_quality is None or skill_quality == '':
                issues_found.append(f"技能 '{skill_name}' 缺少品质 (quality)")
        
        # 4. 检查物品
        items = monster.get('items', [])
        for item_idx, item in enumerate(items):
            item_name = item.get('name', f'未知物品#{item_idx+1}')
            item_name_zh = item.get('name_zh', '')
            item_quality = item.get('quality')
            
            if not item_name_zh:
                issues_found.append(f"物品 '{item_name}' 缺少中文名称 (name_zh)")
            if item_quality is None or item_quality == '':
                issues_found.append(f"物品 '{item_name}' 缺少品质 (quality)")
        
        # 如果有问题，记录
        if issues_found:
            issues.append({
                'index': idx,
                'name': monster_name,
                'name_zh': monster_name_zh or '(无)',
                'health': monster.get('health', '(缺失)'),
                'issues': issues_found
            })
    
    # 输出结果
    if not issues:
        print("✅ 检查完成：未发现缺失信息！")
        print(f"所有 {total_monsters} 个怪物的数据完整。")
    else:
        print(f"❌ 发现 {len(issues)} 个怪物存在缺失信息：\n")
        
        for issue in issues:
            print(f"【怪物 #{issue['index']}】{issue['name']} ({issue['name_zh']})")
            print(f"  生命值: {issue['health']}")
            print(f"  问题：")
            for problem in issue['issues']:
                print(f"    - {problem}")
            print()
        
        print("=" * 80)
        print(f"总结：{len(issues)}/{total_monsters} 个怪物存在缺失信息")
        
        # 统计缺失类型
        missing_name_zh = sum(1 for i in issues if any('缺少中文名称' in p and 'name_zh' in p for p in i['issues']))
        missing_health = sum(1 for i in issues if '缺少生命值' in str(i['issues']))
        missing_skill_quality = sum(1 for i in issues if any('技能' in p and '品质' in p for p in i['issues']))
        missing_item_quality = sum(1 for i in issues if any('物品' in p and '品质' in p for p in i['issues']))
        missing_skill_name_zh = sum(1 for i in issues if any('技能' in p and '中文名称' in p for p in i['issues']))
        missing_item_name_zh = sum(1 for i in issues if any('物品' in p and '中文名称' in p for p in i['issues']))
        
        print("\n缺失统计：")
        if missing_name_zh > 0:
            print(f"  - 缺少怪物中文名称: {missing_name_zh} 个")
        if missing_health > 0:
            print(f"  - 缺少生命值: {missing_health} 个")
        if missing_skill_name_zh > 0:
            print(f"  - 缺少技能中文名称: {missing_skill_name_zh} 个技能")
        if missing_skill_quality > 0:
            print(f"  - 缺少技能品质: {missing_skill_quality} 个技能")
        if missing_item_name_zh > 0:
            print(f"  - 缺少物品中文名称: {missing_item_name_zh} 个物品")
        if missing_item_quality > 0:
            print(f"  - 缺少物品品质: {missing_item_quality} 个物品")

if __name__ == '__main__':
    check_monsters_detail_completeness()
