"""
从 The Bazaar Wiki 获取怪物详细信息
Wiki网站结构更清晰，更容易解析
"""

import time
import json
import os
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class WikiMonsterCrawler:
    """Wiki怪物爬虫"""
    
    def __init__(self, headless=False):
        """初始化"""
        self.base_url = "https://thebazaar.wiki.gg/wiki"
        self.headless = headless
        self.driver = None
        
        # 创建输出目录
        self.output_dir = Path('../data')
        self.html_dir = self.output_dir / 'html' / 'monsters_wiki'
        self.icons_dir = self.output_dir / 'icons'
        self.skills_icons_dir = self.icons_dir / 'skills'
        self.items_icons_dir = self.icons_dir / 'items'
        
        for dir_path in [self.html_dir, self.skills_icons_dir, self.items_icons_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def init_driver(self):
        """初始化浏览器"""
        print("\n初始化浏览器...")
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        if self.headless:
            options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(60)
        print("  ✓ 浏览器已启动")
    
    def download_icon(self, url, save_path):
        """下载图标"""
        try:
            if os.path.exists(save_path):
                return True
            
            # 如果URL是相对路径，补全为绝对路径
            if url.startswith('/'):
                url = f"https://thebazaar.wiki.gg{url}"
            elif not url.startswith('http'):
                url = f"https://thebazaar.wiki.gg/wiki/{url}"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"      ✗ 下载失败: {e}")
            return False
    
    def extract_monster_details(self, monster_name):
        """提取单个怪物的详细信息"""
        # Wiki URL格式
        wiki_url = f"{self.base_url}/{monster_name.replace(' ', '_')}"
        
        print(f"\n处理: {monster_name}")
        print(f"  访问: {wiki_url}")
        
        try:
            # 访问Wiki页面
            self.driver.get(wiki_url)
            time.sleep(3)  # 等待页面加载
            
            # 保存HTML用于调试
            html_file = self.html_dir / f"{monster_name.replace(' ', '_')}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            details = {
                "name": monster_name,
                "url": wiki_url,
                "level": "",
                "health": "",
                "skills": [],
                "items": []
            }
            
            # 提取技能
            try:
                # 查找技能表格或列表
                skill_elements = self.driver.find_elements(By.XPATH, "//h2[contains(., 'Skill')]/..//following-sibling::*//a[contains(@href, '/wiki/')]")
                
                for skill_elem in skill_elements:
                    try:
                        skill_name = skill_elem.text.strip()
                        
                        # 查找技能描述（通常在同一行或下一行）
                        parent = skill_elem.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div")
                        skill_desc = parent.text.strip()
                        
                        # 查找技能图标
                        try:
                            img = skill_elem.find_element(By.XPATH, ".//preceding::img[1] | .//following::img[1]")
                            icon_url = img.get_attribute('src')
                            icon_filename = icon_url.split('/')[-1].split('?')[0]
                        except:
                            icon_url = ""
                            icon_filename = ""
                        
                        if skill_name and len(skill_name) < 50:
                            details["skills"].append({
                                "name": skill_name,
                                "description": skill_desc,
                                "icon_url": icon_url,
                                "icon_filename": icon_filename
                            })
                            
                            # 下载图标
                            if icon_url and icon_filename:
                                icon_path = self.skills_icons_dir / icon_filename
                                if self.download_icon(icon_url, str(icon_path)):
                                    print(f"    ✓ 技能: {skill_name}")
                    except:
                        continue
                
            except Exception as e:
                print(f"    提取技能失败: {e}")
            
            # 提取物品
            try:
                # 查找物品表格或列表
                item_elements = self.driver.find_elements(By.XPATH, "//h2[contains(., 'Item')]/..//following-sibling::*//a[contains(@href, '/wiki/')]")
                
                for item_elem in item_elements:
                    try:
                        item_name = item_elem.text.strip()
                        
                        # 查找物品描述
                        parent = item_elem.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div")
                        item_desc = parent.text.strip()
                        
                        # 查找物品图标
                        try:
                            img = item_elem.find_element(By.XPATH, ".//preceding::img[1] | .//following::img[1]")
                            icon_url = img.get_attribute('src')
                            icon_filename = icon_url.split('/')[-1].split('?')[0]
                        except:
                            icon_url = ""
                            icon_filename = ""
                        
                        if item_name and len(item_name) < 50:
                            details["items"].append({
                                "name": item_name,
                                "description": item_desc,
                                "icon_url": icon_url,
                                "icon_filename": icon_filename
                            })
                            
                            # 下载图标
                            if icon_url and icon_filename:
                                icon_path = self.items_icons_dir / icon_filename
                                if self.download_icon(icon_url, str(icon_path)):
                                    print(f"    ✓ 物品: {item_name}")
                    except:
                        continue
                
            except Exception as e:
                print(f"    提取物品失败: {e}")
            
            print(f"  ✓ 共提取 {len(details['skills'])} 个技能, {len(details['items'])} 个物品")
            return details
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def crawl_monsters(self, monster_names=None, test_mode=True, test_count=3):
        """爬取怪物详细信息"""
        print("=" * 80)
        print("从 The Bazaar Wiki 爬取怪物详细信息...")
        print("=" * 80)
        
        try:
            # 初始化浏览器
            self.init_driver()
            
            # 步骤1: 读取怪物清单
            if not monster_names:
                print("\n[步骤1] 读取怪物清单")
                with open('unique_monsters.json', 'r', encoding='utf-8') as f:
                    monster_names = [line.strip().strip('"') for line in f if line.strip()]
                print(f"  ✓ 读取到 {len(monster_names)} 个怪物")
            
            # 步骤2: 爬取详细信息
            print("\n[步骤2] 爬取怪物详细信息")
            
            if test_mode:
                print(f"  (测试模式: 只处理前 {test_count} 个怪物)")
                monster_names = monster_names[:test_count]
            
            all_details = []
            
            for i, monster_name in enumerate(monster_names, 1):
                print(f"\n[{i}/{len(monster_names)}] ", end="")
                
                details = self.extract_monster_details(monster_name)
                
                if details:
                    all_details.append(details)
                
                # 短暂延迟，避免请求过快
                time.sleep(1)
            
            # 步骤3: 保存结果
            print("\n[步骤3] 保存结果")
            output_file = self.output_dir / 'monsters_details_wiki.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_details, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ 已保存到: {output_file}")
            
            # 统计信息
            total_skills = sum(len(m['skills']) for m in all_details)
            total_items = sum(len(m['items']) for m in all_details)
            
            print("\n" + "=" * 80)
            print("完成！")
            print("=" * 80)
            print(f"处理怪物数: {len(all_details)}")
            print(f"总技能数: {total_skills}")
            print(f"总物品数: {total_items}")
            print(f"HTML保存在: {self.html_dir}")
            print(f"图标保存在: {self.icons_dir}")
            print("=" * 80)
            
            return all_details
            
        finally:
            if self.driver:
                print("\n关闭浏览器...")
                self.driver.quit()


def main():
    """主函数"""
    # 创建爬虫实例
    crawler = WikiMonsterCrawler(headless=False)
    
    # 运行爬虫（测试模式：只处理前3个怪物）
    crawler.crawl_monsters(test_mode=True, test_count=3)


if __name__ == "__main__":
    main()
