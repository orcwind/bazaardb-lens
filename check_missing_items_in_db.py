"""
检查 items_db.json 中是否包含缺失的物品
只检查是否存在以及是否有中文名称，不检查品质
"""
import json
import os

def check_missing_items_in_db():
    """检查 items_db.json 中是否包含缺失的物品"""
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
    
    # 需要检查的物品列表
    missing_items = [
        "Knife Sharpener",
        "Crow's Nest",
        "Captain's Wheel",
        "Magnus' Femur",
        "Admiral's Badge",
        "Mortar & Pestle",
        "Arken's Ring",
        "Philosopher's Stone"
    ]
    
    print(f"检查文件：{json_file}")
    print(f"物品总数：{len(items_data)}\n")
    print("=" * 80)
    
    # 将 items_data 转换为字典，键为物品名称（用于快速查找）
    items_by_name = {}
    for uuid, item in items_data.items():
        item_name = item.get('name', '')
        if item_name:
            items_by_name[item_name] = item
    
    results = []
    
    for item_name in missing_items:
        # 处理 HTML 实体编码
        item_name_encoded = item_name.replace("'", "&#x27;")
        
        found = False
        found_name = None
        name_zh = None
        
        # 尝试原始名称
        if item_name in items_by_name:
            found = True
            found_name = item_name
            name_zh = items_by_name[item_name].get('name_zh', '')
        # 尝试编码后的名称
        elif item_name_encoded in items_by_name:
            found = True
            found_name = item_name_encoded
            name_zh = items_by_name[item_name_encoded].get('name_zh', '')
        else:
            # 尝试不区分大小写搜索
            for db_name, db_item in items_by_name.items():
                if db_name.lower() == item_name.lower() or db_name.lower() == item_name_encoded.lower():
                    found = True
                    found_name = db_name
                    name_zh = db_item.get('name_zh', '')
                    break
        
        results.append({
            'name': item_name,
            'found': found,
            'found_name': found_name,
            'name_zh': name_zh or '(无)',
            'has_name_zh': bool(name_zh)
        })
    
    # 输出结果
    print("检查结果：\n")
    
    found_count = 0
    found_with_zh_count = 0
    not_found_count = 0
    found_without_zh_count = 0
    
    for result in results:
        if result['found']:
            found_count += 1
            if result['has_name_zh']:
                found_with_zh_count += 1
                status = "✅"
            else:
                found_without_zh_count += 1
                status = "⚠️"
            print(f"{status} {result['name']}")
            print(f"   找到名称: {result['found_name']}")
            print(f"   中文名称: {result['name_zh']}")
        else:
            not_found_count += 1
            print(f"❌ {result['name']}")
            print(f"   未找到")
        print()
    
    print("=" * 80)
    print(f"总结：")
    print(f"  - 找到物品: {found_count}/{len(missing_items)} 个")
    print(f"  - 有中文名称: {found_with_zh_count} 个")
    print(f"  - 无中文名称: {found_without_zh_count} 个")
    print(f"  - 未找到: {not_found_count} 个")

if __name__ == '__main__':
    check_missing_items_in_db()
