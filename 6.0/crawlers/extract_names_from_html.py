"""从HTML文件中提取所有card URL，提取怪物、技能、物品名称"""
import re
import json
from pathlib import Path
from urllib.parse import unquote

def extract_all_card_urls_from_html(html_file_path, keep_duplicates=True):
    """从HTML文件中提取所有card URL
    
    格式: card/随机码/名称
    Args:
        html_file_path: HTML文件路径
        keep_duplicates: 是否保留重复项（默认True，保留所有出现）
    
    返回: 名称列表（按出现顺序，如果keep_duplicates=True则包含重复项）
    """
    if not html_file_path.exists():
        print(f"文件不存在: {html_file_path}")
        return []
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 提取所有 card/随机码/名称 的URL
    # 模式: card/随机字符/名称
    # 使用更精确的模式，确保匹配完整的URL
    pattern = r'/card/([a-zA-Z0-9]+)/([^"\'/\s<>?&]+)'
    matches = re.findall(pattern, html)
    
    print(f"  找到 {len(matches)} 个card URL匹配")
    
    # 提取名称（第二个捕获组）
    names = []
    seen = set() if not keep_duplicates else None
    
    for code, name in matches:
        # URL解码
        decoded_name = unquote(name)
        
        if keep_duplicates:
            # 保留所有出现（包括重复）
            names.append(decoded_name)
        else:
            # 去重但保持顺序
            if decoded_name not in seen:
                seen.add(decoded_name)
                names.append(decoded_name)
    
    return names

def extract_card_urls_from_html(html_file_path):
    """从HTML文件中提取所有card URL（保留重复项）"""
    return extract_all_card_urls_from_html(html_file_path, keep_duplicates=True)

def extract_from_monsters_html(use_english=True, keep_duplicates=True):
    """从monsters_list_page.html提取所有名称
    
    Args:
        use_english: 是否使用英文版本（monsters_list_page_en.html）
        keep_duplicates: 是否保留重复项（默认True，保留所有出现）
    """
    if use_english:
        html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page_en.html"
        if not html_file.exists():
            print(f"英文HTML文件不存在: {html_file}")
            print("请先运行 fetch_monsters_html_english.py 抓取英文HTML")
            return []
    else:
        html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page.html"
    
    names = extract_all_card_urls_from_html(html_file, keep_duplicates=keep_duplicates)
    
    if keep_duplicates:
        print(f"从 {html_file.name} 提取到 {len(names)} 个名称（包含重复）")
        # 统计唯一名称数量
        unique_names = len(set(names))
        print(f"  其中唯一名称: {unique_names} 个")
    else:
        print(f"从 {html_file.name} 提取到 {len(names)} 个唯一名称")
    
    print(f"前10个: {names[:10]}")
    
    # 检查Flame-Juggler和Magma-Core
    flame_juggler_count = names.count('Flame-Juggler')
    magma_core_count = names.count('Magma-Core')
    burst_of_flame_count = names.count('Burst-of-Flame')
    
    print(f"\n示例统计:")
    print(f"  Flame-Juggler: {flame_juggler_count} 次")
    print(f"  Burst-of-Flame: {burst_of_flame_count} 次")
    print(f"  Magma-Core: {magma_core_count} 次")
    
    # 保存到JSON
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_from_html.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")
    
    return names

if __name__ == "__main__":
    import sys
    use_english = '--en' in sys.argv or '--english' in sys.argv
    keep_duplicates = '--no-dedup' in sys.argv or '--keep-duplicates' in sys.argv
    # 默认保留重复项
    if '--dedup' in sys.argv or '--unique' in sys.argv:
        keep_duplicates = False
    
    extract_from_monsters_html(use_english=use_english, keep_duplicates=keep_duplicates)

