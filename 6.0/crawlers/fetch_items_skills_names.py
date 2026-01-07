"""
从搜索页面HTML中提取物品、技能和怪物名称
不仅从pageCards JSON中提取，还从DOM元素中提取所有名称
"""

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import unquote

def extract_card_names_from_html(html_content, category='items'):
    """
    从HTML内容中提取卡片名称（从pageCards JSON中提取，类似fetch_monster_name.py）
    """
    names = []
    search_pos = 0
    
    # 确定要提取的类型
    item_type = 'Item' if category == 'items' else 'Skill'
    
    # 先统计有多少个 initialData 和 pageCards
    initialdata_count = html_content.count('initialData')
    pagecards_count = html_content.count('pageCards')
    print(f"  [调试] HTML中 found {initialdata_count} 个 'initialData', {pagecards_count} 个 'pageCards'")
    
    initialdata_found = 0
    pagecards_found = 0
    
    while True:
        # 查找 initialData
        init_pos = html_content.find('initialData', search_pos)
        if init_pos == -1:
            break
        
        initialdata_found += 1
        print(f"  [调试] 找到第 {initialdata_found} 个 initialData 在位置 {init_pos}")
        
        # 在 initialData 区域内查找 pageCards（移除范围限制，搜索整个文件）
        pagecards_key = 'pageCards'
        key_pos = html_content.find(pagecards_key, init_pos)
        
        if key_pos != -1:
            pagecards_found += 1
            print(f"  [调试] 找到第 {pagecards_found} 个 pageCards 在位置 {key_pos} (距离 initialData {key_pos - init_pos} 字符)")
            # 找到 pageCards，提取数组
            bracket_start = html_content.find('[', key_pos)
            
            if bracket_start != -1:
                # 手动匹配完整的JSON数组
                depth = 0
                in_string = False
                escape = False
                bracket_end = -1
                
                for i in range(bracket_start, len(html_content)):
                    ch = html_content[i]
                    
                    if escape:
                        escape = False
                        continue
                    
                    if ch == '\\':
                        escape = True
                        continue
                    
                    if ch == '"':
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if ch == '[':
                            depth += 1
                        elif ch == ']':
                            depth -= 1
                            if depth == 0:
                                bracket_end = i
                                break
                
                if bracket_end != -1:
                    # 提取并解析JSON数组
                    json_str = html_content[bracket_start:bracket_end + 1]
                    cards_data = None
                    json_error = None
                    
                    try:
                        # 尝试直接解析
                        cards_data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        json_error = str(e)
                        # 如果失败，尝试解码转义
                        try:
                            import ast
                            decoded_str = ast.literal_eval(f'"{json_str}"')
                            cards_data = json.loads(decoded_str)
                            json_error = None
                        except Exception as e2:
                            json_error = f"直接解析失败: {e}, 转义解析也失败: {e2}"
                    
                    if cards_data and isinstance(cards_data, list):
                        print(f"  [调试] 成功解析JSON数组，包含 {len(cards_data)} 个卡片")
                        # 统计所有类型
                        type_counts = {}
                        for card in cards_data:
                            if isinstance(card, dict):
                                card_type = card.get('Type', '')
                                type_counts[card_type] = type_counts.get(card_type, 0) + 1
                        print(f"  [调试] 卡片类型统计: {type_counts}")
                        
                        # 提取符合类型的卡片名称（优先使用英文名）
                        found_count = 0
                        for card in cards_data:
                            if isinstance(card, dict):
                                card_type = card.get('Type', '')
                                if card_type == item_type:
                                    # 优先使用 _originalTitleText（英文名）
                                    name = card.get('_originalTitleText', '')
                                    if not name:
                                        # 如果没有，尝试从 Title.Text 提取
                                        title = card.get('Title', {})
                                        if isinstance(title, dict):
                                            name = title.get('Text', '')
                                    
                                    if name and name not in names:
                                        names.append(name)
                                        found_count += 1
                        print(f"  [调试] 从该数组中找到 {found_count} 个{item_type}类型卡片")
                    else:
                        if json_error:
                            print(f"  [警告] JSON解析失败: {json_error}")
                        else:
                            print(f"  [警告] 未找到有效的卡片数组数据")
        
        else:
            print(f"  [调试] 该 initialData 后未找到 pageCards")
        
        # 继续搜索下一个 initialData
        search_pos = init_pos + 1
    
    print(f"  [调试] 总共找到 {initialdata_found} 个 initialData, {pagecards_found} 个 pageCards")
    print(f"  [调试] 从pageCards JSON中提取到 {len(names)} 个名称")
    
    # 如果从JSON中提取的数量很少，尝试从DOM元素中提取
    if len(names) < 50:
        print(f"  [调试] JSON中数量较少，尝试从DOM元素中提取...")
        dom_names = extract_names_from_dom(html_content, category)
        print(f"  [调试] 从DOM元素中提取到 {len(dom_names)} 个名称")
        names.extend(dom_names)
    
    # 去重并过滤掉带反斜杠的重复项
    unique_names = []
    seen = set()
    for name in names:
        # 去掉末尾的反斜杠
        clean_name = name.rstrip('\\')
        if clean_name and clean_name not in seen:
            seen.add(clean_name)
            unique_names.append(clean_name)
    
    print(f"  找到 {len(names)} 个{category}，去重后 {len(unique_names)} 个")
    
    return sorted(unique_names)

