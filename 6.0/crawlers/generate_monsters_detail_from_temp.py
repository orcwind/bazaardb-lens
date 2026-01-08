"""从temp_monster.json生成monsters_detail.json"""
import json
from pathlib import Path
from urllib.parse import unquote

def normalize_name(name):
    """标准化名称：去掉末尾反斜杠，将连字符替换为空格，首字母大写"""
    if not name:
        return ""
    # 去掉末尾反斜杠
    name = name.rstrip('\\')
    # URL解码
    name = unquote(name)
    # 将连字符替换为空格，首字母大写
    return name.replace('-', ' ').title()

def load_json_file(file_path):
    """加载JSON文件"""
    if not file_path.exists():
        print(f"警告: 文件不存在: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def build_name_maps():
    """构建名称映射表"""
    # 加载怪物列表
    monsters_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters.json"
    monsters = load_json_file(monsters_file)
    monster_names = {normalize_name(m.get('name', '')): m for m in monsters if isinstance(m, dict)}
    
    # 加载技能列表
    skills_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills.json"
    skills = load_json_file(skills_file)
    skill_names = {normalize_name(s.get('name', '')): s for s in skills if isinstance(s, dict)}
    
    # 加载物品列表
    items_file = Path(__file__).parent.parent.parent / "data" / "Json" / "items.json"
    items = load_json_file(items_file)
    item_names = {normalize_name(i.get('name', '')): i for i in items if isinstance(i, dict)}
    
    return monster_names, skill_names, item_names

def parse_monsters_from_temp():
    """从temp_monster.json解析怪物、技能和物品的关联关系"""
    temp_file = Path(__file__).parent.parent.parent / "data" / "Json" / "temp_monster.json"
    if not temp_file.exists():
        print(f"错误: 文件不存在: {temp_file}")
        return []
    
    with open(temp_file, 'r', encoding='utf-8') as f:
        names_list = json.load(f)
    
    print(f"从temp_monster.json读取到 {len(names_list)} 个名称")
    
    # 构建名称映射
    monster_names, skill_names, item_names = build_name_maps()
    
    # 过滤掉带反斜杠结尾的项
    filtered_names = []
    for name in names_list:
        normalized = normalize_name(name)
        # 跳过空名称
        if not normalized:
            continue
        filtered_names.append(normalized)
    
    print(f"过滤后剩余 {len(filtered_names)} 个名称")
    
    # 结果列表
    monsters_detail = []
    
    # 当前处理的怪物
    current_monster = None
    current_skills = []
    current_items = []
    
    i = 0
    while i < len(filtered_names):
        name = filtered_names[i]
        
        # 检查是否是怪物（需要检查连续两个相同的）
        is_monster = False
        monster_info = None
        
        if name in monster_names:
            # 检查下一个是否也是相同的怪物名称
            if i + 1 < len(filtered_names) and filtered_names[i + 1] == name:
                is_monster = True
                monster_info = monster_names[name]
                i += 2  # 跳过两个重复的怪物名称
        
        if is_monster:
            # 如果之前有怪物，先保存
            if current_monster:
                monsters_detail.append({
                    "name_zh": current_monster.get('name_zh', ''),
                    "name": current_monster.get('name', ''),
                    "skills": current_skills,
                    "items": current_items
                })
            
            # 开始新的怪物
            current_monster = monster_info
            current_skills = []
            current_items = []
            continue
        
        # 如果不是怪物，检查是否是技能或物品
        if current_monster:
            # 检查是否是技能
            if name in skill_names:
                skill_info = skill_names[name]
                skill_data = {
                    "name": skill_info.get('name', name),
                    "name_zh": skill_info.get('name_zh', '')
                }
                current_skills.append(skill_data)
            
            # 检查是否是物品
            elif name in item_names:
                item_info = item_names[name]
                item_data = {
                    "name": item_info.get('name', name),
                    "name_zh": item_info.get('name_zh', '')
                }
                # 物品可能有重复，都添加
                current_items.append(item_data)
        
        i += 1
    
    # 保存最后一个怪物
    if current_monster:
        monsters_detail.append({
            "name_zh": current_monster.get('name_zh', ''),
            "name": current_monster.get('name', ''),
            "skills": current_skills,
            "items": current_items
        })
    
    return monsters_detail

def main():
    """主函数"""
    print("正在从temp_monster.json解析怪物、技能和物品的关联关系...")
    
    # 解析数据
    monsters_detail = parse_monsters_from_temp()
    
    print(f"\n找到 {len(monsters_detail)} 个怪物")
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in monsters_detail)
    total_items = sum(len(m['items']) for m in monsters_detail)
    unique_skills = set()
    unique_items = set()
    for m in monsters_detail:
        for s in m['skills']:
            unique_skills.add(s['name'])
        for i in m['items']:
            unique_items.add(i['name'])
    
    print(f"  总技能数: {total_skills} (唯一: {len(unique_skills)})")
    print(f"  总物品数: {total_items} (唯一: {len(unique_items)})")
    
    # 显示前3个怪物的信息
    print("\n前3个怪物示例:")
    for i, monster in enumerate(monsters_detail[:3], 1):
        print(f"\n{i}. {monster['name_zh']} ({monster['name']})")
        print(f"   技能: {len(monster['skills'])} 个")
        if monster['skills']:
            for skill in monster['skills'][:3]:
                print(f"     - {skill['name_zh']} ({skill['name']})")
        print(f"   物品: {len(monster['items'])} 个")
        if monster['items']:
            for item in monster['items'][:3]:
                print(f"     - {item['name_zh']} ({item['name']})")
    
    # 检查Flame Juggler
    flame_juggler = next((m for m in monsters_detail if m['name'] == 'Flame Juggler'), None)
    if flame_juggler:
        print(f"\n示例: Flame Juggler (舞火大师)")
        print(f"  技能: {len(flame_juggler['skills'])} 个")
        for skill in flame_juggler['skills']:
            print(f"    - {skill['name_zh']} ({skill['name']})")
        print(f"  物品: {len(flame_juggler['items'])} 个")
        for item in flame_juggler['items']:
            print(f"    - {item['name_zh']} ({item['name']})")
    
    # 保存结果
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_detail.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(monsters_detail, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")

if __name__ == "__main__":
    main()

