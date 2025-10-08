"""分析debug_monsters.html的结构"""
from bs4 import BeautifulSoup
import re

# 读取HTML
with open('crawlers/6.0/debug_monsters.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"HTML文件大小: {len(html)} 字符")
print("=" * 60)

# 解析HTML
soup = BeautifulSoup(html, 'html.parser')

# 查找所有链接
all_links = soup.find_all('a')
print(f"\n找到 {len(all_links)} 个 <a> 标签")

# 查找包含 /card/ 的链接
card_links = soup.find_all('a', href=re.compile(r'/card/'))
print(f"找到 {len(card_links)} 个包含 /card/ 的链接")

# 查看前5个卡片链接的结构
print("\n" + "=" * 60)
print("前5个卡片链接的结构:")
print("=" * 60)
for i, link in enumerate(card_links[:5], 1):
    print(f"\n链接 {i}:")
    print(f"  href: {link.get('href', 'N/A')[:100]}")
    
    # 查找img标签
    img = link.find('img')
    if img:
        print(f"  img找到: Yes")
        print(f"  img.src: {img.get('src', 'N/A')[:100]}")
        print(f"  img.srcset: {img.get('srcset', 'N/A')[:100]}")
        print(f"  img其他属性: {list(img.attrs.keys())}")
        
        # 检查是否包含encounter
        src = img.get('src', '')
        srcset = img.get('srcset', '')
        if '/encounter/' in src or '/encounter/' in srcset:
            print(f"  ✓ 包含 /encounter/")
        else:
            print(f"  ✗ 不包含 /encounter/")
    else:
        print(f"  img找到: No")
    print(f"  完整HTML: {str(link)[:200]}")

# 统计包含encounter的链接
encounter_count = 0
for link in card_links:
    img = link.find('img')
    if img:
        src = img.get('src', '')
        srcset = img.get('srcset', '')
        if '/encounter/' in src or '/encounter/' in srcset:
            encounter_count += 1

print("\n" + "=" * 60)
print(f"包含 /encounter/ 的卡片链接数量: {encounter_count}")
print("=" * 60)





