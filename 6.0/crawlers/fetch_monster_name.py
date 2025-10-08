import re
import json
from html import unescape

def extract_combat_encounters(html_file_path):
    """
    从HTML文件中提取战斗遭遇怪物名称
    """
    print("=" * 80)
    print("开始提取怪物名称...")
    print("=" * 80)
    
    # 步骤1: 读取HTML文件
    print(f"\n[步骤1] 读取HTML文件: {html_file_path}")
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"  文件大小: {len(content)} 字符")
    
    # 步骤2: 查找所有CombatEncounter出现的位置
    print("\n[步骤2] 查找所有 CombatEncounter...")
    all_matches = list(re.finditer(r'CombatEncounter', content))
    print(f"  总共找到 {len(all_matches)} 个 CombatEncounter")
    
    # 步骤3: 提取每个CombatEncounter后面的80个字符
    print("\n[步骤3] 提取片段...")
    snippets = []
    for i, match in enumerate(all_matches, 1):
        end_pos = match.end()
        next_80_chars = content[end_pos:end_pos+80]
        snippets.append({
            "index": i,
            "snippet": next_80_chars
        })
    print(f"  已提取 {len(snippets)} 个片段")
    
    # 步骤4: 从片段中提取怪物名称
    print("\n[步骤4] 从片段中提取怪物名称...")
    monster_names = []
    pattern = r'\\"Title\\":\{\\"Text\\":\\"([^"\\]+)\\"'
    
    for item in snippets:
        snippet = item['snippet']
        match = re.search(pattern, snippet)
        if match:
            name = unescape(match.group(1))
            monster_names.append({
                "index": item['index'],
                "name": name
            })
    
    print(f"  成功提取 {len(monster_names)} 个怪物名称")
    
    # 步骤5: 去重
    print("\n[步骤5] 去除重复...")
    unique_names = []
    seen = set()
    for item in monster_names:
        if item['name'] not in seen:
            seen.add(item['name'])
            unique_names.append(item['name'])
    
    print(f"  去重后剩余 {len(unique_names)} 个唯一怪物名称")
    
    # 步骤6: 保存结果
    print("\n[步骤6] 保存结果...")
    
    # 保存去重后的怪物列表（每行一个名称，不带中括号）
    with open('unique_monsters.json', 'w', encoding='utf-8') as f:
        for name in unique_names:
            f.write(f'"{name}"\n')
    print("  ✓ 已保存: unique_monsters.json")
    
    # 显示结果预览
    print("\n" + "=" * 80)
    print(f"提取完成！共 {len(unique_names)} 个唯一怪物")
    print("=" * 80)
    print("\n前20个怪物名称：")
    for i, name in enumerate(unique_names[:20], 1):
        print(f"  {i:2d}. {name}")
    
    if len(unique_names) > 20:
        print(f"  ... 还有 {len(unique_names) - 20} 个怪物")
    
    print("\n" + "=" * 80)
    
    return unique_names


if __name__ == "__main__":
    # 设置HTML文件路径
    html_file = 'debug_monsters.html'
    
    try:
        # 执行提取
        monsters = extract_combat_encounters(html_file)
        
        print(f"\n✓ 成功提取 {len(monsters)} 个唯一怪物名称")
        print(f"✓ 结果已保存到 unique_monsters.json")
        
    except FileNotFoundError:
        print(f"\n✗ 错误: 找不到文件 {html_file}")
        print("  请确认文件路径是否正确")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()