"""
检查 items_db.json 文件的完整性
检查缺失的中文名称、品质等信息
"""
import json
import os

def check_items_db_completeness():
    """检查 items_db.json 的完整性"""
    json_file = os.path.join('data', 'Json', 'items_db.json')
    
    if not os.path.exists(json_file):
        print(f"错误：未找到文件 {json_file}")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
    except Exception as e:
        print(f"错误：读取文件失败: {e}")
        return
    
    # 判断数据结构：字典还是列表
    if isinstance(items_data, dict):
        items = list(items_data.values())
        print(f"检查文件：{json_file} (字典格式，{len(items_data)} 个物品)")
    elif isinstance(items_data, list):
        items = items_data
        print(f"检查文件：{json_file} (列表格式)")
    else:
        print(f"错误：不支持的数据格式")
        return
    
    print(f"物品总数：{len(items)}\n")
    print("=" * 80)
    
    issues = []
    total_items = len(items)
    
    # 统计缺失类型
    missing_name_count = 0
    missing_name_zh_count = 0
    missing_quality_count = 0
    
    for idx, item in enumerate(items, 1):
        item_name = item.get('name', '')
        item_name_zh = item.get('name_zh', '')
        item_quality = item.get('quality')
        
        issues_found = []
        
        # 1. 检查物品英文名称
        if not item_name:
            issues_found.append(f"缺少英文名称 (name)")
            missing_name_count += 1
        
        # 2. 检查物品中文名称
        if not item_name_zh:
            issues_found.append(f"缺少中文名称 (name_zh)")
            missing_name_zh_count += 1
        
        # 3. 检查品质（quality 可以是 null，但如果有这个字段也算完整）
        # 注意：quality 可能不存在，也可能是 null 或空字符串
        if 'quality' not in item:
            # quality 字段不存在
            pass  # 如果文件中没有 quality 字段，不算缺失
        elif item_quality is None:
            # quality 字段存在但值为 null
            issues_found.append(f"品质为空 (quality: null)")
            missing_quality_count += 1
        elif item_quality == '':
            # quality 字段存在但值为空字符串
            issues_found.append(f"品质为空 (quality: '')")
            missing_quality_count += 1
        
        # 如果有问题，记录
        if issues_found:
            issues.append({
                'index': idx,
                'name': item_name or '(无)',
                'name_zh': item_name_zh or '(无)',
                'quality': item_quality if item_quality is not None else '(null)',
                'issues': issues_found
            })
    
    # 输出结果
    if not issues:
        print("✅ 检查完成：未发现缺失信息！")
        print(f"所有 {total_items} 个物品的数据完整。")
    else:
        print(f"❌ 发现 {len(issues)} 个物品存在缺失信息：\n")
        
        # 只显示前20个，避免输出过多
        display_count = min(20, len(issues))
        for issue in issues[:display_count]:
            print(f"【物品 #{issue['index']}】{issue['name']} ({issue['name_zh']})")
            print(f"  品质: {issue['quality']}")
            print(f"  问题：")
            for problem in issue['issues']:
                print(f"    - {problem}")
            print()
        
        if len(issues) > display_count:
            print(f"... 还有 {len(issues) - display_count} 个物品存在缺失信息（未显示）\n")
        
        print("=" * 80)
        print(f"总结：{len(issues)}/{total_items} 个物品存在缺失信息")
        
        print("\n缺失统计：")
        if missing_name_count > 0:
            print(f"  - 缺少英文名称 (name): {missing_name_count} 个")
        if missing_name_zh_count > 0:
            print(f"  - 缺少中文名称 (name_zh): {missing_name_zh_count} 个")
        if missing_quality_count > 0:
            print(f"  - 品质为空 (quality 为 null 或 '': {missing_quality_count} 个")

if __name__ == '__main__':
    check_items_db_completeness()
