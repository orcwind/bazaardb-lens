"""
批量抓取怪物详细信息
从 monsters_only_list.json 读取怪物名称列表，逐个访问搜索页面提取数据

功能：
1. 读取 data/Json/monsters_only_list.json
2. 为每个怪物访问 https://bazaardb.gg/search?q={monster_name}&c=monsters
3. 提取：name, name_zh, description_zh, icon, aspect_ratio
4. 下载图标到 data/icon/monster 目录
5. 增量保存到 data/Json/monsters.json
"""

import json
import sys
import time
import re
import ast
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from html import unescape

# 导入必要的函数
sys.path.insert(0, str(Path(__file__).parent))

from selenium_items_skills import (
    parse_card_json_data,
    size_to_aspect_ratio,
    setup_driver,
    extract_all_monsters_or_events_from_search_page
)
from utils_icon import download_icon

def extract_all_monsters_from_html_file(html_file_path):
    """
    从已保存的HTML文件中批量提取所有怪物的完整JSON数据
    返回一个字典：{monster_name: card_json}
    """
    monsters_data = {}
    
    if not html_file_path.exists():
        print(f"  警告: HTML文件不存在: {html_file_path}")
        return monsters_data
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        print(f"  从HTML文件提取怪物数据（文件大小: {len(html)} 字符）...")
        
        # 方法1: 使用与 fetch_items_skills_names.py 完全相同的方法提取名称
        # 先提取所有 _originalTitleText（英文名称）- 转义版本
        escaped_pattern3 = rf'\\"Type\\":\\"CombatEncounter\\"[^}}]*?\\"_originalTitleText\\":\s*\\"([^"]+)\\"'
        matches3_escaped = re.findall(escaped_pattern3, html, re.DOTALL)
        
        # 未转义版本
        pattern3 = r'"Type"\s*:\s*"CombatEncounter"[^}]*?"_originalTitleText"\s*:\s*"([^"]+)"'
        matches3 = re.findall(pattern3, html, re.DOTALL)
        
        all_names = []
        for match in matches3_escaped:
            name = unescape(match).strip().rstrip('\\')
            if name:
                all_names.append(name)
        for match in matches3:
            name = unescape(match).strip()
            if name:
                all_names.append(name)
        
        unique_names = list(set(all_names))
        print(f"  [调试] 找到 {len(unique_names)} 个唯一的怪物名称")
        
        # 对于每个名称，尝试从HTML中找到对应的完整JSON对象
        # 由于HTML中数据可能是转义的，我们需要找到包含这个名称的完整对象
        # 使用更简单的方法：查找包含名称和Type的JSON片段，然后尝试解析
        for name in unique_names:
            if name in monsters_data:
                continue
            
            # 尝试找到包含这个名称的完整对象
            # 搜索模式：包含 Type":"CombatEncounter" 和 _originalTitleText":"{name}" 的完整对象
            # 先尝试未转义版本
            search_pattern = rf'"Type"\s*:\s*"CombatEncounter"[^}}]*?"_originalTitleText"\s*:\s*"{re.escape(name)}"[^}}]*?'
            match_obj = re.search(search_pattern, html, re.DOTALL)
            
            if not match_obj:
                # 尝试转义版本
                search_pattern_escaped = rf'\\"Type\\":\\"CombatEncounter\\"[^}}]*?\\"_originalTitleText\\":\s*\\"{re.escape(name)}\\"[^}}]*?'
                match_obj = re.search(search_pattern_escaped, html, re.DOTALL)
            
            if match_obj:
                # 找到匹配的位置，尝试提取完整的对象
                match_start = match_obj.start()
                # 向前查找对象的开始 {
                obj_start = html.rfind('{', max(0, match_start - 10000), match_start)
                if obj_start == -1:
                    continue
                
                # 向后查找对象的结束 }
                depth = 0
                in_string = False
                escape = False
                obj_end = -1
                
                for i in range(obj_start, min(len(html), obj_start + 50000)):
                    ch = html[i]
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
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                obj_end = i
                                break
                
                if obj_end != -1:
                    json_str = html[obj_start:obj_end + 1]
                    try:
                        card_data = json.loads(json_str)
                        if card_data.get('Type') == 'CombatEncounter' and card_data.get('_originalTitleText') == name:
                            monsters_data[name] = card_data
                    except:
                        pass
        
        # 方法2: 如果方法1提取的数量不够，尝试未转义版本
        if len(monsters_data) < 50:
            pattern = rf'"Type"\s*:\s*"CombatEncounter"[^}}]*?"_originalTitleText"\s*:\s*"([^"]+)"'
            matches = re.findall(pattern, html, re.DOTALL)
            
            for match in matches:
                clean_name = unescape(match).strip()
                if clean_name and clean_name not in monsters_data:
                    # 找到 _originalTitleText 的位置
                    title_pos = html.find(f'"_originalTitleText":"{match}"')
                    if title_pos != -1:
                        obj_start = html.rfind('{', 0, title_pos)
                        if obj_start != -1:
                            depth = 0
                            in_string = False
                            escape = False
                            obj_end = -1
                            
                            for i in range(obj_start, len(html)):
                                ch = html[i]
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
                                    if ch == '{':
                                        depth += 1
                                    elif ch == '}':
                                        depth -= 1
                                        if depth == 0:
                                            obj_end = i
                                            break
                            
                            if obj_end != -1:
                                json_str = html[obj_start:obj_end + 1]
                                try:
                                    card_data = json.loads(json_str)
                                    monsters_data[clean_name] = card_data
                                except:
                                    pass
        
        print(f"  ✓ 从HTML文件提取到 {len(monsters_data)} 个怪物数据")
        return monsters_data
        
    except Exception as e:
        print(f"  ✗ 从HTML文件提取失败: {e}")
        import traceback
        traceback.print_exc()
        return monsters_data

