import json
import re
from html import unescape

def extract_combat_encounters(html_content):
    """
    从HTML内容中提取战斗遭遇信息
    """
    # 正则表达式匹配 "Type":"CombatEncounter","Title":{"Text":"..."} 模式
    pattern = r'"Type":"CombatEncounter","Title":\s*{\s*"Text":\s*"([^"]+)"'
    
    # 查找所有匹配项
    matches = re.findall(pattern, html_content)
    
    # 处理HTML转义字符
    cleaned_matches = [unescape(match) for match in matches]
    
    return cleaned_matches

def save_to_json(data, output_file):
    """
    将数据保存为JSON文件
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # 配置输入和输出文件
    input_html_file = "6.0\crawlers\6.0\debug_monsters.html"  # 替换为您的HTML文件路径
    output_json_file = "combat_encounters.json"
    
    try:
        # 读取HTML文件
        print(f"正在读取文件: {input_html_file}")
        with open(input_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取战斗遭遇信息
        print("正在提取战斗遭遇信息...")
        combat_encounters = extract_combat_encounters(html_content)
        
        # 创建结构化的数据
        structured_data = {
            "combat_encounters": [
                {"title": title} for title in combat_encounters
            ],
            "count": len(combat_encounters),
            "extracted_titles": combat_encounters
        }
        
        # 保存到JSON文件
        save_to_json(structured_data, output_json_file)
        
        print(f"成功提取 {len(combat_encounters)} 个战斗遭遇")
        print(f"结果已保存到: {output_json_file}")
        
        # 显示前几个结果作为预览
        print("\n前5个提取的战斗遭遇标题:")
        for i, title in enumerate(combat_encounters[:5], 1):
            print(f"{i}. {title}")
            
        if len(combat_encounters) > 5:
            print(f"... 还有 {len(combat_encounters) - 5} 个")
            
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_html_file}")
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")

# 更强大的版本，可以处理更复杂的JSON结构
def extract_combat_encounters_advanced(html_content):
    """
    更高级的提取函数，可以处理更复杂的JSON结构
    """
    encounters = []
    
    # 匹配更完整的模式，可能包含在更大的JSON结构中
    pattern = r'"Type":\s*"CombatEncounter"[^}]*"Title":\s*{\s*"Text":\s*"([^"]+)"[^}]*}'
    
    matches = re.findall(pattern, html_content)
    
    # 处理HTML转义字符
    cleaned_matches = [unescape(match) for match in matches]
    
    return cleaned_matches

# 如果需要提取更多字段，可以使用这个版本
def extract_complete_encounter_data(html_content):
    """
    提取完整的遭遇战数据（如果JSON结构中有更多字段）
    """
    # 这个模式会匹配包含CombatEncounter的完整对象
    pattern = r'{\s*"Type":\s*"CombatEncounter"[^}]+}'
    
    matches = re.findall(pattern, html_content)
    
    complete_data = []
    for match in matches:
        try:
            # 尝试解析JSON
            data = json.loads(match)
            complete_data.append(data)
        except json.JSONDecodeError:
            # 如果JSON不完整，尝试手动提取标题
            title_match = re.search(r'"Text":\s*"([^"]+)"', match)
            if title_match:
                complete_data.append({
                    "Type": "CombatEncounter",
                    "Title": {"Text": unescape(title_match.group(1))}
                })
    
    return complete_data

if __name__ == "__main__":
    main()