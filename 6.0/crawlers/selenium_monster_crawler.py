"""
使用Selenium获取怪物详细信息
包括技能、物品的名称、描述和图标
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


class MonsterDetailCrawler:
    """怪物详情爬虫"""
    
    def __init__(self, headless=False):
        """初始化"""
        self.base_url = "https://bazaardb.gg"
        self.headless = headless
        self.driver = None
        
        # 创建输出目录
        self.output_dir = Path('../data')
        self.html_dir = self.output_dir / 'html' / 'monsters'
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
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"      ✗ 下载失败: {e}")
            return False
    
    def extract_monster_details(self, monster_name, detail_url):
        """提取单个怪物的详细信息"""
        print(f"\n处理: {monster_name}")
        print(f"  访问: {detail_url}")
        
        try:
            # 访问详情页
            self.driver.get(detail_url)
            time.sleep(3)  # 等待页面加载
            
            # 保存HTML用于调试
            html_file = self.html_dir / f"{monster_name.replace(' ', '_')}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            details = {
                "name": monster_name,
                "url": detail_url,
                "level": "",
                "health": "",
                "skills": [],
                "items": []
            }
            
            # 提取等级
            try:
                level_elem = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Level')]/following-sibling::*//div")
                details["level"] = level_elem.text.strip()
            except:
                pass
            
            # 提取血量
            try:
                health_elem = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Health')]/following-sibling::*//div")
                details["health"] = health_elem.text.strip()
            except:
                pass
            
            print(f"  ✓ 等级: {details['level']}, 血量: {details['health']}")
            
            # 提取技能
            try:
                # 查找 "Skills" 标题后的所有卡片
                skills_section = self.driver.find_element(By.XPATH, "//h3[text()='Skills']/following-sibling::div[1]")
                skill_cards = skills_section.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
                
                for skill_card in skill_cards:
                    try:
                        # 技能名称
                        skill_name = skill_card.find_element(By.TAG_NAME, 'h3').text.strip()
                        
                        # 技能描述 - 在卡片内查找包含描述的div
                        try:
                            desc_elem = skill_card.find_element(By.XPATH, ".//following-sibling::div//div[contains(@class, '_bM')]")
                            skill_desc = desc_elem.text.strip()
                        except:
                            skill_desc = ""
                        
                        # 技能图标
                        try:
                            img = skill_card.find_element(By.CSS_SELECTOR, 'img[src*="/skill/"]')
                            icon_url = img.get_attribute('src')
                            icon_filename = icon_url.split('/')[-1].split('?')[0]
                        except:
                            icon_url = ""
                            icon_filename = ""
                        
                        if skill_name:
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
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"    提取技能失败: {e}")
            
            # 提取物品
            try:
                # 查找 "Items" 标题后的所有卡片
                items_section = self.driver.find_element(By.XPATH, "//h3[text()='Items']/following-sibling::div[1]")
                item_cards = items_section.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
                
                for item_card in item_cards:
                    try:
                        # 物品名称
                        item_name = item_card.find_element(By.TAG_NAME, 'h3').text.strip()
                        
                        # 物品描述
                        try:
                            desc_elem = item_card.find_element(By.XPATH, ".//following-sibling::div//div[contains(@class, '_bM')]")
                            item_desc = desc_elem.text.strip()
                        except:
                            item_desc = ""
                        
                        # 物品图标
                        try:
                            img = item_card.find_element(By.CSS_SELECTOR, 'img[src*="/item/"]')
                            icon_url = img.get_attribute('src')
                            icon_filename = icon_url.split('/')[-1].split('?')[0]
                        except:
                            icon_url = ""
                            icon_filename = ""
                        
                        if item_name:
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
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"    提取物品失败: {e}")
            
            print(f"  ✓ 共提取 {len(details['skills'])} 个技能, {len(details['items'])} 个物品")
            return details
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            return None
    
    def get_monster_urls_from_list(self):
        """从怪物列表页获取所有怪物的详情URL"""
        print("\n获取怪物列表...")
        url = f"{self.base_url}/search?c=monsters"
        print(f"  访问: {url}")
        
        self.driver.get(url)
        time.sleep(5)
        
        # 滚动加载所有怪物
        print("  滚动页面加载所有怪物...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # 提取所有怪物卡片链接
        monster_urls = {}
        cards = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/card/"]')
        
        for card in cards:
            try:
                href = card.get_attribute('href')
                # 提取怪物名称
                name = href.split('/')[-1].replace('-', ' ')
                monster_urls[name] = href
            except:
                continue
        
        print(f"  ✓ 找到 {len(monster_urls)} 个怪物")
        return monster_urls
    
    def crawl_monsters(self, monster_names=None, test_mode=True, test_count=3):
        """爬取怪物详细信息"""
        print("=" * 80)
        print("开始爬取怪物详细信息...")
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
            
            # 步骤2: 获取怪物详情URL
            print("\n[步骤2] 获取怪物详情URL")
            monster_urls = self.get_monster_urls_from_list()
            
            # 步骤3: 爬取详细信息
            print("\n[步骤3] 爬取怪物详细信息")
            
            if test_mode:
                print(f"  (测试模式: 只处理前 {test_count} 个怪物)")
                monster_names = monster_names[:test_count]
            
            all_details = []
            
            for i, monster_name in enumerate(monster_names, 1):
                print(f"\n[{i}/{len(monster_names)}] ", end="")
                
                # 查找对应的URL
                detail_url = None
                for url_name, url in monster_urls.items():
                    if url_name.lower() == monster_name.lower():
                        detail_url = url
                        break
                
                if not detail_url:
                    print(f"  ✗ 未找到 {monster_name} 的详情URL")
                    continue
                
                details = self.extract_monster_details(monster_name, detail_url)
                
                if details:
                    all_details.append(details)
                
                # 短暂延迟，避免请求过快
                time.sleep(1)
            
            # 步骤4: 保存结果
            print("\n[步骤4] 保存结果")
            output_file = self.output_dir / 'monsters_details.json'
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
    crawler = MonsterDetailCrawler(headless=False)
    
    # 运行爬虫（测试模式：只处理前3个怪物）
    crawler.crawl_monsters(test_mode=True, test_count=3)


if __name__ == "__main__":
    main()
