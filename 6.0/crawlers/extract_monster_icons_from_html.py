"""
从monsters_list_page_en.html提取所有monster的icon URL并下载
"""
import json
import re
import requests
from pathlib import Path
from urllib.parse import unquote

# 配置路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
HTML_FILE = PROJECT_ROOT / "data" / "html" / "monsters_list_page_en.html"
MONSTERS_JSON = PROJECT_ROOT / "data" / "Json" / "monsters.json"
ICON_DIR = PROJECT_ROOT / "data" / "icon" / "monster"

# 确保icon目录存在
ICON_DIR.mkdir(parents=True, exist_ok=True)


def extract_monster_icons_from_html(html_file):
    """从HTML文件中提取monster icon URL
    
    格式: <img src="https://s.bazaardb.gg/v0/z10.0/encounter/{hash}@256.webp?v=2" alt="MonsterName" class="_aV">
    
    返回: {monster_name: icon_url} 字典
    """
    if not html_file.exists():
        print(f"文件不存在: {html_file}")
        return {}
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 匹配 <img src="...encounter/...@256.webp" alt="MonsterName" class="_aV">
    # 使用更精确的正则表达式
    pattern = r'<img\s+src="(https://s\.bazaardb\.gg/v0/[^/]+/encounter/[^"]+@256\.webp[^"]*)"\s+alt="([^"]+)"\s+class="_aV"'
    matches = re.findall(pattern, html)
    
    monster_icons = {}
    for icon_url, monster_name in matches:
        # 清理怪物名称
        monster_name = unquote(monster_name) if monster_name else ""
        if monster_name:
            monster_icons[monster_name] = icon_url
    
    print(f"从HTML中提取到 {len(monster_icons)} 个monster icon URL")
    return monster_icons


def download_icon(icon_url, monster_name):
    """下载icon并保存到data/icon/monster/文件夹"""
    if not icon_url:
        return False
    
    try:
        # 清理文件名中的非法字符
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
        filename = f"{safe_name}.webp"
        filepath = ICON_DIR / filename
        
        # 如果文件已存在，跳过下载
        if filepath.exists():
            print(f"      ✓ 图标已存在: {filename}")
            return True
        
        # 下载图标
        response = requests.get(icon_url, timeout=10)
        response.raise_for_status()
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"      ✓ 下载成功: {filename}")
        return True
    
    except Exception as e:
        print(f"      ✗ 下载失败: {e}")
        return False


def load_monsters():
    """加载monsters.json获取所有怪物名称"""
    if not MONSTERS_JSON.exists():
        print(f"文件不存在: {MONSTERS_JSON}")
        return []
    
    try:
        with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
        print(f"加载了 {len(monsters)} 个怪物")
        return monsters
    except Exception as e:
        print(f"加载怪物列表失败: {e}")
        return []


def main():
    """主函数"""
    print("=" * 80)
    print("从HTML文件提取并下载怪物图标")
    print("=" * 80)
    
    # 提取icon URL
    print(f"\n[1/3] 从HTML文件提取icon URL...")
    monster_icons = extract_monster_icons_from_html(HTML_FILE)
    
    if not monster_icons:
        print("未找到任何icon URL")
        return
    
    # 加载monsters.json获取完整列表
    print(f"\n[2/3] 加载怪物列表...")
    monsters = load_monsters()
    
    # 创建名称映射（处理可能的名称差异）
    monster_dict = {monster.get('name', ''): monster for monster in monsters}
    
    # 下载icon
    print(f"\n[3/3] 下载图标...")
    success_count = 0
    fail_count = 0
    skip_count = 0
    not_found_count = 0
    
    for idx, monster in enumerate(monsters, 1):
        monster_name = monster.get('name', '')
        
        if not monster_name:
            continue
        
        print(f"\n[{idx}/{len(monsters)}] {monster_name}")
        
        # 查找对应的icon URL
        icon_url = monster_icons.get(monster_name)
        
        if not icon_url:
            # 尝试查找（可能名称有差异）
            for html_name, url in monster_icons.items():
                if html_name.lower() == monster_name.lower():
                    icon_url = url
                    print(f"  找到匹配（名称略有不同）: {html_name}")
                    break
        
        if not icon_url:
            print(f"  ✗ 未找到icon URL")
            not_found_count += 1
            continue
        
        # 检查是否已存在
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
        icon_file = ICON_DIR / f"{safe_name}.webp"
        if icon_file.exists():
            print(f"  ✓ 图标已存在，跳过")
            skip_count += 1
            continue
        
        # 下载
        if download_icon(icon_url, monster_name):
            success_count += 1
        else:
            fail_count += 1
    
    # 统计
    print("\n" + "=" * 80)
    print("下载完成！")
    print("=" * 80)
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    print(f"跳过: {skip_count} 个")
    print(f"未找到: {not_found_count} 个")
    print(f"总计: {len(monsters)} 个")
    print(f"\n图标保存位置: {ICON_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()


