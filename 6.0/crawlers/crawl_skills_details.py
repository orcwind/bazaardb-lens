"""
批量抓取技能详细信息
从 skills_only_list.json 读取技能名称列表，逐个访问搜索页面提取数据

功能：
1. 读取 data/Json/skills_only_list.json
2. 为每个技能访问 https://bazaardb.gg/search?q={skill_name}&c=skills
3. 提取：name, name_zh, description_zh, icon, aspect_ratio
4. 下载图标到 data/icon/skill 目录
5. 增量保存到 data/Json/skills.json
"""

import json
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

# 导入必要的函数
sys.path.insert(0, str(Path(__file__).parent))

from selenium_items_skills import (
    extract_card_data_from_search_page,
    parse_card_json_data,
    size_to_aspect_ratio,
    setup_driver
)
from utils_icon import download_icon

def load_skills_list():
    """从 skills_only_list.json 加载技能名称列表"""
    skills_json = Path(__file__).parent.parent.parent / "data" / "Json" / "skills_only_list.json"
    if not skills_json.exists():
        print(f"错误: 找不到文件 {skills_json}")
        print("提示: 请先运行 fetch_items_skills_names.py 生成技能名称列表")
        return []
    
    try:
        with open(skills_json, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except Exception as e:
        print(f"错误: 读取文件失败: {e}")
        return []

def load_existing_skills():
    """加载已存在的技能数据"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills.json"
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_skills(skills_data):
    """保存技能数据到JSON文件"""
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(skills_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存 {len(skills_data)} 个技能到 {output_file}")

def save_error_log(error_log, output_file):
    """保存错误日志到JSON文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(error_log, f, ensure_ascii=False, indent=2)
    
    total_errors = sum(len(errors) for errors in error_log.values())
    print(f"  ✓ 已保存错误日志到 {output_file} (共 {total_errors} 个错误)")

def process_skill(driver, skill_name, existing_skills_dict, error_log):
    """处理单个技能
    
    Args:
        driver: Selenium WebDriver
        skill_name: 技能名称（英文，用于URL）
        existing_skills_dict: 已有技能数据字典（key为name）
        error_log: 错误日志字典，用于记录失败信息
    
    Returns:
        (skill_data, errors): 技能数据字典和错误信息列表
    """
    errors = []
    try:
        # 检查是否已存在
        if skill_name in existing_skills_dict:
            existing = existing_skills_dict[skill_name]
            # 如果已有完整数据，跳过
            if existing.get('name_zh') and existing.get('description_zh') and existing.get('icon'):
                print(f"  ⊙ {skill_name} (已存在，跳过)")
                return existing, []
        
        print(f"  → 处理: {skill_name}")
        
        # 步骤1: 从搜索页面提取JSON数据
        card_json = extract_card_data_from_search_page(driver, skill_name, 'skills')
        if not card_json:
            error_msg = f"未找到卡片数据"
            print(f"      ✗ {error_msg}")
            errors.append({
                'type': 'data_extraction',
                'message': error_msg,
                'skill_name': skill_name
            })
            result = existing_skills_dict.get(skill_name)
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
                'skill_name': skill_name
            })
            result = existing_skills_dict.get(skill_name)
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
                'skill_name': skill_name
            })
        
        if not parsed_data.get('description_zh'):
            errors.append({
                'type': 'missing_field',
                'field': 'description_zh',
                'message': '缺少中文描述',
                'skill_name': skill_name
            })
        
        # 步骤3: 下载图标
        icon_filename = ""
        icon_url = parsed_data.get('icon_url', '')
        if icon_url:
            icon_filename = download_icon(icon_url, parsed_data.get('name', skill_name), category='skill')
            if not icon_filename:
                error_msg = f"图标下载失败 (URL: {icon_url})"
                print(f"      ⚠ {error_msg}")
                errors.append({
                    'type': 'icon_download',
                    'message': error_msg,
                    'icon_url': icon_url,
                    'skill_name': skill_name
                })
        else:
            error_msg = "缺少图标URL"
            errors.append({
                'type': 'missing_field',
                'field': 'icon_url',
                'message': error_msg,
                'skill_name': skill_name
            })
        
        # 步骤4: 构建技能数据
        skill_data = {
            "name": parsed_data.get('name', skill_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename,
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": f"https://bazaardb.gg/search?q={skill_name.replace(' ', '+')}&c=skills"
        }
        
        # 步骤5: 如果已有数据，保留已有字段（智能合并）
        if skill_name in existing_skills_dict:
            existing = existing_skills_dict[skill_name]
            # 保留已有但新数据中没有的字段
            if existing.get('name_zh') and not skill_data.get('name_zh'):
                skill_data['name_zh'] = existing['name_zh']
            if existing.get('description_zh') and not skill_data.get('description_zh'):
                skill_data['description_zh'] = existing['description_zh']
            if existing.get('icon') and not skill_data.get('icon'):
                skill_data['icon'] = existing['icon']
        
        if errors:
            print(f"      ⚠ 完成（有警告）: {skill_data.get('name_zh', skill_name)}")
        else:
            print(f"      ✓ 完成: {skill_data.get('name_zh', skill_name)}")
        
        return skill_data, errors
        
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        print(f"      ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        errors.append({
            'type': 'exception',
            'message': error_msg,
            'skill_name': skill_name,
            'traceback': traceback.format_exc()
        })
        result = existing_skills_dict.get(skill_name)
        return result, errors

