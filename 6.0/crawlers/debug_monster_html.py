"""调试怪物HTML数据格式"""
import re
from pathlib import Path
from html import unescape

html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters_list_page.html"

if not html_file.exists():
    print(f"文件不存在: {html_file}")
    exit(1)

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"HTML长度: {len(html)} 字符")
print()

# 检查CombatEncounter
matches1 = re.findall(r'"Type":"CombatEncounter"', html)
matches2 = re.findall(r'\\"Type\\":\\"CombatEncounter\\"', html)
matches3 = re.findall(r'CombatEncounter', html)

print(f"未转义的 \"Type\":\"CombatEncounter\": {len(matches1)} 个")
print(f"转义的 \\\"Type\\\":\\\"CombatEncounter\\\": {len(matches2)} 个")
print(f"所有 CombatEncounter: {len(matches3)} 个")
print()

# 检查_originalTitleText
matches4 = re.findall(r'"_originalTitleText":"([^"]+)"', html)
matches5 = re.findall(r'\\"_originalTitleText\\":\\"([^"]+)\\"', html)

print(f"未转义的 _originalTitleText: {len(matches4)} 个")
print(f"转义的 _originalTitleText: {len(matches5)} 个")
if matches4:
    print(f"前5个未转义名称: {matches4[:5]}")
if matches5:
    print(f"前5个转义名称: {[unescape(m) for m in matches5[:5]]}")
print()

# 检查Pickpocket
pos = html.find('Pickpocket')
if pos > 0:
    print(f"找到Pickpocket在位置: {pos}")
    print("前后500字符:")
    print(html[max(0, pos-250):pos+250])
    print()
    
    # 检查Pickpocket附近的Type
    area = html[max(0, pos-1000):pos+1000]
    if 'CombatEncounter' in area:
        print("Pickpocket附近包含CombatEncounter")
    if 'Type' in area:
        print("Pickpocket附近包含Type")
    if '_originalTitleText' in area:
        print("Pickpocket附近包含_originalTitleText")
else:
    print("未找到Pickpocket")

# 检查Next.js序列化数据
if 'self.__next_f' in html:
    print("\n找到Next.js序列化数据 (self.__next_f)")
    # 查找所有包含CombatEncounter的脚本块
    script_pattern = r'<script[^>]*>(.*?)</script>'
    scripts = re.findall(script_pattern, html, re.DOTALL)
    combat_scripts = [s for s in scripts if 'CombatEncounter' in s]
    print(f"包含CombatEncounter的脚本块: {len(combat_scripts)} 个")
    if combat_scripts:
        print(f"第一个脚本块长度: {len(combat_scripts[0])} 字符")
        print(f"前500字符: {combat_scripts[0][:500]}")

