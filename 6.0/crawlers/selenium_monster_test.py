"""
Selenium怪物爬虫 - 测试版（只处理3个怪物）
使用Selenium获取怪物详细信息
"""

import json
import time
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # 不使用无头模式，方便观察
    # options.add_argument('--headless')
    
    driver = webdriver.Chrome(options=options)
    return driver


def get_monster_detail_url(driver, monster_name):
    """
    从搜索页获取怪物详情页URL
    """
    print(f"\n  [1/2] 搜索怪物: {monster_name}")
    
    # 访问搜索页
    search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
    driver.get(search_url)
    
    # 等待页面加载
    time.sleep(3)
    
    try:
        # 查找第一个卡片链接
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        detail_url = card_link.get_attribute('href')
        print(f"  ✓ 找到详情页: {detail_url}")
        return detail_url
    except NoSuchElementException:
        print(f"  ✗ 未找到怪物: {monster_name}")
        return None


def extract_monster_details(driver, monster_name, detail_url):
    """
    从详情页提取怪物信息
    """
    print(f"\n  [2/2] 提取详细信息...")
    
    # 访问详情页
    driver.get(detail_url)
    
    # 等待页面加载
    time.sleep(5)
    
    monster_data = {
        "name": monster_name,
        "url": detail_url,
        "skills": [],
        "items": []
    }
    
    try:
        # 获取页面HTML源代码
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取技能
        try:
            # 查找Skills标题后的内容（到Items标题为止）
            skills_section = re.search(r'<h3>Skills</h3>(.*?)<h3>Items</h3>', html_content, re.DOTALL)
            if skills_section:
                skills_html = skills_section.group(1)
                
                # 简化：只提取名称、URL和图标
                # 查找所有 aria-label="See details for XXX" 的链接
                skill_matches = re.finditer(
                    r'<a[^>]*aria-label="See details for ([^"]+)"[^>]*href="(/card/[^"]+)"[^>]*>',
                    skills_html
                )
                
                skills_found = []
                for match in skill_matches:
                    skill_name = match.group(1)
                    skill_url = match.group(2)
                    
                    # 在该链接附近查找图标（查找后续500字符内的图标）
                    start_pos = match.end()
                    nearby_html = skills_html[start_pos:start_pos+500]
                    icon_match = re.search(r'<img[^>]*src="(https://s\.bazaardb\.gg/v0/z5\.0\.0/skill/[^"]+)"', nearby_html)
                    skill_icon = icon_match.group(1) if icon_match else None
                    
                    skills_found.append({
                        "name": skill_name,
                        "url": f"https://bazaardb.gg{skill_url}",
                        "icon": skill_icon,
                        "description": ""  # 暂时为空
                    })
                
                print(f"    找到 {len(skills_found)} 个技能")
                for skill in skills_found:
                    monster_data["skills"].append(skill)
                    print(f"      ✓ 技能: {skill['name']}")
            else:
                print(f"    ✗ 未找到Skills部分")
        
        except Exception as e:
            print(f"    ✗ 提取技能部分失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 提取掉落物品
        try:
            # 查找Items标题后的内容（到页面底部）
            items_section = re.search(r'<h3>Items</h3>(.*?)<div class="_ab"></div>', html_content, re.DOTALL)
            if items_section:
                items_html = items_section.group(1)
                
                # 简化：只提取名称、URL和图标
                # 查找所有 aria-label="See details for XXX" 的链接
                item_matches = re.finditer(
                    r'<a[^>]*aria-label="See details for ([^"]+)"[^>]*href="(/card/[^"]+)"[^>]*>',
                    items_html
                )
                
                items_found = []
                for match in item_matches:
                    item_name = match.group(1)
                    item_url = match.group(2)
                    
                    # 在该链接附近查找图标（查找后续500字符内的图标）
                    start_pos = match.end()
                    nearby_html = items_html[start_pos:start_pos+500]
                    icon_match = re.search(r'<img[^>]*src="(https://s\.bazaardb\.gg/v0/z5\.0\.0/item/[^"]+)"', nearby_html)
                    item_icon = icon_match.group(1) if icon_match else None
                    
                    items_found.append({
                        "name": item_name,
                        "url": f"https://bazaardb.gg{item_url}",
                        "icon": item_icon,
                        "description": ""  # 暂时为空
                    })
                
                print(f"    找到 {len(items_found)} 个物品")
                for item in items_found:
                    monster_data["items"].append(item)
                    print(f"      ✓ 物品: {item['name']}")
            else:
                print(f"    ✗ 未找到Items部分")
        
        except Exception as e:
            print(f"    ✗ 提取物品部分失败: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"  ✗ 提取详情失败: {e}")
        import traceback
        traceback.print_exc()
    
    return monster_data


def main():
    """主函数"""
    print("=" * 80)
    print("Selenium怪物爬虫测试 - 只处理前3个怪物")
    print("=" * 80)
    
    # 读取怪物列表
    monsters_file = 'unique_monsters.json'
    
    if not os.path.exists(monsters_file):
        print(f"\n✗ 错误: 找不到文件 {monsters_file}")
        return
    
    # 读取怪物名称
    with open(monsters_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        monster_names = [line.strip().strip('"') for line in lines if line.strip()]
    
    # 只处理前3个
    monster_names = monster_names[:3]
    
    print(f"\n将测试 {len(monster_names)} 个怪物:")
    for i, name in enumerate(monster_names, 1):
        print(f"  {i}. {name}")
    
    # 设置输出目录
    output_dir = Path('monster_details_test')
    output_dir.mkdir(exist_ok=True)
    
    # 启动浏览器
    print("\n启动浏览器...")
    driver = setup_driver()
    
    try:
        all_monsters = []
        
        for i, monster_name in enumerate(monster_names, 1):
            print(f"\n{'=' * 80}")
            print(f"[{i}/{len(monster_names)}] 处理: {monster_name}")
            print('=' * 80)
            
            try:
                # 获取详情页URL
                detail_url = get_monster_detail_url(driver, monster_name)
                
                if not detail_url:
                    print(f"  ✗ 跳过: {monster_name}")
                    continue
                
                # 提取详细信息
                monster_data = extract_monster_details(driver, monster_name, detail_url)
                all_monsters.append(monster_data)
                
                # 显示摘要
                print(f"\n  摘要:")
                print(f"    技能数: {len(monster_data['skills'])}")
                print(f"    物品数: {len(monster_data['items'])}")
                
            except Exception as e:
                print(f"\n  ✗ 处理失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 保存结果
        output_file = output_dir / 'monsters_test.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_monsters, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        print(f"\n✓ 成功处理 {len(all_monsters)} 个怪物")
        print(f"✓ 结果已保存到: {output_file}")
        
        # 显示统计
        total_skills = sum(len(m['skills']) for m in all_monsters)
        total_items = sum(len(m['items']) for m in all_monsters)
        print(f"\n统计:")
        print(f"  总技能数: {total_skills}")
        print(f"  总物品数: {total_items}")
        
    finally:
        print("\n关闭浏览器...")
        driver.quit()


if __name__ == "__main__":
    main()
