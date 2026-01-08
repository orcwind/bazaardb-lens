"""生成monsters_detail.json，包含怪物的中英文名称、技能和物品"""
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

def parse_monsters_from_html():
    """从monsters_from_html.json解析怪物、技能和物品的关联关系"""
    html_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_from_html.json"
    if not html_file.exists():
        print(f"错误: 文件不存在: {html_file}")
        return []
    
    with open(html_file, 'r', encoding='utf-8') as f:
        names_list = json.load(f)
    
    # 构建名称映射
    monster_names, skill_names, item_names = build_name_maps()
    
    # 结果列表
    monsters_detail = []
    
    # 当前处理的怪物
    current_monster = None
    current_skills = []
    current_items = []
    
    for name in names_list:
        normalized = normalize_name(name)
        
        # 检查是否是怪物
        if normalized in monster_names:
            # 如果之前有怪物，先保存
            if current_monster:
                monsters_detail.append({
                    "name_zh": current_monster.get('name_zh', ''),
                    "name": current_monster.get('name', ''),
                    "skills": current_skills,
                    "items": current_items
                })
            
            # 开始新的怪物
            current_monster = monster_names[normalized]
            current_skills = []
            current_items = []
        
        # 检查是否是技能
        elif normalized in skill_names:
            if current_monster:
                skill_info = skill_names[normalized]
                skill_data = {
                    "name": skill_info.get('name', normalized),
                    "name_zh": skill_info.get('name_zh', '')
                }
                # 避免重复添加相同的技能
                if skill_data not in current_skills:
                    current_skills.append(skill_data)
        
        # 检查是否是物品
        elif normalized in item_names:
            if current_monster:
                item_info = item_names[normalized]
                item_data = {
                    "name": item_info.get('name', normalized),
                    "name_zh": item_info.get('name_zh', '')
                }
                # 物品可能有重复（如Magma-Core出现4次），都添加
                current_items.append(item_data)
    
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
    print("正在解析怪物、技能和物品的关联关系...")
    
    # 解析数据
    monsters_detail = parse_monsters_from_html()
    
    print(f"找到 {len(monsters_detail)} 个怪物")
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in monsters_detail)
    total_items = sum(len(m['items']) for m in monsters_detail)
    print(f"  总技能数: {total_skills}")
    print(f"  总物品数: {total_items}")
    
    # 显示前3个怪物的信息
    print("\n前3个怪物示例:")
    for i, monster in enumerate(monsters_detail[:3], 1):
        print(f"\n{i}. {monster['name_zh']} ({monster['name']})")
        print(f"   技能: {len(monster['skills'])} 个")
        if monster['skills']:
            print(f"   - {monster['skills'][0]['name_zh']} ({monster['skills'][0]['name']})")
        print(f"   物品: {len(monster['items'])} 个")
        if monster['items']:
            print(f"   - {monster['items'][0]['name_zh']} ({monster['items'][0]['name']})")
    
    # 保存结果
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_detail.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(monsters_detail, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")

if __name__ == "__main__":
    main()

