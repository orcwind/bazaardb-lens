"""
批量抓取事件详细信息
从 events_only_list.json 读取事件名称列表，逐个访问搜索页面提取数据

功能：
1. 读取 data/Json/events_only_list.json
2. 为每个事件访问 https://bazaardb.gg/search?q={event_name}&c=events
3. 提取：name, name_zh, description_zh, icon, aspect_ratio
4. 下载图标到 data/icon/event 目录
5. 增量保存到 data/Json/events.json
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
    setup_driver
)
from utils_icon import download_icon

def extract_event_data_from_html(html, event_name):
    """
    从HTML中提取事件的完整JSON数据（使用正则表达式）
    事件数据不在 initialData.pageCards 中，而是直接嵌入在HTML中
    """
    try:
        # 搜索包含 _originalTitleText 的完整JSON对象
        # 先尝试转义版本
        escaped_pattern = rf'\\"Type\\":\\"EventEncounter\\"[^}}]*?\\"_originalTitleText\\":\s*\\"([^"]+)\\"'
        matches = re.findall(escaped_pattern, html, re.DOTALL)
        
        for match in matches:
            clean_match = unescape(match).strip()
            # 检查是否匹配事件名称（忽略大小写和连字符/空格差异）
            if clean_match.replace('-', ' ').replace('_', ' ').lower() == event_name.replace('-', ' ').replace('_', ' ').lower():
                # 找到匹配，提取完整的JSON对象
                full_pattern = rf'\\"Type\\":\\"EventEncounter\\"[^}}]*?\\"_originalTitleText\\":\s*\\"{re.escape(match)}\\"[^}}]*?\}}'
                full_match = re.search(full_pattern, html, re.DOTALL)
                if full_match:
                    json_str = full_match.group(0)
                    try:
                        # 解码转义字符
                        decoded = ast.literal_eval(f'"{json_str}"')
                        card_data = json.loads(decoded)
                        print(f"      ✓ 通过转义JSON提取成功")
                        return card_data
                    except:
                        pass
        
        # 尝试未转义的版本
        pattern = rf'"Type"\s*:\s*"EventEncounter"[^}}]*?"_originalTitleText"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches:
            clean_match = unescape(match).strip()
            if clean_match.replace('-', ' ').replace('_', ' ').lower() == event_name.replace('-', ' ').replace('_', ' ').lower():
                # 提取完整的对象（从 { 到 }）
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
                                print(f"      ✓ 通过正则表达式提取成功")
                                return card_data
                            except:
                                pass
        
        # 如果都失败，尝试提取第一个 EventEncounter 对象
        pattern_first = r'"Type"\s*:\s*"EventEncounter"[^}]*?\{[^}]*?\}'
        match_first = re.search(pattern_first, html, re.DOTALL)
        if match_first:
            obj_start = html.rfind('{', 0, match_first.start())
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
                        print(f"      ✓ 提取第一个EventEncounter对象成功")
                        return card_data
                    except:
                        pass
        
        print(f"      ✗ 未找到匹配的 EventEncounter 数据")
        return None
        
    except Exception as e:
        print(f"      ✗ 提取事件数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_events_list():
    """从 events_only_list.json 加载事件名称列表"""
    events_json = Path(__file__).parent.parent.parent / "data" / "Json" / "events_only_list.json"
    if not events_json.exists():
        print(f"错误: 找不到文件 {events_json}")
        print("提示: 请先运行 fetch_items_skills_names.py 生成事件名称列表")
        return []
    
    try:
        with open(events_json, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except Exception as e:
        print(f"错误: 读取文件失败: {e}")
        return []

def load_existing_events():
    """加载已存在的事件数据"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "events.json"
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_events(events_data):
    """保存事件数据到JSON文件"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "events.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存 {len(events_data)} 个事件到 {output_file}")

def save_error_log(error_log, output_file):
    """保存错误日志到JSON文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(error_log, f, ensure_ascii=False, indent=2)
    
    total_errors = sum(len(errors) for errors in error_log.values())
    print(f"  ✓ 已保存错误日志到 {output_file} (共 {total_errors} 个错误)")

