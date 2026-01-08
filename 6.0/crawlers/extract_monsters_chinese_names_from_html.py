"""从中文HTML文件中提取怪物的中英文名称对应关系"""
import json
import re
from pathlib import Path
from urllib.parse import unquote
from html import unescape

def is_chinese(text):
    """检查文本是否包含中文字符"""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def extract_monster_name_pairs_from_html(html_file_path):
    """从HTML文件中提取怪物的中英文名称对应关系
    
    从 card/随机码/名称 的URL中提取：
    - 通过相同的随机码匹配中英文名称
    - 如果名称是中文，则是中文名称
    - 如果名称是英文，则是英文名称
    """
    if not html_file_path.exists():
        print(f"文件不存在: {html_file_path}")
        return {}
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 字典：英文名称 -> 中文名称
    name_pairs = {}
    
    # 从 card/随机码/名称 URL中提取
    # 提取所有 card URL
    pattern = r'/card/([a-zA-Z0-9]+)/([^"\'/\s<>?&]+)'
    matches = re.findall(pattern, html)
    
    print(f"  找到 {len(matches)} 个card URL")
    
    # 按code分组，收集每个code对应的中英文名称
    code_to_names = {}
    for code, name in matches:
        decoded_name = unquote(name)
        if code not in code_to_names:
            code_to_names[code] = {'zh': [], 'en': []}
        
        if is_chinese(decoded_name):
            code_to_names[code]['zh'].append(decoded_name)
        else:
            # 英文名称，转换为标准格式（去掉末尾反斜杠，空格替换连字符，首字母大写）
            english_name = decoded_name.rstrip('\\').replace('-', ' ').title()
            code_to_names[code]['en'].append(english_name)
    
    # 通过相同的code匹配中英文名称
    for code, names in code_to_names.items():
        if names['zh'] and names['en']:
            # 取第一个中文和第一个英文名称
            zh_name = names['zh'][0]
            en_name = names['en'][0]
            name_pairs[en_name] = zh_name
    
    print(f"  通过code匹配到 {len(name_pairs)} 个中英文名称对应关系")
    
    return name_pairs

def main():
    """主函数：从HTML文件提取怪物中英文名称对应关系"""
    # 读取中文HTML文件
    html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page.html"
    
    if not html_file.exists():
        print(f"错误: HTML文件不存在: {html_file}")
        return
    
    print(f"从 {html_file.name} 提取怪物中英文名称对应关系...")
    
    # 提取名称对应关系
    name_pairs = extract_monster_name_pairs_from_html(html_file)
    
    # 读取怪物列表
    monsters_list_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_only_list.json"
    if not monsters_list_file.exists():
        print(f"错误: 文件不存在: {monsters_list_file}")
        return
    
    with open(monsters_list_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        # 处理JSON Lines格式（每行一个字符串）
        if content.startswith('"'):
            monsters = []
            for line in content.split('\n'):
                line = line.strip()
                if line and line.startswith('"') and line.endswith('"'):
                    monsters.append(json.loads(line))
        else:
            monsters = json.load(f)
    
    print(f"\n找到 {len(monsters)} 个怪物")
    
    # 读取现有的monsters.json（如果有）
    monsters_json_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters.json"
    existing_monsters = {}
    if monsters_json_file.exists():
        try:
            with open(monsters_json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    for monster in existing_data:
                        if isinstance(monster, dict) and 'name' in monster:
                            existing_monsters[monster['name']] = monster
        except:
            pass
    
    # 构建结果列表
    results = []
    success_count = 0
    fail_count = 0
    
    for monster_name in monsters:
        # 检查是否已有中文名称
        if monster_name in existing_monsters:
            existing = existing_monsters[monster_name]
            if existing.get('name_zh'):
                print(f"  ⊙ {monster_name} -> {existing['name_zh']} (已有)")
                results.append(existing)
                success_count += 1
                continue
        
        # 查找中文名称
        chinese_name = name_pairs.get(monster_name, '')
        
        if chinese_name:
            print(f"  ✓ {monster_name} -> {chinese_name}")
            monster_data = {
                "name": monster_name,
                "name_zh": chinese_name,
                "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
            }
            results.append(monster_data)
            success_count += 1
        else:
            print(f"  ✗ {monster_name} -> 未找到中文名称")
            monster_data = {
                "name": monster_name,
                "name_zh": "",
                "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
            }
            results.append(monster_data)
            fail_count += 1
    
    # 保存结果
    output_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成!")
    print(f"  成功: {success_count}/{len(monsters)}")
    print(f"  失败: {fail_count}/{len(monsters)}")
    print(f"  已保存到: {output_file}")

if __name__ == "__main__":
    main()

