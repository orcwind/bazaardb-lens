import requests
import json
import re
import os
from html import unescape
from pathlib import Path
from bs4 import BeautifulSoup

def download_image(url, save_path):
    """下载图片"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"    ✗ 下载失败: {e}")
        return False

def get_monster_detail_url(monster_name, session):
    """从搜索页面获取怪物详情页URL"""
    search_url = f"https://bazaardb.gg/search?q={monster_name}&c=monsters"
    
    try:
        response = session.get(search_url, timeout=30)
        response.raise_for_status()
        
        # 在HTML中查找详情页链接
        # 格式: /card/{id}/{name}
        pattern = r'/card/([a-z0-9]+)/' + re.escape(monster_name.replace(' ', '-'))
        match = re.search(pattern, response.text, re.IGNORECASE)
        
        if match:
            card_id = match.group(1)
            detail_url = f"https://bazaardb.gg/card/{card_id}/{monster_name.replace(' ', '-')}"
            return detail_url
        
        return None
        
    except Exception as e:
        print(f"    ✗ 获取详情URL失败: {e}")
        return None

def extract_monster_details(html_content, monster_name):
    """从怪物详情页提取技能和物品信息"""
    details = {
        "name": monster_name,
        "skills": [],
        "items": [],
        "level": "",
        "health": ""
    }
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取等级和血量
    # 查找包含 "Level" 和 "Health" 的文本
    level_match = re.search(r'Level\s*(\d+)', html_content)
    if level_match:
        details["level"] = level_match.group(1)
    
    health_match = re.search(r'Health\s*(\d+)', html_content)
    if health_match:
        details["health"] = health_match.group(1)
    
    # 提取技能 (Skills)
    # 在HTML中查找 "### Skills" 之后的内容
    skills_section = re.search(r'### Skills(.*?)(?:### Items|$)', html_content, re.DOTALL)
    if skills_section:
        skills_text = skills_section.group(1)
        
        # 提取技能名称和描述
        # 格式: 技能名\n...\n描述文本
        skill_pattern = r'([A-Z][A-Za-z\s]+)\n.*?\n([^\n]+(?:\n[^\n#]+)*)'
        skill_matches = re.findall(skill_pattern, skills_text)
        
        for skill_name, skill_desc in skill_matches:
            skill_name = skill_name.strip()
            skill_desc = skill_desc.strip()
            
            if skill_name and skill_desc and len(skill_name) < 50:
                details["skills"].append({
                    "name": skill_name,
                    "description": skill_desc,
                    "icon_url": "",
                    "icon_filename": ""
                })
    
    # 提取物品 (Items)
    items_section = re.search(r'### Items(.*?)$', html_content, re.DOTALL)
    if items_section:
        items_text = items_section.group(1)
        
        # 提取物品名称
        # 物品名称通常在标题位置
        item_pattern = r'([A-Z][A-Za-z\s\']+?)(?:VAN|PYG|DOO|MAK|STE|JUL|\n)'
        item_matches = re.findall(item_pattern, items_text)
        
        for item_name in item_matches:
            item_name = item_name.strip()
            
            if item_name and len(item_name) < 50 and item_name not in ['Golden', 'Heavy', 'Icy', 'Turbo', 'Shielded']:
                # 查找该物品的描述
                item_desc_pattern = rf'{re.escape(item_name)}.*?\n.*?\n(.*?)(?:\n\n|\d+ enchantments|$)'
                desc_match = re.search(item_desc_pattern, items_text, re.DOTALL)
                
                item_desc = ""
                if desc_match:
                    item_desc = desc_match.group(1).strip()
                
                details["items"].append({
                    "name": item_name,
                    "description": item_desc,
                    "icon_url": "",
                    "icon_filename": ""
                })
    
    return details

def fetch_monster_details(monster_name, session):
    """获取单个怪物的详细信息"""
    print(f"\n处理: {monster_name}")
    
    # 步骤1: 获取详情页URL
    detail_url = get_monster_detail_url(monster_name, session)
    
    if not detail_url:
        print(f"  ✗ 无法找到详情页URL")
        return None
    
    print(f"  访问: {detail_url}")
    
    try:
        # 步骤2: 访问详情页
        response = session.get(detail_url, timeout=30)
        response.raise_for_status()
        
        # 步骤3: 提取详细信息
        details = extract_monster_details(response.text, monster_name)
        
        print(f"  ✓ 等级: {details['level']}, 血量: {details['health']}")
        print(f"  ✓ 找到 {len(details['skills'])} 个技能")
        print(f"  ✓ 找到 {len(details['items'])} 个物品")
        
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
    
    # 创建session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 获取每个怪物的详细信息
    print(f"\n[步骤2] 获取怪物详细信息")
    all_monsters_details = []
    
    # 只处理前3个怪物作为测试
    test_count = 3
    print(f"  (测试模式: 只处理前 {test_count} 个怪物)")
    
    for i, monster_name in enumerate(monster_names[:test_count], 1):
        print(f"\n[{i}/{test_count}] ", end="")
        
        details = fetch_monster_details(monster_name, session)
        
        if details:
            all_monsters_details.append(details)
    
    # 保存结果
    print(f"\n[步骤3] 保存结果")
    output_file = output_dir / 'monsters_details.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_monsters_details, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存到: {output_file}")
    
    # 统计信息
    total_skills = sum(len(m['skills']) for m in all_monsters_details)
    total_items = sum(len(m['items']) for m in all_monsters_details)
    
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"处理怪物数: {len(all_monsters_details)}")
    print(f"总技能数: {total_skills}")
    print(f"总物品数: {total_items}")
    print("=" * 80)

if __name__ == "__main__":
    main()
