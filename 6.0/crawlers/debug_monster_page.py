import requests

# 下载一个怪物详情页用于分析
monster_name = "Banannibal"
url = f"https://bazaardb.gg/search?q={monster_name}"

print(f"正在下载: {url}")

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

response = session.get(url, timeout=30)
response.raise_for_status()

# 保存HTML
output_file = 'debug_monster_page.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"已保存到: {output_file}")
print(f"文件大小: {len(response.text)} 字符")

# 搜索 "CombatEncounter" 看看有多少个
import re
matches = re.findall(r'CombatEncounter', response.text)
print(f"找到 {len(matches)} 个 CombatEncounter")

# 搜索可能的技能/掉落物关键词
for keyword in ['Skill', 'Drop', 'Ability', 'Reward', 'Loot']:
    matches = re.findall(keyword, response.text, re.IGNORECASE)
    if matches:
        print(f"找到 {len(matches)} 个 {keyword}")
