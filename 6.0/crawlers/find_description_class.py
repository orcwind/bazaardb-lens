"""
查找描述所在的CSS类名
"""

import re
import time
from selenium import webdriver


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def find_description_class(driver, card_url, expected_desc_keyword):
    """查找包含描述的CSS类名
    
    Args:
        card_url: 卡片详情页URL
        expected_desc_keyword: 描述中应该包含的关键词（用于验证）
    """
    print(f"\n访问: {card_url}")
    driver.get(card_url)
    time.sleep(5)  # 等待页面完全加载
    
    html = driver.page_source
    
    # 保存HTML用于分析
    with open('current_card_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✓ HTML已保存到: current_card_page.html")
    
    # 方法1: 查找所有可能的CSS类名
    print(f"\n方法1: 查找包含关键词'{expected_desc_keyword}'的div...")
    
    # 提取所有div的class和内容
    div_pattern = r'<div[^>]*class="([^"]*)"[^>]*>(.*?)</div>'
    matches = re.findall(div_pattern, html, re.DOTALL)
    
    found_classes = []
    for class_name, content in matches:
        clean_content = re.sub(r'<[^>]+>', '', content).strip()
        if expected_desc_keyword.lower() in clean_content.lower():
            print(f"\n✓ 找到匹配:")
            print(f"  CSS类名: {class_name}")
            print(f"  内容: {clean_content[:150]}")
            found_classes.append(class_name)
    
    # 方法2: 从渲染后的页面获取文本
    print(f"\n方法2: 从渲染后的页面获取文本...")
    page_text = driver.execute_script("return document.body.innerText;")
    
    if expected_desc_keyword.lower() in page_text.lower():
        print(f"✓ 页面文本中包含关键词'{expected_desc_keyword}'")
        
        # 找到包含关键词的行
        lines = page_text.split('\n')
        for line in lines:
            if expected_desc_keyword.lower() in line.lower():
                print(f"  描述行: {line.strip()}")
                break
    else:
        print(f"✗ 页面文本中未找到关键词'{expected_desc_keyword}'")
    
    # 方法3: 使用JavaScript查询所有可能的元素
    print(f"\n方法3: 使用JavaScript查询所有div...")
    script = """
    const allDivs = Array.from(document.querySelectorAll('div'));
    const keyword = arguments[0].toLowerCase();
    const matches = allDivs
        .filter(div => div.textContent && div.textContent.toLowerCase().includes(keyword))
        .map(div => ({
            class: div.className,
            text: div.innerText.substring(0, 200),
            tagName: div.tagName
        }));
    return matches.slice(0, 5); // 只返回前5个
    """
    
    try:
        js_matches = driver.execute_script(script, expected_desc_keyword)
        if js_matches:
            print(f"✓ JavaScript找到 {len(js_matches)} 个匹配:")
            for match in js_matches:
                print(f"\n  class=\"{match['class']}\"")
                print(f"  内容: {match['text'][:150]}")
        else:
            print(f"✗ JavaScript未找到匹配")
    except Exception as e:
        print(f"✗ JavaScript执行失败: {e}")
    
    return found_classes


def main():
    """主函数"""
    print("="*80)
    print("查找描述所在的CSS类名")
    print("="*80)
    
    # 测试Crypto卡片（已知描述：At the start of each hour）
    test_cases = [
        ("Crypto", "https://bazaardb.gg/card/255tcgdd4x1fr53511c37huj6/Crypto", "At the start"),
        ("Healthy Jolt", "https://bazaardb.gg/card/6r8afpa0mffhx4qyiaf7fjb9i/Healthy-Jolt", "Over-Heal"),
    ]
    
    driver = setup_driver()
    
    try:
        all_classes = []
        
        for card_name, card_url, keyword in test_cases:
            print(f"\n{'='*80}")
            print(f"测试卡片: {card_name}")
            print(f"关键词: {keyword}")
            print('='*80)
            
            classes = find_description_class(driver, card_url, keyword)
            all_classes.extend(classes)
            time.sleep(2)
        
        # 总结
        print(f"\n{'='*80}")
        print("总结")
        print('='*80)
        
        if all_classes:
            unique_classes = list(set(all_classes))
            print(f"\n发现 {len(unique_classes)} 个可能的CSS类名:")
            for cls in unique_classes:
                print(f"  - {cls}")
            
            print(f"\n建议:")
            print(f"1. 查看 current_card_page.html 文件")
            print(f"2. 搜索关键词找到描述位置")
            print(f"3. 更新 get_card_description() 函数中的CSS选择器")
        else:
            print(f"\n未找到匹配的CSS类名")
            print(f"建议使用方法2：从document.body.innerText提取文本")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()