def extract_monster_data_from_html(html, monster_name):
    """
    从HTML中提取单个怪物的完整JSON数据
    先尝试从 initialData.pageCards 提取（与items/skills相同的方法）
    如果失败，再尝试从HTML中直接提取
    """
    try:
        # 方法1: 尝试从 initialData.pageCards 提取（与items/skills相同）
        initial_data_key = 'initialData'
        init_pos = html.find(initial_data_key)
        
        if init_pos == -1:
            print(f"      · 调试: 未找到 initialData 关键字")
        else:
            print(f"      · 调试: 找到 initialData 在位置 {init_pos}")
        
        if init_pos != -1:
            # 从 initialData 位置开始查找 pageCards
            search_start = init_pos
            search_end = min(len(html), init_pos + 50000)
            search_area = html[search_start:search_end]
            
            pagecards_key = 'pageCards'
            key_pos_in_area = search_area.find(pagecards_key)
            
            if key_pos_in_area == -1:
                print(f"      · 调试: 在 initialData 区域内未找到 pageCards")
            else:
                print(f"      · 调试: 找到 pageCards 在位置 {search_start + key_pos_in_area}")
            
            if key_pos_in_area != -1:
                key_pos = search_start + key_pos_in_area
                bracket_start = html.find('[', key_pos)
                if bracket_start == -1:
                    print(f"      · 调试: 未找到数组开始标记 [")
                else:
                    print(f"      · 调试: 找到数组开始标记 [ 在位置 {bracket_start}")
                
                if bracket_start != -1:
                    # 手动匹配括号深度
                    depth = 0
                    in_string = False
                    escape = False
                    bracket_end = -1
                    
                    for i in range(bracket_start, len(html)):
                        ch = html[i]
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
                        full_json_str = html[bracket_start:bracket_end + 1]
                        try:
                            cards_data = json.loads(full_json_str)
                            print(f"      · 调试: 成功解析 pageCards，包含 {len(cards_data)} 个卡片")
                            if isinstance(cards_data, list) and len(cards_data) > 0:
                                # 查找匹配的怪物
                                for idx, card in enumerate(cards_data):
                                    card_type = card.get('Type', '')
                                    print(f"      · 调试: 卡片 {idx}: Type={card_type}")
                                    if card_type == 'CombatEncounter':
                                        original_title = card.get('_originalTitleText', '')
                                        print(f"      · 调试: 找到 CombatEncounter，_originalTitleText={original_title}")
                                        if original_title and original_title.replace('-', ' ').replace('_', ' ').lower() == monster_name.replace('-', ' ').replace('_', ' ').lower():
                                            print(f"      ✓ 从 initialData.pageCards 提取成功")
                                            return card
                                        # 如果名称不完全匹配，但只有一个结果，也返回它
                                        if len(cards_data) == 1:
                                            print(f"      ✓ 从 initialData.pageCards 提取成功（单个结果）")
                                            return card
                        except json.JSONDecodeError:
                            # 尝试处理转义字符
                            try:
                                import ast
                                decoded_str = ast.literal_eval(f'"{full_json_str}"')
                                cards_data = json.loads(decoded_str)
                                if isinstance(cards_data, list) and len(cards_data) > 0:
                                    for card in cards_data:
                                        if card.get('Type') == 'CombatEncounter':
                                            original_title = card.get('_originalTitleText', '')
                                            if original_title and original_title.replace('-', ' ').replace('_', ' ').lower() == monster_name.replace('-', ' ').replace('_', ' ').lower():
                                                print(f"      ✓ 从 initialData.pageCards（转义）提取成功")
                                                return card
                            except:
                                pass
        
        # 方法2: 从HTML中直接搜索（如果initialData不存在）
        # 使用与 fetch_items_skills_names.py 中 extract_names_from_dom_strict 相同的方法
        # 搜索 "Type":"CombatEncounter" 附近的 _originalTitleText，然后提取完整对象
        
        # 先找到所有包含 Type":"CombatEncounter" 和 _originalTitleText 的位置
        # 使用更宽泛的搜索范围（5000字符内）
        pattern = rf'"Type"\s*:\s*"CombatEncounter"[^}}]{{0,5000}}?"_originalTitleText"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        
        print(f"      · 调试: 找到 {len(matches)} 个可能的匹配")
        
        for match in matches:
            clean_match = unescape(match).strip()
            # 检查是否匹配怪物名称（忽略大小写和连字符/空格差异）
            if clean_match.replace('-', ' ').replace('_', ' ').replace(' ', '').lower() == monster_name.replace('-', ' ').replace('_', ' ').replace(' ', '').lower():
                print(f"      · 调试: 找到匹配的名称: {clean_match}")
                # 找到 _originalTitleText 的位置
                title_pos = html.find(f'"_originalTitleText":"{match}"')
                if title_pos != -1:
                    # 向前查找对象的开始 {
                    # 在 _originalTitleText 之前查找最近的 "Type":"CombatEncounter"
                    type_pattern = rf'"Type"\s*:\s*"CombatEncounter"[^}}]{{0,5000}}?"_originalTitleText"\s*:\s*"{re.escape(match)}"'
                    type_match = re.search(type_pattern, html, re.DOTALL)
                    if type_match:
                        match_start = type_match.start()
                        # 向前查找对象的开始 {
                        obj_start = html.rfind('{', max(0, match_start - 10000), match_start)
                        if obj_start != -1:
                            # 向后查找对象的结束 }
                            depth = 0
                            in_string = False
                            escape = False
                            obj_end = -1
                            
                            for i in range(obj_start, min(len(html), obj_start + 50000)):
                                ch = html[i]
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
                                    if ch == '{':
                                        depth += 1
                                    elif ch == '}':
                                        depth -= 1
                                        if depth == 0:
                                            obj_end = i
                                            break
                            
                            if obj_end != -1:
                                json_str = html[obj_start:obj_end + 1]
                                try:
                                    card_data = json.loads(json_str)
                                    if card_data.get('Type') == 'CombatEncounter':
                                        print(f"      ✓ 通过正则表达式提取成功")
                                        return card_data
                                except:
                                    pass
        
        # 如果名称匹配失败，但只有一个CombatEncounter，也返回它
        pattern_single = r'"Type"\s*:\s*"CombatEncounter"'
        all_matches = list(re.finditer(pattern_single, html, re.DOTALL))
        if len(all_matches) == 1:
            print(f"      · 调试: 找到单个CombatEncounter，尝试提取")
            match = all_matches[0]
            match_start = match.start()
            obj_start = html.rfind('{', max(0, match_start - 10000), match_start)
            if obj_start != -1:
                depth = 0
                in_string = False
                escape = False
                obj_end = -1
                
                for i in range(obj_start, min(len(html), obj_start + 50000)):
                    ch = html[i]
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
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                obj_end = i
                                break
                
                if obj_end != -1:
                    json_str = html[obj_start:obj_end + 1]
                    try:
                        card_data = json.loads(json_str)
                        if card_data.get('Type') == 'CombatEncounter':
                            print(f"      ✓ 提取单个CombatEncounter成功")
                            return card_data
                    except:
                        pass
        
        print(f"      ✗ 未找到匹配的 CombatEncounter 数据")
        return None
        
    except Exception as e:
        print(f"      ✗ 提取怪物数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_monsters_list():
    """从 monsters_only_list.json 加载怪物名称列表"""
    monsters_json = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_only_list.json"
    if not monsters_json.exists():
        print(f"错误: 找不到文件 {monsters_json}")
        print("提示: 请先运行 fetch_items_skills_names.py 生成怪物名称列表")
        return []
    
    try:
        with open(monsters_json, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except Exception as e:
        print(f"错误: 读取文件失败: {e}")
        return []

def load_existing_monsters():
    """加载已存在的怪物数据"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters.json"
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_monsters(monsters_data):
    """保存怪物数据到JSON文件"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(monsters_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存 {len(monsters_data)} 个怪物到 {output_file}")

def save_error_log(error_log, output_file):
    """保存错误日志到JSON文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(error_log, f, ensure_ascii=False, indent=2)
    
    total_errors = sum(len(errors) for errors in error_log.values())
    print(f"  ✓ 已保存错误日志到 {output_file} (共 {total_errors} 个错误)")

def process_monster_from_json(card_json, monster_name, existing_monsters_dict, error_log):
    """从已提取的JSON数据中处理怪物（不访问网络）"""
    errors = []
    try:
        # 检查是否已存在
        if monster_name in existing_monsters_dict:
            existing = existing_monsters_dict[monster_name]
            if existing.get('name_zh') and existing.get('description_zh') and existing.get('icon'):
                print(f"  ⊙ {monster_name} (已存在，跳过)")
                return existing, []
        
        # 解析JSON数据
        parsed_data = parse_card_json_data(card_json)
        if not parsed_data:
            error_msg = f"解析卡片数据失败"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_parsing',
                'message': error_msg,
                'monster_name': monster_name
            })
            result = existing_monsters_dict.get(monster_name)
            if result:
                return result, errors
            else:
                return None, errors
        
        # 检查关键字段
        if not parsed_data.get('name_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'name_zh',
                'message': '缺少中文名称',
                'monster_name': monster_name
            })
        
        if not parsed_data.get('description_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'description_zh',
                'message': '缺少中文描述',
                'monster_name': monster_name
            })
        
        # 下载图标
        icon_filename = ""
        icon_url = parsed_data.get('icon_url', '')
        if icon_url:
            icon_filename = download_icon(icon_url, parsed_data.get('name', monster_name), category='monster')
            if not icon_filename:
                error_msg = f"图标下载失败 (URL: {icon_url})"
                print(f"      ⚠ {error_msg}")
                errors.append({
                    'type': 'icon_download',
                    'message': error_msg,
                    'icon_url': icon_url,
                    'monster_name': monster_name
                })
        else:
            error_msg = "缺少图标URL"
            errors.append({
                'type': 'missing_field',
                'field': 'icon_url',
                'message': error_msg,
                'monster_name': monster_name
            })
        
        # 构建怪物数据
        monster_data = {
            "name": parsed_data.get('name', monster_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename,
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
        }
        
        # 智能合并已有数据
        if monster_name in existing_monsters_dict:
            existing = existing_monsters_dict[monster_name]
            if existing.get('name_zh') and not monster_data.get('name_zh'):
                monster_data['name_zh'] = existing['name_zh']
            if existing.get('description_zh') and not monster_data.get('description_zh'):
                monster_data['description_zh'] = existing['description_zh']
            if existing.get('icon') and not monster_data.get('icon'):
                monster_data['icon'] = existing['icon']
        
        if errors:
            print(f"      ⚠ 完成（有警告）: {monster_data.get('name_zh', monster_name)}")
        else:
            print(f"      ✓ 完成: {monster_data.get('name_zh', monster_name)}")
        
        return monster_data, errors
        
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        print(f"      ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        errors.append({
            'type': 'exception',
            'message': error_msg,
            'monster_name': monster_name,
            'traceback': traceback.format_exc()
        })
        result = existing_monsters_dict.get(monster_name)
        return result, errors

def process_monster(driver, monster_name, existing_monsters_dict, error_log):
    """处理单个怪物
    
    Args:
        driver: Selenium WebDriver
        monster_name: 怪物名称（英文，用于URL）
        existing_monsters_dict: 已有怪物数据字典（key为name）
        error_log: 错误日志字典，用于记录失败信息
    
    Returns:
        (monster_data, errors): 怪物数据字典和错误信息列表
    """
    errors = []
    try:
        # 检查是否已存在
        if monster_name in existing_monsters_dict:
            existing = existing_monsters_dict[monster_name]
            # 如果已有完整数据，跳过
            if existing.get('name_zh') and existing.get('description_zh') and existing.get('icon'):
                print(f"  ⊙ {monster_name} (已存在，跳过)")
                return existing, []
        
        print(f"  → 处理: {monster_name}")
        
        # 步骤1: 访问搜索页面并提取JSON数据（带重试机制）
        search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
        html = None
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                driver.get(search_url)
                time.sleep(5)  # 增加等待时间
                html = driver.page_source
                break
            except WebDriverException as e:
                if "ERR_CONNECTION" in str(e) or "ERR_NETWORK" in str(e):
                    if retry < max_retries - 1:
                        wait_time = (retry + 1) * 5
                        print(f"      ⚠ 网络错误，{wait_time}秒后重试 ({retry + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"网络连接失败: {str(e)}"
                        print(f"      ✗ {error_msg}")
                        errors.append({
                            'type': 'network_error',
                            'message': error_msg,
                            'monster_name': monster_name
                        })
                        return existing_monsters_dict.get(monster_name), errors
                else:
                    raise
        
        if not html:
            error_msg = f"无法获取页面内容"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_extraction',
                'message': error_msg,
                'monster_name': monster_name
            })
            return existing_monsters_dict.get(monster_name), errors
        
        card_json = extract_monster_data_from_html(html, monster_name)
        if not card_json:
            error_msg = f"未找到卡片数据"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_extraction',
                'message': error_msg,
                'monster_name': monster_name
            })
            result = existing_monsters_dict.get(monster_name)
            if result:
                return result, errors
            else:
                return None, errors
        
        # 步骤2: 解析JSON数据
        parsed_data = parse_card_json_data(card_json)
        if not parsed_data:
            error_msg = f"解析卡片数据失败"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_parsing',
                'message': error_msg,
                'monster_name': monster_name
            })
            result = existing_monsters_dict.get(monster_name)
            if result:
                return result, errors
            else:
                return None, errors
        
        # 检查关键字段是否缺失
        if not parsed_data.get('name_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'name_zh',
                'message': '缺少中文名称',
                'monster_name': monster_name
            })
        
        if not parsed_data.get('description_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'description_zh',
                'message': '缺少中文描述',
                'monster_name': monster_name
            })
        
        # 步骤3: 下载图标
        icon_filename = ""
        icon_url = parsed_data.get('icon_url', '')
        if icon_url:
            icon_filename = download_icon(icon_url, parsed_data.get('name', monster_name), category='monster')
            if not icon_filename:
                error_msg = f"图标下载失败 (URL: {icon_url})"
                print(f"      ⚠ {error_msg}")
                errors.append({
                    'type': 'icon_download',
                    'message': error_msg,
                    'icon_url': icon_url,
                    'monster_name': monster_name
                })
        else:
            error_msg = "缺少图标URL"
            errors.append({
                'type': 'missing_field',
                'field': 'icon_url',
                'message': error_msg,
                'monster_name': monster_name
            })
        
        # 步骤4: 构建怪物数据
        monster_data = {
            "name": parsed_data.get('name', monster_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename,
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
        }
        
        # 步骤5: 如果已有数据，保留已有字段（智能合并）
        if monster_name in existing_monsters_dict:
            existing = existing_monsters_dict[monster_name]
            # 保留已有但新数据中没有的字段
            if existing.get('name_zh') and not monster_data.get('name_zh'):
                monster_data['name_zh'] = existing['name_zh']
            if existing.get('description_zh') and not monster_data.get('description_zh'):
                monster_data['description_zh'] = existing['description_zh']
            if existing.get('icon') and not monster_data.get('icon'):
                monster_data['icon'] = existing['icon']
        
        if errors:
            print(f"      ⚠ 完成（有警告）: {monster_data.get('name_zh', monster_name)}")
        else:
            print(f"      ✓ 完成: {monster_data.get('name_zh', monster_name)}")
        
        return monster_data, errors
        
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        print(f"      ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        errors.append({
            'type': 'exception',
            'message': error_msg,
            'monster_name': monster_name,
            'traceback': traceback.format_exc()
        })
        result = existing_monsters_dict.get(monster_name)
        return result, errors

def main():
    """主函数"""
    # 检查是否测试模式
    TEST_MODE = '--test' in sys.argv or '-t' in sys.argv
    TEST_LIMIT = 10 if TEST_MODE else None
    
    print("=" * 80)
    if TEST_MODE:
        print("批量抓取怪物详细信息 - 测试模式")
        print(f"只处理前 {TEST_LIMIT} 个怪物")
    else:
        print("批量抓取怪物详细信息 - 完整模式")
    print("=" * 80)
    
    # 加载怪物列表
    print("\n[1/3] 加载怪物名称列表...")
    monster_names = load_monsters_list()
    if not monster_names:
        return
    
    if TEST_MODE:
        monster_names = monster_names[:TEST_LIMIT]
    
    print(f"  找到 {len(monster_names)} 个怪物")
    
    # 加载已有数据
    print("\n[2/3] 加载已有怪物数据...")
    existing_monsters = load_existing_monsters()
    existing_monsters_dict = {monster.get('name', ''): monster for monster in existing_monsters if monster.get('name')}
    print(f"  已有 {len(existing_monsters_dict)} 个怪物数据")
    
    # 检查是否使用HTML文件模式（避免网络问题）
    USE_HTML_FILE = '--from-html' in sys.argv or '--html' in sys.argv
    html_file_path = Path(__file__).parent.parent.parent / "data" / "html" / "monsters.html"
    
    if USE_HTML_FILE and html_file_path.exists():
        print("\n[3/3] 从HTML文件批量提取数据（避免网络问题）...")
        # 从HTML文件批量提取所有怪物数据
        html_monsters_dict = extract_all_monsters_from_html_file(html_file_path)
        
        monsters_data = []
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        error_log = {}
        
        for idx, monster_name in enumerate(monster_names, 1):
            print(f"\n[{idx}/{len(monster_names)}] {monster_name}")
            
            # 从HTML文件中查找对应的数据
            card_json = None
            for name, data in html_monsters_dict.items():
                if name.replace('-', ' ').replace('_', ' ').lower() == monster_name.replace('-', ' ').replace('_', ' ').lower():
                    card_json = data
                    break
            
            if not card_json:
                print(f"  ✗ 在HTML文件中未找到数据")
                failed_count += 1
                error_log[monster_name] = [{
                    'type': 'data_extraction',
                    'message': '在HTML文件中未找到数据',
                    'monster_name': monster_name
                }]
                continue
            
            # 解析和处理数据
            try:
                result, errors = process_monster_from_json(card_json, monster_name, existing_monsters_dict, error_log)
                if errors:
                    error_log[monster_name] = errors
                if result:
                    monsters_data.append(result)
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"  ✗ 处理出错: {e}")
                failed_count += 1
                error_log[monster_name] = [{
                    'type': 'exception',
                    'message': f"处理时发生异常: {str(e)}",
                    'monster_name': monster_name
                }]
            
            # 每10个保存一次
            if idx % 10 == 0:
                save_monsters(monsters_data)
                error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_errors.json"
                save_error_log(error_log, error_log_file)
                print(f"\n  [进度] 已处理: {processed_count}, 跳过: {skipped_count}, 失败: {failed_count}")
        
        # 最终保存
        save_monsters(monsters_data)
        error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_errors.json"
        save_error_log(error_log, error_log_file)
        
        # 统计错误
        total_errors = sum(len(errors) for errors in error_log.values())
        icon_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') == 'icon_download')
        data_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') in ['data_extraction', 'data_parsing'])
        missing_field_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') == 'missing_field')
        
        print("\n" + "=" * 80)
        print("抓取完成！")
        print(f"  成功处理: {processed_count} 个")
        print(f"  跳过（已存在）: {skipped_count} 个")
        print(f"  失败: {failed_count} 个")
        print(f"  总计: {len(monsters_data)} 个怪物")
        print("\n错误统计:")
        print(f"  总错误数: {total_errors}")
        print(f"  图标下载失败: {icon_errors} 个")
        print(f"  数据提取/解析失败: {data_errors} 个")
        print(f"  缺少字段: {missing_field_errors} 个")
        if error_log:
            print(f"  详细错误日志已保存到: {error_log_file}")
        print("=" * 80)
    else:
        # 使用浏览器模式 - 从总列表页面批量提取
        print("\n[3/3] 启动浏览器并从总列表页面批量提取...")
        driver = setup_driver()
        
        try:
            # 从总列表页面批量提取所有怪物数据
            print("\n从总列表页面提取所有怪物数据...")
            all_cards_json = extract_all_monsters_or_events_from_search_page(driver, 'monsters')
            
            if not all_cards_json:
                print("  ✗ 未能从总列表页面提取任何怪物数据")
                return
            
            print(f"  成功提取 {len(all_cards_json)} 个怪物的JSON数据")
            
            # 构建名称到JSON的映射
            cards_dict = {}
            for card_json in all_cards_json:
                original_title = card_json.get('_originalTitleText', '')
                if original_title:
                    cards_dict[original_title] = card_json
            
            monsters_data = []
            processed_count = 0
            skipped_count = 0
            failed_count = 0
            error_log = {}  # 记录所有错误 {monster_name: [errors]}
            
            for idx, monster_name in enumerate(monster_names, 1):
                print(f"\n[{idx}/{len(monster_names)}] {monster_name}")
                
                try:
                    # 从批量提取的数据中查找对应的JSON
                    card_json = None
                    for name, json_data in cards_dict.items():
                        if name.replace('-', ' ').replace('_', ' ').lower() == monster_name.replace('-', ' ').replace('_', ' ').lower():
                            card_json = json_data
                            break
                    
                    if not card_json:
                        print(f"  ✗ 在批量数据中未找到")
                        failed_count += 1
                        error_log[monster_name] = [{
                            'type': 'data_extraction',
                            'message': '在批量数据中未找到',
                            'monster_name': monster_name
                        }]
                        continue
                    
                    # 使用已有的process_monster_from_json函数处理
                    result, errors = process_monster_from_json(card_json, monster_name, existing_monsters_dict, error_log)
                    
                    # 记录错误
                    if errors:
                        error_log[monster_name] = errors
                    
                    if result:
                        monsters_data.append(result)
                        if monster_name in existing_monsters_dict and result == existing_monsters_dict[monster_name]:
                            skipped_count += 1
                        else:
                            processed_count += 1
                    else:
                        failed_count += 1
                    
                    # 每10个保存一次（增量保存）
                    if idx % 10 == 0:
                        save_monsters(monsters_data)
                        # 保存错误日志
                        error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_errors.json"
                        save_error_log(error_log, error_log_file)
                        print(f"\n  [进度] 已处理: {processed_count}, 跳过: {skipped_count}, 失败: {failed_count}")
                    
                except KeyboardInterrupt:
                    print("\n\n用户中断，保存当前进度...")
                    save_monsters(monsters_data)
                    error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_errors.json"
                    save_error_log(error_log, error_log_file)
                    break
                except Exception as e:
                    print(f"  ✗ 处理 {monster_name} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
                    error_log[monster_name] = [{
                        'type': 'exception',
                        'message': f"处理时发生异常: {str(e)}",
                        'monster_name': monster_name,
                        'traceback': traceback.format_exc()
                    }]
                    continue
            
            # 最终保存
            save_monsters(monsters_data)
            error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_errors.json"
            save_error_log(error_log, error_log_file)
            
            # 统计错误
            total_errors = sum(len(errors) for errors in error_log.values())
            icon_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') == 'icon_download')
            data_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') in ['data_extraction', 'data_parsing'])
            missing_field_errors = sum(1 for errors in error_log.values() for e in errors if e.get('type') == 'missing_field')
            
            print("\n" + "=" * 80)
            print("抓取完成！")
            print(f"  成功处理: {processed_count} 个")
            print(f"  跳过（已存在）: {skipped_count} 个")
            print(f"  失败: {failed_count} 个")
            print(f"  总计: {len(monsters_data)} 个怪物")
            print("\n错误统计:")
            print(f"  总错误数: {total_errors}")
            print(f"  图标下载失败: {icon_errors} 个")
            print(f"  数据提取/解析失败: {data_errors} 个")
            print(f"  缺少字段: {missing_field_errors} 个")
            if error_log:
                print(f"  详细错误日志已保存到: {error_log_file}")
            print("=" * 80)
            
        finally:
            driver.quit()

if __name__ == "__main__":
    main()

