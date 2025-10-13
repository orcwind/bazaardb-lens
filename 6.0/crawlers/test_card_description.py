"""
测试脚本：查看最新的卡片详情页HTML结构，找到描述数据的位置
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def analyze_card_page(driver, card_url, card_name):
    """分析卡片详情页的HTML结构"""
    print(f"\n{'='*80}")
    print(f"分析卡片: {card_name}")
    print(f"URL: {card_url}")
    print('='*80)
    
    try:
        driver.get(card_url)
        print("等待页面加载...")
        time.sleep(3)
        
        html = driver.page_source
        
        # 保存完整HTML用于分析
        debug_file = f"debug_card_{card_name.replace(' ', '_')}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ HTML已保存到: {debug_file}")
        
        # 尝试多种可能的CSS类名
        print("\n查找可能包含描述的元素...")
        
        css_classes_to_try = [
            "_bM",      # 旧的类名
            "_dM",      # 可能的新类名
            "description",
            "card-description",
            "effect",
            "card-effect",
            ".effect-text",
            "[class*='desc']",
            "[class*='effect']",
            "[class*='text']"
        ]
        
        for css_class in css_classes_to_try:
            pattern = rf'<div class="{css_class}">(.*?)</div>'
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                print(f"\n✓ 找到匹配: class=\"{css_class}\"")
                print(f"  匹配数量: {len(matches)}")
                print(f"  第一个匹配内容:")
                clean_text = re.sub(r'<[^>]+>', '', matches[0]).strip()
                print(f"    {clean_text[:200]}")
                
        # 尝试查找所有包含描述关键词的div
        print("\n查找包含描述性文本的div...")
        div_pattern = r'<div[^>]*class="([^"]*)"[^>]*>(.*?)</div>'
        all_divs = re.findall(div_pattern, html, re.DOTALL)[:50]  # 只看前50个
        
        for class_name, content in all_divs:
            clean_content = re.sub(r'<[^>]+>', '', content).strip()
            # 查找可能是描述的文本（长度合适，包含游戏术语）
            if (len(clean_content) > 20 and 
                len(clean_content) < 500 and
                any(keyword in clean_content for keyword in ['Deal', 'Gain', 'When', 'Shield', 'Damage', 'Heal', 'Haste', 'Slow'])):
                print(f"\n可能的描述:")
                print(f"  class=\"{class_name}\"")
                print(f"  内容: {clean_content[:150]}")
                
    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数 - 测试几个卡片"""
    print("="*80)
    print("卡片描述提取分析")
    print("="*80)
    
    # 测试几个不同的卡片
    test_cards = [
        ("Crypto", "https://bazaardb.gg/card/255tcgdd4x1fr53511c37huj6/Crypto"),
        ("Solar Farm", "https://bazaardb.gg/card/51g0gtqc0vq5suyn68fgujtd9/Solar-Farm"),
    ]
    
    driver = setup_driver()
    
    try:
        for card_name, card_url in test_cards:
            analyze_card_page(driver, card_url, card_name)
            time.sleep(2)
        
        print(f"\n{'='*80}")
        print("分析完成！")
        print('='*80)
        print("\n下一步:")
        print("1. 查看生成的 debug_card_*.html 文件")
        print("2. 搜索卡片描述内容（如'Deal', 'Gain', 'When'等关键词）")
        print("3. 找出描述所在的CSS类名")
        print("4. 更新 get_card_description() 函数")
        print('='*80)
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()


