"""为怪物列表获取中文名称"""
import json
import time
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import unquote

def is_chinese(text):
    """检查文本是否包含中文字符"""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def setup_driver():
    """设置Chrome驱动，强制使用中文语言"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # 强制设置语言为中文
    options.add_argument('--lang=zh-CN')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'zh-CN,zh'
    })
    
    return webdriver.Chrome(options=options)

def extract_chinese_name_from_html(html, monster_name):
    """从HTML中提取中文名称"""
    # 方法1: 从Title.Text字段提取（中文名称）
    # 查找 "Type":"CombatEncounter" 和 "_originalTitleText" 匹配怪物名称的JSON对象
    # 然后提取 "Title":{"Text":"中文名称"}
    
    # 准备转义后的怪物名称（用于匹配）
    escaped_monster_name = re.escape(monster_name.replace(" ", "-"))
    
    # 先尝试转义版本（在原始字符串中，需要正确转义花括号）
    escaped_pattern = r'\\"Type\\":\\"CombatEncounter\\"[^}]*?\\"_originalTitleText\\":\\"' + escaped_monster_name + r'\\"[^}]*?\\"Title\\":\s*\{\s*\\"Text\\":\s*\\"([^"]+)\\"'
    match = re.search(escaped_pattern, html, re.DOTALL)
    if match:
        chinese_name = match.group(1)
        # 处理转义字符
        from html import unescape
        chinese_name = unescape(chinese_name)
        if is_chinese(chinese_name):
            return chinese_name
    
    # 方法2: 未转义版本
    pattern = r'"Type"\s*:\s*"CombatEncounter"[^}]*?"_originalTitleText"\s*:\s*"' + escaped_monster_name + r'"[^}]*?"Title"\s*:\s*\{\s*"Text"\s*:\s*"([^"]+)"'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        chinese_name = match.group(1)
        if is_chinese(chinese_name):
            return chinese_name
    
    # 方法3: 从页面标题或h1标签提取
    h1_pattern = r'<h1[^>]*>(.*?)</h1>'
    h1_match = re.search(h1_pattern, html, re.DOTALL)
    if h1_match:
        title_text = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        if title_text and is_chinese(title_text):
            return title_text
    
    return None

def fetch_monster_chinese_name(driver, monster_name):
    """获取单个怪物的中文名称"""
    # 构建搜索URL（使用英文名称）
    search_url = f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
    
    try:
        # 设置Accept-Language header强制使用中文
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": driver.execute_script("return navigator.userAgent;"),
            "acceptLanguage": "zh-CN,zh;q=0.9"
        })
        
        driver.get(search_url)
        time.sleep(3)  # 等待页面加载
        
        # 尝试通过JavaScript设置语言偏好
        driver.execute_script("""
            if (window.localStorage) {
                localStorage.setItem('language', 'zh');
                localStorage.setItem('locale', 'zh-CN');
            }
        """)
        
        # 重新加载页面以应用语言设置
        driver.refresh()
        time.sleep(2)
        
        html = driver.page_source
        
        # 提取中文名称
        chinese_name = extract_chinese_name_from_html(html, monster_name)
        
        return chinese_name
        
    except Exception as e:
        print(f"      ✗ 获取 {monster_name} 失败: {e}")
        return None

def main():
    """主函数：为所有怪物获取中文名称"""
    # 读取怪物列表
    monsters_list_file = Path(__file__).parent.parent.parent / "data" / "Json" / "monsters_only_list.json"
    if not monsters_list_file.exists():
        print(f"错误: 文件不存在: {monsters_list_file}")
        return
    
    with open(monsters_list_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        # 处理JSON Lines格式（每行一个字符串）
        if content.startswith('"'):
            # 如果是JSON Lines格式，逐行解析
            monsters = []
            for line in content.split('\n'):
                line = line.strip()
                if line and line.startswith('"') and line.endswith('"'):
                    monsters.append(json.loads(line))
        else:
            # 标准JSON数组格式
            monsters = json.load(f)
    
    print(f"找到 {len(monsters)} 个怪物")
    
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
    
    # 设置驱动
    driver = setup_driver()
    
    results = []
    success_count = 0
    fail_count = 0
    
    try:
        for i, monster_name in enumerate(monsters, 1):
            print(f"\n[{i}/{len(monsters)}] 处理: {monster_name}")
            
            # 检查是否已有中文名称
            if monster_name in existing_monsters:
                existing = existing_monsters[monster_name]
                if existing.get('name_zh'):
                    print(f"  ⊙ 已有中文名称: {existing['name_zh']}")
                    results.append(existing)
                    success_count += 1
                    continue
            
            # 获取中文名称
            chinese_name = fetch_monster_chinese_name(driver, monster_name)
            
            if chinese_name:
                print(f"  ✓ 中文名称: {chinese_name}")
                monster_data = {
                    "name": monster_name,
                    "name_zh": chinese_name,
                    "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
                }
                results.append(monster_data)
                success_count += 1
            else:
                print(f"  ✗ 未找到中文名称")
                # 即使没有中文名称，也保存基本信息
                monster_data = {
                    "name": monster_name,
                    "name_zh": "",
                    "url": f"https://bazaardb.gg/search?q={monster_name.replace(' ', '+')}&c=monsters"
                }
                results.append(monster_data)
                fail_count += 1
            
            # 避免请求过快
            time.sleep(1)
    
    finally:
        driver.quit()
    
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

