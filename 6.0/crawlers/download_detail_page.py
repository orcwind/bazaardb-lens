import requests
import os
from pathlib import Path

# 创建输出目录
output_dir = Path('../data/html')
output_dir.mkdir(parents=True, exist_ok=True)

# 下载Banannibal详情页
url = "https://bazaardb.gg/card/1q3zi7wtui5kfes7wxor9hgla/Banannibal"

print(f"正在下载: {url}")

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

response = session.get(url, timeout=30)
response.raise_for_status()

# 保存HTML
output_file = output_dir / 'banannibal_detail.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"已保存到: {output_file}")
print(f"文件大小: {len(response.text)} 字符")

# 搜索关键信息
import re

# 查找 "Healthy Jolt" (技能名称)
if 'Healthy Jolt' in response.text:
    print("✓ 找到技能名称 'Healthy Jolt'")
    # 提取周围100个字符
    pos = response.text.find('Healthy Jolt')
    snippet = response.text[max(0, pos-50):pos+150]
    print(f"  上下文: {repr(snippet[:200])}")
else:
    print("✗ 未找到 'Healthy Jolt'")

# 查找 "Med Kit" (物品名称)
if 'Med Kit' in response.text:
    print("✓ 找到物品名称 'Med Kit'")
    pos = response.text.find('Med Kit')
    snippet = response.text[max(0, pos-50):pos+150]
    print(f"  上下文: {repr(snippet[:200])}")
else:
    print("✗ 未找到 'Med Kit'")

# 查找 Level
level_matches = re.findall(r'Level["\s:]+(\d+)', response.text)
print(f"找到 {len(level_matches)} 个 Level 匹配: {level_matches[:5]}")

# 查找 Health
health_matches = re.findall(r'Health["\s:]+(\d+)', response.text)
print(f"找到 {len(health_matches)} 个 Health 匹配: {health_matches[:5]}")
