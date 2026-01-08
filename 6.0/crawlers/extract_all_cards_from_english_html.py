"""从英文HTML文件中按顺序提取所有card/随机码/名称"""
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
    
    print(f"HTML文件长度: {len(html)} 字符")
    
    # 提取所有 card/随机码/名称 的URL
    # 模式: card/随机字符/名称
    # 使用更精确的模式，确保匹配完整的URL
    pattern = r'/card/([a-zA-Z0-9]+)/([^"\'/\s<>?&]+)'
    matches = re.findall(pattern, html)
    
    print(f"找到 {len(matches)} 个card URL匹配")
    
    # 提取名称（第二个捕获组）
    names = []
    
    for code, name in matches:
        # URL解码
        decoded_name = unquote(name)
        # 保留所有出现（包括重复）
        names.append(decoded_name)
    
    print(f"提取到 {len(names)} 个名称（包含重复）")
    
    # 统计唯一名称数量
    unique_names = len(set(names))
    print(f"  其中唯一名称: {unique_names} 个")
    
    # 显示前10个
    print(f"\n前10个名称:")
    for i, name in enumerate(names[:10], 1):
        print(f"  {i}. {name}")
    
    return names

def main():
    """主函数"""
    # 英文HTML文件路径
    html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page_en.html"
    
    if not html_file.exists():
        print(f"错误: HTML文件不存在: {html_file}")
        return
    
    print(f"从 {html_file.name} 提取所有card URL...")
    
    # 提取所有card URL名称
    names = extract_all_card_urls_from_html(html_file, keep_duplicates=True)
    
    # 保存到temp_monster.json
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "temp_monster.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")
    print(f"总共 {len(names)} 个名称（包含重复）")

if __name__ == "__main__":
    main()