def extract_names_from_dom(html_content, category='items'):
    """
    从HTML中提取所有物品/技能/怪物名称
    直接搜索所有 _originalTitleText 字段，不管它在JSON的哪个位置
    优先提取英文名称，过滤掉URL编码的中文
    """
    names = []
    
    # 确定要匹配的类型
    if category == 'items':
        type_pattern = '"Item"'
    elif category == 'skills':
        type_pattern = '"Skill"'
    elif category == 'monsters':
        type_pattern = '"CombatEncounter"'
    else:
        type_pattern = None
    """
    从HTML中提取所有物品/技能名称
    直接搜索所有 _originalTitleText 字段，不管它在JSON的哪个位置
    优先提取英文名称，过滤掉URL编码的中文
    """
    names = []
    
    # 确定要匹配的类型
    type_pattern = '"Item"' if category == 'items' else '"Skill"'
    
    def clean_name(name):
        """清理名称：URL解码、HTML解码、过滤无效名称"""
        if not name:
            return None
        
        # 先尝试URL解码（处理 %E4%B8%80 这种格式）
        try:
            decoded = unquote(name)
            if decoded != name and not decoded.startswith('%'):  # 如果解码成功且不是URL编码
                name = decoded
        except:
            pass
        
        # HTML解码
        name = unescape(name)
        
        # 过滤条件
        if len(name) < 2 or len(name) > 100:
            return None
        
        # 过滤掉URL编码的字符串（仍然包含%的）
        if '%' in name and len([c for c in name if c == '%']) > 2:
            return None
        
        # 过滤掉明显不是名称的字符串
        skip_keywords = ['http', 'www', 'script', 'function', 'undefined', 'null', 'true', 'false']
        if any(skip in name.lower() for skip in skip_keywords):
            return None
        
        # 过滤掉纯数字或特殊字符
        if name.replace(' ', '').replace('-', '').replace("'", '').isdigit():
            return None
        
        return name
    
    # 方法1: 查找所有 "_originalTitleText":"..." 模式（未转义的）
    pattern1 = r'"_originalTitleText"\s*:\s*"([^"]+)"'
    matches1 = re.findall(pattern1, html_content)
    for match in matches1:
        name = clean_name(match)
        if name and name not in names:
            names.append(name)
    
    # 方法2: 查找转义的版本 \"_originalTitleText\":\"...\"
    pattern2 = r'\\"_originalTitleText\\"\s*:\\s*\\"([^"]+)\\"'
    matches2 = re.findall(pattern2, html_content)
    for match in matches2:
        # 处理转义字符
        name = match.replace('\\"', '"').replace('\\\\', '\\')
        name = clean_name(name)
        if name and name not in names:
            names.append(name)
    
    # 方法3: 查找 Type":"Item" 或 Type":"Skill" 等附近的 _originalTitleText
    # 使用更宽松的模式，允许中间有其他字段
    if category == 'items':
        pattern3 = r'"Type"\s*:\s*"Item"[^}]{0,5000}?"_originalTitleText"\s*:\s*"([^"]+)"'
    elif category == 'skills':
        pattern3 = r'"Type"\s*:\s*"Skill"[^}]{0,5000}?"_originalTitleText"\s*:\s*"([^"]+)"'
    elif category == 'monsters':
        pattern3 = r'"Type"\s*:\s*"CombatEncounter"[^}]{0,5000}?"_originalTitleText"\s*:\s*"([^"]+)"'
    else:
        pattern3 = None
    
    if pattern3:
        matches3 = re.findall(pattern3, html_content, re.DOTALL)
        for match in matches3:
            name = clean_name(match)
            if name and name not in names:
                names.append(name)
    
    # 方法4: 从href链接中提取（/card/.../ItemName格式），但只提取英文名称
    pattern4 = r'/card/[^/]+/([^/"]+)'
    matches4 = re.findall(pattern4, html_content)
    for match in matches4:
        name = clean_name(match)
        # 只保留看起来像英文名称的（不包含中文字符或URL编码）
        if name and name not in names:
            # 检查是否包含中文字符或大量URL编码
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in name)
            has_url_encoded = '%' in name and len([c for c in name if c == '%']) > 1
            
            # 优先保留英文名称（不包含中文且不包含URL编码）
            if not has_chinese and not has_url_encoded:
                names.append(name)
    
    return names


