"""
下载怪物图标脚本
从monsters.json读取怪物列表，访问每个怪物的详情页，提取并下载icon到data/icon/monster/文件夹
"""

import json
import re
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# 配置路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MONSTERS_JSON = PROJECT_ROOT / "data" / "Json" / "monsters.json"
ICON_DIR = PROJECT_ROOT / "data" / "icon" / "monster"

# 确保icon目录存在
ICON_DIR.mkdir(parents=True, exist_ok=True)


def setup_driver():
    """设置Selenium WebDriver"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"✗ 创建WebDriver失败: {e}")
        print("请确保已安装Chrome浏览器和ChromeDriver")
        return None


def get_monster_card_url(driver, monster_name, search_url):
    """从搜索页面获取怪物的card URL"""
    try:
        driver.get(search_url)
        time.sleep(3)
        
        # 查找第一个card链接
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        card_url = card_link.get_attribute('href')
        print(f"    ✓ 找到card URL: {card_url}")
        return card_url
    except NoSuchElementException:
        print(f"    ✗ 未找到怪物card URL: {monster_name}")
        return None
    except Exception as e:
        print(f"    ✗ 获取card URL失败: {e}")
        return None


def extract_monster_icon_url(driver, html_content):
    """从HTML中提取怪物icon URL
    
    方法：
    1. 使用Selenium查找特定的CSS类（参考monster_crawler.js）
    2. 使用Selenium查找img标签
    3. 使用正则表达式查找URL模式
    """
    # 方法1: 查找img._au（角色形象图，参考monster_crawler.js）
    try:
        time.sleep(2)
        
        # 尝试查找img._au（角色形象图）
        try:
            char_img = driver.find_element(By.CSS_SELECTOR, 'img._au')
            src = char_img.get_attribute('src')
            if src:
                print(f"      找到icon URL (方法1-img._au): {src[:80]}...")
                return src
        except:
            pass
        
        # 方法2: 查找div._at的背景图
        try:
            bg_div = driver.find_element(By.CSS_SELECTOR, 'div._at')
            bg_image = bg_div.value_of_css_property('background-image')
            if bg_image and 'url(' in bg_image:
                # 提取URL
                import re
                match = re.search(r'url\(["\']?(.*?)["\']?\)', bg_image)
                if match:
                    src = match.group(1)
                    print(f"      找到icon URL (方法2-div._at背景): {src[:80]}...")
                    return src
        except:
            pass
        
        # 方法3: 查找主要的card图片（通常在页面顶部的大图）
        selectors = [
            'img[src*="@256.webp"]',  # 包含@256.webp的图片
            'img[src*="s.bazaardb.gg"]',  # bazaardb图片
            '.card img',  # card类中的img
            'main img',  # main标签中的img
            'header img',  # header标签中的img
        ]
        
        for selector in selectors:
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for img in img_elements:
                    src = img.get_attribute('src')
                    if src and '@256.webp' in src:
                        # 排除skill和item
                        if '/skill/' not in src and '/item/' not in src:
                            print(f"      找到icon URL (方法3-Selenium): {src[:80]}...")
                            return src
            except:
                continue
    except Exception as e:
        print(f"      Selenium查找失败: {e}")
    
    # 方法2: 使用正则表达式查找
    patterns = [
        # monster格式
        r'https://s\.bazaardb\.gg/v0/[^/]+/monster/([a-f0-9]+)@256\.webp[^"]*',
        # combatencounter格式
        r'https://s\.bazaardb\.gg/v0/[^/]+/combatencounter/([a-f0-9]+)@256\.webp[^"]*',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            icon_hash = matches[0]
            icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/monster/{icon_hash}@256.webp?v=0"
            print(f"      找到icon URL (方法2-正则): {icon_url}")
            return icon_url
    
    # 方法3: 查找所有@256.webp的URL，排除skill和item
    general_pattern = r'(https://s\.bazaardb\.gg/v0/[^/]+/([^/]+)/([a-f0-9]+)@256\.webp[^"]*)'
    all_matches = re.findall(general_pattern, html_content)
    
    for full_url, card_type, icon_hash in all_matches:
        if card_type.lower() not in ['skill', 'item']:
            print(f"      找到icon URL (方法3-通用): {full_url[:80]}...")
            return full_url
    
    print(f"      ✗ 未找到icon URL")
    return None


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
    """加载怪物列表"""
    if not MONSTERS_JSON.exists():
        print(f"✗ 文件不存在: {MONSTERS_JSON}")
        return []
    
    try:
        with open(MONSTERS_JSON, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
        print(f"✓ 加载了 {len(monsters)} 个怪物")
        return monsters
    except Exception as e:
        print(f"✗ 加载怪物列表失败: {e}")
        return []


def main():
    """主函数"""
    print("=" * 80)
    print("开始下载怪物图标")
    print("=" * 80)
    
    # 加载怪物列表
    monsters = load_monsters()
    if not monsters:
        return
    
    # 设置WebDriver
    driver = setup_driver()
    if not driver:
        return
    
    try:
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for idx, monster in enumerate(monsters, 1):
            monster_name = monster.get('name', '')
            search_url = monster.get('url', '')
            
            if not monster_name or not search_url:
                print(f"\n[{idx}/{len(monsters)}] 跳过（缺少名称或URL）")
                skip_count += 1
                continue
            
            print(f"\n[{idx}/{len(monsters)}] {monster_name}")
            
            # 检查是否已存在
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', monster_name)
            icon_file = ICON_DIR / f"{safe_name}.webp"
            if icon_file.exists():
                print(f"  ✓ 图标已存在，跳过")
                skip_count += 1
                continue
            
            # 获取card URL
            print(f"  获取card URL...")
            card_url = get_monster_card_url(driver, monster_name, search_url)
            if not card_url:
                fail_count += 1
                continue
            
            # 访问card页面
            print(f"  访问card页面...")
            driver.get(card_url)
            time.sleep(3)
            
            html_content = driver.page_source
            
            # 提取icon URL
            print(f"  提取icon URL...")
            icon_url = extract_monster_icon_url(driver, html_content)
            
            # 下载icon
            if icon_url:
                print(f"  下载icon...")
                if download_icon(icon_url, monster_name):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        
        print("\n" + "=" * 80)
        print("下载完成！")
        print("=" * 80)
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")
        print(f"跳过: {skip_count} 个")
        print(f"总计: {len(monsters)} 个")
        print(f"\n图标保存位置: {ICON_DIR}")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    # 支持测试模式
    import sys
    TEST_MODE = '--test' in sys.argv or '-t' in sys.argv
    
    if TEST_MODE:
        print("测试模式：只处理前3个怪物")
        # 在main函数中添加测试逻辑
        pass
    
    main()

