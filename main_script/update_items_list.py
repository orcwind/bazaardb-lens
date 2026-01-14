"""
更新 items_only_list.json，增加中文名称
从 items.json 中读取中文名，与英文名关联
"""
import os
import sys
import json
import re

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def normalize_name(name):
    """
    标准化名称用于匹配
    将 "28-Hour-Fitness" 和 "28 Hour Fitness" 都转换为 "28hourfitness"
    """
    # 移除所有非字母数字字符，转小写
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def main():
    # 文件路径
    items_json_path = os.path.join(project_root, 'data', 'Json', 'items.json')
    items_list_path = os.path.join(project_root, 'data', 'Json', 'items_only_list.json')
    output_path = os.path.join(project_root, 'data', 'Json', 'items_with_zh.json')
    
    print("=" * 60)
    print("更新物品列表，增加中文名称")
    print("=" * 60)
    
    # 1. 读取 items.json
    print(f"\n读取 items.json...")
    with open(items_json_path, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    print(f"  加载了 {len(items_data)} 个物品数据")
    
    # 2. 建立英文名 -> 中文名 的映射
    name_mapping = {}
    for item in items_data:
        name_en = item.get('name', '')
        name_zh = item.get('name_zh', '')
        if name_en and name_zh:
            # 使用标准化名称作为key
            normalized = normalize_name(name_en)
            name_mapping[normalized] = {
                'name': name_en,
                'name_zh': name_zh
            }
    print(f"  建立了 {len(name_mapping)} 个名称映射")
    
    # 3. 读取 items_only_list.json
    print(f"\n读取 items_only_list.json...")
    with open(items_list_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # 文件格式是每行一个带引号的字符串，如 "28-Hour-Fitness"
    # 解析方式：按行读取，去除引号
    items_list = []
    for line in content.split('\n'):
        line = line.strip()
        if line:
            # 移除引号
            name = line.strip('"').strip("'")
            if name:
                items_list.append(name)
    print(f"  加载了 {len(items_list)} 个物品名称")
    
    # 4. 匹配并生成新的列表
    print(f"\n匹配中文名称...")
    matched_count = 0
    unmatched = []
    new_items_list = []
    
    for item_name in items_list:
        # 清理名称（移除引号）
        if isinstance(item_name, str):
            name_en = item_name.strip().strip('"')
        else:
            name_en = str(item_name)
        
        # 尝试匹配
        normalized = normalize_name(name_en)
        
        if normalized in name_mapping:
            mapping = name_mapping[normalized]
            new_items_list.append({
                'name_en': name_en,
                'name': mapping['name'],
                'name_zh': mapping['name_zh']
            })
            matched_count += 1
        else:
            # 未匹配到，只保留英文名
            new_items_list.append({
                'name_en': name_en,
                'name': name_en.replace('-', ' '),
                'name_zh': ''
            })
            unmatched.append(name_en)
    
    print(f"  匹配成功: {matched_count} / {len(items_list)}")
    print(f"  匹配率: {matched_count/len(items_list)*100:.1f}%")
    
    if unmatched:
        print(f"\n未匹配的物品 ({len(unmatched)}个):")
        for name in unmatched[:20]:
            print(f"    - {name}")
        if len(unmatched) > 20:
            print(f"    ... 还有 {len(unmatched) - 20} 个")
    
    # 5. 保存新文件
    print(f"\n保存到 {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_items_list, f, ensure_ascii=False, indent=2)
    print(f"  保存完成！")
    
    # 6. 同时更新原文件（覆盖）
    print(f"\n是否覆盖原文件 items_only_list.json? (自动执行)")
    with open(items_list_path, 'w', encoding='utf-8') as f:
        json.dump(new_items_list, f, ensure_ascii=False, indent=2)
    print(f"  原文件已更新！")
    
    # 7. 显示几个示例
    print(f"\n【示例数据】")
    for item in new_items_list[:5]:
        print(f"  {item['name_en']:30} => {item['name_zh']}")
    
    print("\n完成！")

if __name__ == '__main__':
    main()
