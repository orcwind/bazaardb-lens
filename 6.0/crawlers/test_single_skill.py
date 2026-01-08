"""
单独测试抓取某个技能
用于调试失败的技能抓取
"""

import json
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 导入必要的函数
sys.path.insert(0, str(Path(__file__).parent))

from selenium_items_skills import (
    extract_card_data_from_search_page,
    parse_card_json_data,
    size_to_aspect_ratio,
    setup_driver
)
from utils_icon import download_icon

def test_skill(skill_name):
    """测试抓取单个技能"""
    print("=" * 80)
    print(f"测试抓取技能: {skill_name}")
    print("=" * 80)
    
    # 启动浏览器
    driver = setup_driver()
    
    try:
        print(f"\n[1/4] 访问搜索页面...")
        # 尝试多种URL格式
        url_variants = [
            skill_name.replace(' ', '+'),  # 原样
            skill_name.replace('-', '+'),  # 连字符转加号
            skill_name.replace('-', ' ').replace(' ', '+'),  # 连字符转空格再转加号
        ]
        
        for url_variant in url_variants:
            search_url = f"https://bazaardb.gg/search?q={url_variant}&c=skills"
            print(f"  尝试URL: {search_url}")
            driver.get(search_url)
            import time
            time.sleep(3)
            
            # 检查页面是否包含技能信息
            html = driver.page_source
            if 'initialData' in html and 'pageCards' in html:
                print(f"  ✓ 找到数据，使用此URL")
                break
            else:
                print(f"  ✗ 未找到数据")
        else:
            print(f"  ⚠ 所有URL格式都未找到数据")
        
        print(f"\n[2/4] 提取JSON数据...")
        card_json = extract_card_data_from_search_page(driver, skill_name, 'skills')
        
        if not card_json:
            print(f"  ✗ 未找到卡片数据")
            print(f"\n  调试信息:")
            print(f"  - 页面标题: {driver.title}")
            print(f"  - 当前URL: {driver.current_url}")
            
            # 检查页面内容
            html = driver.page_source
            if 'initialData' in html:
                print(f"  - 页面包含 'initialData'")
            else:
                print(f"  - 页面不包含 'initialData'")
            
            if 'pageCards' in html:
                print(f"  - 页面包含 'pageCards'")
            else:
                print(f"  - 页面不包含 'pageCards'")
            
            # 尝试查找技能名称
            if skill_name in html or skill_name.replace('-', ' ') in html:
                print(f"  - 页面包含技能名称")
            else:
                print(f"  - 页面不包含技能名称")
            
            # 保存HTML用于调试
            debug_html = Path(__file__).parent.parent.parent / "data" / "Json" / f"debug_{skill_name}.html"
            with open(debug_html, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  - HTML已保存到: {debug_html}")
            
            return
        
        print(f"  ✓ 成功提取JSON数据")
        print(f"  - JSON键: {list(card_json.keys())[:10]}...")
        
        print(f"\n[3/4] 解析JSON数据...")
        parsed_data = parse_card_json_data(card_json)
        
        if not parsed_data:
            print(f"  ✗ 解析失败")
            return
        
        print(f"  ✓ 解析成功")
        print(f"  - 英文名: {parsed_data.get('name', 'N/A')}")
        print(f"  - 中文名: {parsed_data.get('name_zh', 'N/A')}")
        print(f"  - 描述: {parsed_data.get('description_zh', 'N/A')[:50]}...")
        print(f"  - 图标URL: {parsed_data.get('icon_url', 'N/A')}")
        print(f"  - 尺寸: {parsed_data.get('size', 'N/A')}")
        
        print(f"\n[4/4] 下载图标...")
        icon_url = parsed_data.get('icon_url', '')
        if icon_url:
            icon_filename = download_icon(icon_url, parsed_data.get('name', skill_name), category='skill')
            if icon_filename:
                print(f"  ✓ 图标下载成功: {icon_filename}")
            else:
                print(f"  ✗ 图标下载失败")
        else:
            print(f"  ⚠ 没有图标URL")
        
        # 构建完整数据
        skill_data = {
            "name": parsed_data.get('name', skill_name),
            "name_zh": parsed_data.get('name_zh', ''),
            "description_zh": parsed_data.get('description_zh', ''),
            "icon": icon_filename if icon_url else "",
            "aspect_ratio": size_to_aspect_ratio(parsed_data.get('size')),
            "url": search_url
        }
        
        print(f"\n" + "=" * 80)
        print("抓取结果:")
        print("=" * 80)
        print(json.dumps(skill_data, ensure_ascii=False, indent=2))
        
        # 保存结果
        output_file = Path(__file__).parent.parent.parent / "data" / "Json" / f"test_{skill_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    skill_name = sys.argv[1] if len(sys.argv) > 1 else "Defensive-Stance"
    test_skill(skill_name)

