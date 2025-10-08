import requests
import json
import re
import os
from html import unescape
from pathlib import Path

def download_image(url, save_path):
    """下载图片"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False

def extract_monster_details(html_content, monster_name):
    """从怪物详情页提取技能和掉落物信息"""
    details = {
        "name": monster_name,
        "skills": [],
        "drops": []
    }
    
    # 查找所有包含 "Title" 和 "Text" 的 JSON 对象（技能和掉落物）
    # 匹配模式: "Title":{"Text":"名称"},"Description":{"Text":"描述"},"Art":"图标URL"
    pattern = r'"Title":\s*\{\s*"Text":\s*"([^"]+)"\s*\}[^}]*?"Description":\s*\{\s*"Text":\s*"([^"]*?)"\s*\}[^}]*?"Art":\s*"([^"]+)"'
    
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    for title, description, art_url in matches:
        title = unescape(title)
        description = unescape(description) if description else ""
        
        item = {
            "name": title,
            "description": description,
            "icon_url": art_url,
            "icon_filename": ""
        }
        
        # 从URL提取文件名
        if art_url:
            # 提取类似 "abc123@256.webp" 的部分
            match = re.search(r'/([^/]+@\d+\.webp)', art_url)
            if match:
                item["icon_filename"] = match.group(1)
        
        # 简单判断是技能还是掉落物（可以根据实际情况调整）
        # 如果描述包含伤害、冷却等关键词，可能是技能
        if any(keyword in description.lower() for keyword in ['damage', 'cooldown', 'attack', 'skill']):
            details["skills"].append(item)
        else:
            details["drops"].append(item)
    
    return details

def fetch_monster_details(monster_name):
    """获取单个怪物的详细信息"""
    # 将怪物名称转换为URL格式
    url_name = monster_name.replace(' ', '-')
    url = f"https://bazaardb.gg/search?q={monster_name}"
    
    print(f"\n处理: {monster_name}")
    print(f"  访问: {url}")
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        # 提取详细信息
        details = extract_monster_details(response.text, monster_name)
        
        print(f"  ✓ 找到 {len(details['skills'])} 个技能")
        print(f"  ✓ 找到 {len(details['drops'])} 个掉落物")
        
        return details
        
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 80)
    print("开始获取怪物详细信息...")
    print("=" * 80)
    
    # 读取怪物清单
    monsters_file = 'unique_monsters.json'
    print(f"\n[步骤1] 读取怪物清单: {monsters_file}")
    
    try:
        with open(monsters_file, 'r', encoding='utf-8') as f:
            # 读取每行的怪物名称（去除引号和换行符）
            monster_names = [line.strip().strip('"') for line in f if line.strip()]
        
        print(f"  ✓ 读取到 {len(monster_names)} 个怪物")
    except FileNotFoundError:
        print(f"  ✗ 找不到文件: {monsters_file}")
        return
    
    # 创建输出目录
    output_dir = Path('monster_details')
    icons_dir = output_dir / 'icons'
    output_dir.mkdir(exist_ok=True)
    icons_dir.mkdir(exist_ok=True)
    
    # 获取每个怪物的详细信息
    print(f"\n[步骤2] 获取怪物详细信息")
    all_monsters_details = []
    
    # 只处理前5个怪物作为测试
    test_count = 5
    print(f"  (测试模式: 只处理前 {test_count} 个怪物)")
    
    for i, monster_name in enumerate(monster_names[:test_count], 1):
        print(f"\n[{i}/{test_count}] ", end="")
        
        details = fetch_monster_details(monster_name)
        
        if details:
            all_monsters_details.append(details)
            
            # 下载图标
            for skill in details['skills']:
                if skill['icon_url'] and skill['icon_filename']:
                    icon_path = icons_dir / skill['icon_filename']
                    if not icon_path.exists():
                        print(f"    下载技能图标: {skill['icon_filename']}")
                        download_image(skill['icon_url'], str(icon_path))
            
            for drop in details['drops']:
                if drop['icon_url'] and drop['icon_filename']:
                    icon_path = icons_dir / drop['icon_filename']
                    if not icon_path.exists():
                        print(f"    下载掉落物图标: {drop['icon_filename']}")
                        download_image(drop['icon_url'], str(icon_path))
    
    # 保存结果
    print(f"\n[步骤3] 保存结果")
    output_file = output_dir / 'monsters_details.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_monsters_details, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存到: {output_file}")
    print(f"  ✓ 图标保存在: {icons_dir}")
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in all_monsters_details)
    total_drops = sum(len(m['drops']) for m in all_monsters_details)
    
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"处理怪物数: {len(all_monsters_details)}")
    print(f"总技能数: {total_skills}")
    print(f"总掉落物数: {total_drops}")
    print("=" * 80)

if __name__ == "__main__":
    main()