def process_event(driver, event_name, existing_events_dict, error_log):
    """处理单个事件
    
    Args:
        driver: Selenium WebDriver
        event_name: 事件名称（英文，用于URL）
        existing_events_dict: 已有事件数据字典（key为name）
        error_log: 错误日志字典，用于记录失败信息
    
    Returns:
        (event_data, errors): 事件数据字典和错误信息列表
    """
    errors = []
    try:
        # 检查是否已存在
        if event_name in existing_events_dict:
            existing = existing_events_dict[event_name]
            # 如果已有完整数据，跳过
            if existing.get('name_zh') and existing.get('description_zh') and existing.get('icon'):
                print(f"  ⊙ {event_name} (已存在，跳过)")
                return existing, []
        
        print(f"  → 处理: {event_name}")
        
        # 步骤1: 访问搜索页面并提取JSON数据（带重试机制）
        search_url = f"https://bazaardb.gg/search?q={event_name.replace(' ', '+')}&c=events"
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
                            'event_name': event_name
                        })
                        return existing_events_dict.get(event_name), errors
                else:
                    raise
        
        if not html:
            error_msg = f"无法获取页面内容"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_extraction',
                'message': error_msg,
                'event_name': event_name
            })
            return existing_events_dict.get(event_name), errors
        
        card_json = extract_event_data_from_html(html, event_name)
        if not card_json:
            error_msg = f"未找到卡片数据"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_extraction',
                'message': error_msg,
                'event_name': event_name
            })
            result = existing_events_dict.get(event_name)
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
                'event_name': event_name
            })
            result = existing_events_dict.get(event_name)
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
                'event_name': event_name
            })
        
        if not parsed_data.get('description_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'description_zh',
                'message': '缺少中文描述',
                'event_name': event_name
            })
        
        # 步骤3: 下载图标
        icon_filename = ""
        icon_url = parsed_data.get('icon_url', '')
        if icon_url:
            icon_filename = download_icon(icon_url, parsed_data.get('name', event_name), category='event')
            if not icon_filename:
                error_msg = f"图标下载失败 (URL: {icon_url})"
                print(f"      ⚠ {error_msg}")
                errors.append({
                    'type': 'icon_download',
                    'message': error_msg,
                    'icon_url': icon_url,
                    'event_name': event_name
                })
        else:
            error_msg = "缺少图标URL"
            errors.append({
                'type': 'missing_field',
                'field': 'icon_url',
                'message': error_msg,
                'event_name': event_name
            })
        
        # 步骤4: 构建事件数据
        event_data = {
            "name": parsed_data.get('name', event_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename,
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": f"https://bazaardb.gg/search?q={event_name.replace(' ', '+')}&c=events"
        }
        
        # 步骤5: 如果已有数据，保留已有字段（智能合并）
        if event_name in existing_events_dict:
            existing = existing_events_dict[event_name]
            # 保留已有但新数据中没有的字段
            if existing.get('name_zh') and not event_data.get('name_zh'):
                event_data['name_zh'] = existing['name_zh']
            if existing.get('description_zh') and not event_data.get('description_zh'):
                event_data['description_zh'] = existing['description_zh']
            if existing.get('icon') and not event_data.get('icon'):
                event_data['icon'] = existing['icon']
        
        if errors:
            print(f"      ⚠ 完成（有警告）: {event_data.get('name_zh', event_name)}")
        else:
            print(f"      ✓ 完成: {event_data.get('name_zh', event_name)}")
        
        return event_data, errors
        
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        print(f"      ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        errors.append({
            'type': 'exception',
            'message': error_msg,
            'event_name': event_name,
            'traceback': traceback.format_exc()
        })
        result = existing_events_dict.get(event_name)
        return result, errors

def main():
    """主函数"""
    # 检查是否测试模式
    TEST_MODE = '--test' in sys.argv or '-t' in sys.argv
    TEST_LIMIT = 10 if TEST_MODE else None
    
    print("=" * 80)
    if TEST_MODE:
        print("批量抓取事件详细信息 - 测试模式")
        print(f"只处理前 {TEST_LIMIT} 个事件")
    else:
        print("批量抓取事件详细信息 - 完整模式")
    print("=" * 80)
    
    # 加载事件列表
    print("\n[1/3] 加载事件名称列表...")
    event_names = load_events_list()
    if not event_names:
        return
    
    if TEST_MODE:
        event_names = event_names[:TEST_LIMIT]
    
    print(f"  找到 {len(event_names)} 个事件")
    
    # 加载已有数据
    print("\n[2/3] 加载已有事件数据...")
    existing_events = load_existing_events()
    existing_events_dict = {event.get('name', ''): event for event in existing_events if event.get('name')}
    print(f"  已有 {len(existing_events_dict)} 个事件数据")
    
    # 启动浏览器
    print("\n[3/3] 启动浏览器并开始抓取...")
    driver = setup_driver()
    
    try:
        events_data = []
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        error_log = {}  # 记录所有错误 {event_name: [errors]}
        
        for idx, event_name in enumerate(event_names, 1):
            print(f"\n[{idx}/{len(event_names)}] {event_name}")
            
            try:
                result, errors = process_event(driver, event_name, existing_events_dict, error_log)
                
                # 记录错误
                if errors:
                    error_log[event_name] = errors
                
                if result:
                    events_data.append(result)
                    if event_name in existing_events_dict and result == existing_events_dict[event_name]:
                        skipped_count += 1
                    else:
                        processed_count += 1
                else:
                    failed_count += 1
                
                # 每10个保存一次（增量保存）
                if idx % 10 == 0:
                    save_events(events_data)
                    # 保存错误日志
                    error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "events_errors.json"
                    save_error_log(error_log, error_log_file)
                    print(f"\n  [进度] 已处理: {processed_count}, 跳过: {skipped_count}, 失败: {failed_count}")
                
                # 短暂延迟，避免请求过快
                time.sleep(2)  # 增加延迟，避免网络连接重置
                
            except KeyboardInterrupt:
                print("\n\n用户中断，保存当前进度...")
                save_events(events_data)
                error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "events_errors.json"
                save_error_log(error_log, error_log_file)
                break
            except Exception as e:
                print(f"  ✗ 处理 {event_name} 时出错: {e}")
                failed_count += 1
                error_log[event_name] = [{
                    'type': 'exception',
                    'message': f"处理时发生异常: {str(e)}",
                    'event_name': event_name
                }]
                continue
        
        # 最终保存
        save_events(events_data)
        error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "events_errors.json"
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
        print(f"  总计: {len(events_data)} 个事件")
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