def main():
    """主函数"""
    # 检查是否测试模式
    TEST_MODE = '--test' in sys.argv or '-t' in sys.argv
    TEST_LIMIT = 10 if TEST_MODE else None
    
    print("=" * 80)
    if TEST_MODE:
        print("批量抓取技能详细信息 - 测试模式")
        print(f"只处理前 {TEST_LIMIT} 个技能")
    else:
        print("批量抓取技能详细信息 - 完整模式")
    print("=" * 80)
    
    # 加载技能列表
    print("\n[1/3] 加载技能名称列表...")
    skill_names = load_skills_list()
    if not skill_names:
        return
    
    if TEST_MODE:
        skill_names = skill_names[:TEST_LIMIT]
    
    print(f"  找到 {len(skill_names)} 个技能")
    
    # 加载已有数据
    print("\n[2/3] 加载已有技能数据...")
    existing_skills = load_existing_skills()
    existing_skills_dict = {skill.get('name', ''): skill for skill in existing_skills if skill.get('name')}
    print(f"  已有 {len(existing_skills_dict)} 个技能数据")
    
    # 启动浏览器
    print("\n[3/3] 启动浏览器并开始抓取...")
    driver = setup_driver()
    
    try:
        skills_data = []
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        error_log = {}  # 记录所有错误 {skill_name: [errors]}
        
        for idx, skill_name in enumerate(skill_names, 1):
            print(f"\n[{idx}/{len(skill_names)}] {skill_name}")
            
            try:
                result, errors = process_skill(driver, skill_name, existing_skills_dict, error_log)
                
                # 记录错误
                if errors:
                    error_log[skill_name] = errors
                
                if result:
                    skills_data.append(result)
                    if skill_name in existing_skills_dict and result == existing_skills_dict[skill_name]:
                        skipped_count += 1
                    else:
                        processed_count += 1
                else:
                    failed_count += 1
                
                # 每10个保存一次（增量保存）
                if idx % 10 == 0:
                    save_skills(skills_data)
                    # 保存错误日志
                    error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills_errors.json"
                    save_error_log(error_log, error_log_file)
                    print(f"\n  [进度] 已处理: {processed_count}, 跳过: {skipped_count}, 失败: {failed_count}")
                
                # 短暂延迟，避免请求过快
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n\n用户中断，保存当前进度...")
                save_skills(skills_data)
                error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills_errors.json"
                save_error_log(error_log, error_log_file)
                break
            except Exception as e:
                print(f"  ✗ 处理 {skill_name} 时出错: {e}")
                failed_count += 1
                error_log[skill_name] = [{
                    'type': 'exception',
                    'message': f"处理时发生异常: {str(e)}",
                    'skill_name': skill_name
                }]
                continue
        
        # 最终保存
        save_skills(skills_data)
        error_log_file = Path(__file__).parent.parent.parent / "data" / "Json" / "skills_errors.json"
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
        print(f"  总计: {len(skills_data)} 个技能")
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