def extract_card_names_from_html_monsters(html_content):
    """从HTML中提取怪物名称（CombatEncounter类型）- 使用类似fetch_monster_name.py的方法"""
    names = []
    
    # 方法1: 搜索转义的JSON数据（优先）
    escaped_pattern = r'\\"Type\\":\\"CombatEncounter\\"[^}]*?\\"Title\\":\s*\{\s*\\"Text\\":\s*\\"([^"]+)\\"'
    matches1 = re.findall(escaped_pattern, html_content, re.DOTALL)
    for match in matches1:
        name = unescape(match)
        if name and name not in names:
            names.append(name)
    
    # 方法2: 搜索普通版本（未转义）
    if len(names) < 50:
        pattern = r'"Type"\s*:\s*"CombatEncounter"[^}]*?"Title"\s*:\s*\{\s*"Text"\s*:\s*"([^"]+)"'
        matches2 = re.findall(pattern, html_content, re.DOTALL)
        for match in matches2:
            name = unescape(match)
            if name and name not in names:
                names.append(name)
    
    # 方法3: 搜索 _originalTitleText（英文名称）
    pattern3 = r'"Type"\s*:\s*"CombatEncounter"[^}]*?"_originalTitleText"\s*:\s*"([^"]+)"'
    matches3 = re.findall(pattern3, html_content, re.DOTALL)
    for match in matches3:
        name = unescape(match)
        if name and name not in names:
            names.append(name)
    
    print(f"  [调试] 从HTML中提取到 {len(names)} 个怪物名称")
    
    # 去重并过滤掉带反斜杠的重复项
    unique_names = []
    seen = set()
    for name in names:
        # 去掉末尾的反斜杠
        clean_name = name.rstrip('\\')
        if clean_name and clean_name not in seen:
            seen.add(clean_name)
            unique_names.append(clean_name)
    
    return sorted(unique_names)


