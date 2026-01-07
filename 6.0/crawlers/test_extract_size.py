"""
测试脚本：验证从卡片详情页提取尺寸信息的方法
目标：测试 Ahexa 的4个物品，验证尺寸提取
"""

import time
import re
from selenium import webdriver


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def extract_card_size(html):
    """从HTML中提取卡片尺寸
    
    Returns:
        尺寸字符串 (Small/Medium/Large) 或 None
    """
    # 尝试多种正则表达式模式
    size_patterns = [
        r'<span[^>]*>\s*(Small|Medium|Large)\s*</span>',
        r'<div[^>]*>\s*(Small|Medium|Large)\s*</div>',
        r'"size"\s*:\s*"(Small|Medium|Large)"',
        r'Size["\s:]*(["\s]*)(Small|Medium|Large)',
        r'class="[^"]*"[^>]*>\s*(Small|Medium|Large)\s*<',
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            # 返回第一个捕获组（尺寸）
            groups = match.groups()
            for group in groups:
                if group and group.strip() in ['Small', 'Medium', 'Large', 'small', 'medium', 'large']:
                    return group.capitalize()
    
    return None


def size_to_aspect_ratio(size):
    """将尺寸转换为长宽比
    
    正确映射:
    - Small = 0.5:1 (竖长)
    - Medium = 1:1 (正方形)
    - Large = 1.5:1 (横长)
    """
    if not size:
        return 1.0
    
    size_upper = size.upper()
    if size_upper == 'SMALL':
        return 0.5
    elif size_upper == 'MEDIUM':
        return 1.0
    elif size_upper == 'LARGE':
        return 1.5
    else:
        return 1.0


def test_card(driver, card_name, card_url, expected_size=None):
    """测试单个卡片"""
    print(f"\n{'='*70}")
    print(f"测试: {card_name}")
    print(f"URL: {card_url}")
    if expected_size:
        print(f"期望尺寸: {expected_size}")
    print('='*70)
    
    try:
        driver.get(card_url)
        print("  等待页面加载...")
        time.sleep(3)
        
        html = driver.page_source
        
        # 提取尺寸
        size = extract_card_size(html)
        aspect_ratio = size_to_aspect_ratio(size)
        
        # 显示结果
        if size:
            print(f"  ✓ 提取成功:")
            print(f"    尺寸: {size}")
            print(f"    长宽比: {aspect_ratio}")
            
            if expected_size:
                if size.upper() == expected_size.upper():
                    print(f"    ✓ 与期望值匹配")
                else:
                    print(f"    ✗ 期望 {expected_size}，实际 {size}")
        else:
            print(f"  ✗ 未提取到尺寸信息")
            
            # 保存HTML用于调试
            debug_file = f"debug_{card_name.replace(' ', '_')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  ℹ HTML已保存到: {debug_file}")
        
        return size, aspect_ratio
        
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return None, 1.0


def main():
    """主函数"""
    print("="*80)
    print("卡片尺寸提取测试")
    print("="*80)
    print("\n目标: 验证 Ahexa 的4个物品的尺寸提取")
    print("\n尺寸 → 长宽比映射:")
    print("  Small  → 0.5:1 (竖长)")
    print("  Medium → 1:1 (正方形)")
    print("  Large  → 1.5:1 (横长)")
    
    # Ahexa 的4个物品及其预期尺寸
    test_cards = [
        ("Crypto", "https://bazaardb.gg/card/255tcgdd4x1fr53511c37huj6/Crypto", "Small"),
        ("Rapid Injection System", "https://bazaardb.gg/card/7u0davdxb5pm7jrp84t807k9r/Rapid-Injection-System", "Medium"),
        ("Solar Farm", "https://bazaardb.gg/card/51g0gtqc0vq5suyn68fgujtd9/Solar-Farm", "Large"),
        ("Virus", "https://bazaardb.gg/card/4cgtbdq79tjkmz99gbl71i1x/Virus", "Small"),
    ]
    
    driver = setup_driver()
    results = []
    
    try:
        for card_name, card_url, expected_size in test_cards:
            size, aspect_ratio = test_card(driver, card_name, card_url, expected_size)
            results.append({
                'name': card_name,
                'size': size,
                'aspect_ratio': aspect_ratio,
                'expected': expected_size
            })
        
        # 总结
        print(f"\n{'='*80}")
        print("测试总结")
        print('='*80)
        
        success_count = 0
        for r in results:
            status = "✓" if r['size'] and r['size'].upper() == r['expected'].upper() else "✗"
            print(f"\n{status} {r['name']}:")
            print(f"    期望: {r['expected']} → 长宽比 {size_to_aspect_ratio(r['expected'])}")
            if r['size']:
                print(f"    实际: {r['size']} → 长宽比 {r['aspect_ratio']}")
                if r['size'].upper() == r['expected'].upper():
                    success_count += 1
            else:
                print(f"    实际: 未提取到")
        
        print(f"\n{'='*80}")
        print(f"成功率: {success_count}/{len(results)}")
        
        if success_count == len(results):
            print("✓ 所有测试通过！可以将此方法应用到爬虫脚本中")
        elif success_count > 0:
            print("⚠ 部分测试通过，需要改进提取方法")
        else:
            print("✗ 测试失败，需要检查HTML结构")
            print("\n请查看生成的 debug_*.html 文件，手动搜索尺寸信息的位置")
        
        print('='*80)
        
    finally:
        driver.quit()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    main()






