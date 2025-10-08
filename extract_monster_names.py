import re
import json

def extract_monster_names(html_file_path):
    """
    从HTML文件中提取所有CombatEncounter类型的怪物名称
    
    Args:
        html_file_path: HTML文件路径
    
    Returns:
        包含所有怪物名称的列表
    """
    try:
        # 读取HTML文件
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 正则表达式匹配模式：
        # 基于图片中看到的实际格式：{"Type":"CombatEncounter","Title":{"Text":"怪物名称"}}
        pattern = r'"Type":"CombatEncounter","Title":\{"Text":"([^"]+)"\}'
        
        # 查找所有匹配项
        matches = re.findall(pattern, content)
        
        # 去重并排序
        monster_names = sorted(list(set(matches)))
        
        return monster_names
    
    except FileNotFoundError:
        print(f"错误：找不到文件 {html_file_path}")
        return []
    except Exception as e:
        print(f"错误：{str(e)}")
        return []

def main():
    # 目标HTML文件路径
    html_file = r'6.0\crawlers\6.0\debug_monsters.html'
    
    print(f"正在从 {html_file} 中提取怪物名称...")
    
    # 提取怪物名称
    monster_names = extract_monster_names(html_file)
    
    # 显示结果
    if monster_names:
        print(f"\n找到 {len(monster_names)} 个怪物：")
        print("-" * 50)
        for i, name in enumerate(monster_names, 1):
            print(f"{i}. {name}")
        
        # 保存到JSON文件
        output_file = 'extracted_monster_names.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "count": len(monster_names),
                "monster_names": monster_names
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到 {output_file}")
    else:
        print("\n未找到任何怪物名称。")
        print("提示：请确认HTML文件中的数据格式是否与预期一致。")

if __name__ == "__main__":
    main()