def extract_names_from_dom_strict(html_content, card_type):
    """
    严格从HTML中提取指定类型的名称
    只提取 Type":"CardType" 附近的 _originalTitleText
    """
    names = []
    
    def clean_name(name):
        """清理名称"""
        if not name:
            return None
        try:
            decoded = unquote(name)
            if decoded != name and not decoded.startswith('%'):
                name = decoded
        except:
            pass
        name = unescape(name)
        if len(name) < 2 or len(name) > 100:
            return None
        if '%' in name and len([c for c in name if c == '%']) > 2:
            return None
        skip_keywords = ['http', 'www', 'script', 'function', 'undefined', 'null', 'true', 'false']
        if any(skip in name.lower() for skip in skip_keywords):
            return None
        if name.replace(' ', '').replace('-', '').replace("'", '').isdigit():
            return None
        return name
    
    # 只查找指定类型附近的 _originalTitleText
    pattern = rf'"Type"\s*:\s*"{re.escape(card_type)}"[^}}]{{0,5000}}?"_originalTitleText"\s*:\s*"([^"]+)"'
    matches = re.findall(pattern, html_content, re.DOTALL)
    for match in matches:
        name = clean_name(match)
        if name and name not in names:
            names.append(name)
    
    return names

def main():
    """主函数"""
    print("=" * 80)
    print("从HTML提取物品、技能和怪物名称")
    print("=" * 80)
    
    current_script_dir = Path(__file__).parent
    html_dir = current_script_dir.parent.parent / "data" / "html"
    json_dir = current_script_dir.parent.parent / "data" / "Json"
    
    # 确保JSON目录存在
    json_dir.mkdir(parents=True, exist_ok=True)
    
    # 物品
    items_html_file = html_dir / "items.html"
    items_output_json = json_dir / "items_only_list.json"
    
    if items_html_file.exists():
        print(f"\n[1/3] 提取物品名称从: {items_html_file}")
        with open(items_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        item_names = extract_card_names_from_html(html_content, 'items')
        
        with open(items_output_json, 'w', encoding='utf-8') as f:
            for name in item_names:
                f.write(f'"{name}"\n')
        
        print(f"  ✓ 提取到 {len(item_names)} 个物品名称。")
        print(f"  ✓ 已保存到: {items_output_json}")
        
        print(f"\n前10个物品名称:")
        for i, name in enumerate(item_names[:10], 1):
            print(f"  {i}. {name}")
    else:
        print(f"  警告: {items_html_file} 不存在，跳过物品名称提取。")

    # 技能
    skills_html_file = html_dir / "skills.html"
    skills_output_json = json_dir / "skills_only_list.json"

    if skills_html_file.exists():
        print(f"\n[2/3] 提取技能名称从: {skills_html_file}")
        with open(skills_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        skill_names = extract_card_names_from_html(html_content, 'skills')
        
        with open(skills_output_json, 'w', encoding='utf-8') as f:
            for name in skill_names:
                f.write(f'"{name}"\n')
        
        print(f"  ✓ 提取到 {len(skill_names)} 个技能名称。")
        print(f"  ✓ 已保存到: {skills_output_json}")
        
        print(f"\n前10个技能名称:")
        for i, name in enumerate(skill_names[:10], 1):
            print(f"  {i}. {name}")
    else:
        print(f"  警告: {skills_html_file} 不存在，跳过技能名称提取。")

    # 怪物
    monsters_html_file = html_dir / "monsters.html"
    monsters_output_json = json_dir / "monsters_only_list.json"

    if monsters_html_file.exists():
        print(f"\n[3/3] 提取怪物名称从: {monsters_html_file}")
        with open(monsters_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        monster_names = extract_card_names_from_html_monsters(html_content)
        
        with open(monsters_output_json, 'w', encoding='utf-8') as f:
            for name in monster_names:
                f.write(f'"{name}"\n')
        
        print(f"  ✓ 提取到 {len(monster_names)} 个怪物名称。")
        print(f"  ✓ 已保存到: {monsters_output_json}")
        
        print(f"\n前10个怪物名称:")
        for i, name in enumerate(monster_names[:10], 1):
            print(f"  {i}. {name}")
    else:
        print(f"  警告: {monsters_html_file} 不存在，跳过怪物名称提取。")

    print("\n" + "=" * 80)
    print("所有名称提取完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
