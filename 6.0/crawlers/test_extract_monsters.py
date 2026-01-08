"""测试从HTML文件提取怪物数据"""
import re
from html import unescape
from pathlib import Path

html_file = Path(__file__).parent.parent.parent / "data" / "html" / "monsters.html"

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"HTML文件大小: {len(html)} 字符")
print(f"包含 'CombatEncounter': {'CombatEncounter' in html}")

# 测试各种正则表达式
patterns = [
    (r'"Type"\s*:\s*"CombatEncounter"[^}]*?"_originalTitleText"\s*:\s*"([^"]+)"', "未转义版本"),
    (rf'\\"Type\\":\\"CombatEncounter\\"[^}}]*?\\"_originalTitleText\\":\s*\\"([^"]+)\\"', "转义版本（单反斜杠）"),
    (r'\\"Type\\":\\"CombatEncounter\\"[^}]*?\\"_originalTitleText\\":\s*\\"([^"]+)\\"', "转义版本（双反斜杠）"),
]

for pattern, desc in patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    print(f"\n{desc}: 找到 {len(matches)} 个匹配")
    if matches:
        print(f"  前3个: {[unescape(m)[:30] if isinstance(m, str) else str(m)[:30] for m in matches[:3]]}")

# 查找第一个CombatEncounter的位置
pos = html.find('CombatEncounter')
if pos != -1:
    print(f"\n第一个CombatEncounter位置: {pos}")
    print(f"前后500字符:")
    snippet = html[max(0, pos-200):min(len(html), pos+500)]
    print(snippet)

