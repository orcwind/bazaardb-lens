import re
import json
from html import unescape

def extract_event_encounters(html_content):
    """
    从HTML内容中提取事件遭遇信息
    """
    # 处理转义的JSON数据 - 先搜索转义版本
    escaped_pattern = r'\\"Type\\":\\"EventEncounter\\",\\"Title\\":\s*{\s*\\"Text\\":\s*\\"([^"]+)\\"'
    matches = re.findall(escaped_pattern, html_content)
    
    # 如果没找到转义版本，尝试普通版本
    if not matches:
        pattern = r'"Type":"EventEncounter","Title":\s*{\s*"Text":\s*"([^"]+)"'
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
    input_html_file = "debug_events.html"  # 替换为您的HTML文件路径
    output_json_file = "unique_events.json"
    
    try:
        # 读取HTML文件
        print(f"正在读取文件: {input_html_file}")
        with open(input_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取事件遭遇信息
        print("正在提取事件遭遇信息...")
        event_encounters = extract_event_encounters(html_content)
        
        # 去重并排序
        unique_events = sorted(list(set(event_encounters)))
        
        # 保存到JSON文件（只保存事件名称列表）
        with open(output_json_file, 'w', encoding='utf-8') as f:
            for event in unique_events:
                f.write(f'"{event}"\n')
        
        print(f"成功提取 {len(event_encounters)} 个事件遭遇，去重后 {len(unique_events)} 个事件")
        print(f"结果已保存到: {output_json_file}")
        
        # 显示前几个结果作为预览
        print("\n前10个事件名称:")
        for i, title in enumerate(unique_events[:10], 1):
            print(f"{i}. {title}")
            
        if len(unique_events) > 10:
            print(f"... 还有 {len(unique_events) - 10} 个")
            
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_html_file}")
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")

def extract_event_encounters_old(html_file_path):
    """
    从HTML文件中提取事件遭遇名称
    """
    print("=" * 80)
    print("开始提取事件名称...")
    print("=" * 80)
    
    # 步骤1: 读取HTML文件
    print(f"\n[步骤1] 读取HTML文件: {html_file_path}")
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"  文件大小: {len(content)} 字符")
    
    # 步骤2: 查找所有EventEncounter出现的位置
    print("\n[步骤2] 查找所有 EventEncounter...")
    all_matches = list(re.finditer(r'EventEncounter', content))
    print(f"  总共找到 {len(all_matches)} 个 EventEncounter")
    
    # 步骤3: 提取每个EventEncounter后面的80个字符
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
    
    # 步骤4: 从片段中提取事件名称
    print("\n[步骤4] 从片段中提取事件名称...")
    event_names = []
    pattern = r'\\"Title\\":\{\\"Text\\":\\"([^"\\]+)\\"'
    
    for item in snippets:
        snippet = item['snippet']
        match = re.search(pattern, snippet)
        if match:
            name = unescape(match.group(1))
            event_names.append({
                "index": item['index'],
                "name": name
            })
    
    print(f"  成功提取 {len(event_names)} 个事件名称")
    
    # 步骤5: 去重
    print("\n[步骤5] 去除重复...")
    unique_names = []
    seen = set()
    for item in event_names:
        if item['name'] not in seen:
            seen.add(item['name'])
            unique_names.append(item['name'])
    
    print(f"  去重后剩余 {len(unique_names)} 个唯一事件名称")
    
    # 步骤6: 保存结果
    print("\n[步骤6] 保存结果...")
    
    # 保存去重后的事件列表（每行一个名称，不带中括号）
    with open('unique_events.json', 'w', encoding='utf-8') as f:
        for name in unique_names:
            f.write(f'"{name}"\n')
    print("  ✓ 已保存: unique_events.json")
    
    # 显示结果预览
    print("\n" + "=" * 80)
    print(f"提取完成！共 {len(unique_names)} 个唯一事件")
    print("=" * 80)
    print("\n前20个事件名称：")
    for i, name in enumerate(unique_names[:20], 1):
        print(f"  {i:2d}. {name}")
    
    if len(unique_names) > 20:
        print(f"  ... 还有 {len(unique_names) - 20} 个事件")
    
    print("\n" + "=" * 80)
    
    return unique_names


if __name__ == "__main__":
    # 设置HTML文件路径
    html_file = 'debug_events.html'
    
    try:
        # 执行提取
        events = extract_event_encounters(html_file)
        
        print(f"\n✓ 成功提取 {len(events)} 个唯一事件名称")
        print(f"✓ 结果已保存到 unique_events.json")
        
    except FileNotFoundError:
        print(f"\n✗ 错误: 找不到文件 {html_file}")
        print("  请确认文件路径是否正确")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
