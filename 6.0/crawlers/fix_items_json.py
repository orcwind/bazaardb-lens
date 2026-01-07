"""
修复 items.json 中的错误数据：
1. 修复 name 字段（目前全是 "Ctrl+K"）
2. 修复 description 字段（确保有中文描述）
"""

import json
from pathlib import Path
import re
from urllib.parse import unquote

def is_chinese(text):
    """检查文本是否包含中文字符"""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def extract_name_from_url(url):
    """从URL中提取名称"""
    # URL格式: /card/HASH/NAME
    match = re.search(r'/card/[^/]+/([^/\?]+)', url)
    if match:
        url_name = match.group(1)
        # URL解码
        decoded_name = unquote(url_name)
        # 移除/zh-CN等后缀
        if '/zh-CN' in decoded_name:
            decoded_name = decoded_name.replace('/zh-CN', '').strip()
        return decoded_name
    return None

def fix_items_json():
    """修复 items.json"""
    items_file = Path('../../data/Json/items.json')
    
    if not items_file.exists():
        print(f"错误: 找不到文件 {items_file}")
        return
    
    with open(items_file, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    print(f"找到 {len(items)} 个物品")
    fixed_count = 0
    
    for item in items:
        url = item.get('url', '')
        name_zh = item.get('name_zh', '')
        name = item.get('name', '')
        description_zh = item.get('description_zh', '')
        description = item.get('description', '')
        
        # 修复 name 字段（如果是 "Ctrl+K" 或错误的）
        if name == "Ctrl+K" or not name or name == name_zh:
            # 从URL提取英文名称
            url_name = extract_name_from_url(url)
            if url_name and not is_chinese(url_name):
                # 英文名称：将连字符替换为空格，并首字母大写
                fixed_name = url_name.replace('-', ' ').title()
                if fixed_name != name:
                    print(f"修复名称: {name_zh or name} -> {fixed_name}")
                    item['name'] = fixed_name
                    fixed_count += 1
            elif name_zh and not name:
                # 如果没有英文名称，至少保留中文名称作为备用
                item['name'] = name_zh
                print(f"警告: {name_zh} 没有英文名称，使用中文名称作为备用")
        
        # 修复 description 字段（如果 description_zh 和 description 都是英文）
        if description and description_zh and not is_chinese(description_zh):
            # 如果中文描述是英文，尝试从英文描述中提取
            # 这种情况下，说明中文描述提取失败了
            print(f"警告: {name_zh or name} 的中文描述是英文: {description_zh[:50]}...")
            # 暂时保持原样，需要重新抓取
    
    # 保存修复后的数据
    with open(items_file, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f"\n修复完成！共修复 {fixed_count} 个物品的 name 字段")
    print(f"数据已保存到: {items_file}")

if __name__ == "__main__":
    fix_items_json()

