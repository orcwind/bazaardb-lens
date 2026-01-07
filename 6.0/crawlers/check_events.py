"""
检查events_final.json的完整性
"""

import json
from pathlib import Path

events_file = Path('event_details_final/events_final.json')

with open(events_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("事件数据完整性检查")
print("="*80)

# 基本统计
print(f"\n事件总数: {len(data)}")

total_choices = sum(len(e.get('choices', [])) for e in data)
print(f"总选项数: {total_choices}")

# 检查空描述
empty_desc = [(e['name'], c['name']) for e in data for c in e.get('choices', []) if not c.get('description', '').strip()]
print(f"\n空描述数量: {len(empty_desc)}")
if empty_desc:
    for e, c in empty_desc:
        print(f"  - {e} -> {c}")

# 检查缺失长宽比
missing_ar = [(e['name'], c['name']) for e in data for c in e.get('choices', []) if 'aspect_ratio' not in c]
print(f"\n缺失长宽比: {len(missing_ar)}")
if missing_ar and len(missing_ar) <= 20:
    for e, c in missing_ar:
        print(f"  - {e} -> {c}")
elif missing_ar:
    print(f"  (太多，省略显示)")

# 列出所有事件
print(f"\n所有事件:")
for i, e in enumerate(data, 1):
    choice_count = len(e.get('choices', []))
    print(f"  {i:2d}. {e['name']:30s} - {choice_count} 选项")

# 对比unique_events.json
print(f"\n" + "="*80)
print("与unique_events.json对比")
print("="*80)

with open('unique_events.json', 'r', encoding='utf-8') as f:
    unique_events = [line.strip().strip('"') for line in f if line.strip()]

print(f"unique_events.json: {len(unique_events)} 个事件")
print(f"events_final.json: {len(data)} 个事件")
print(f"差异: {len(unique_events) - len(data)} 个")

current_events = {e['name'] for e in data}
missing_events = [e for e in unique_events if e not in current_events]

if missing_events:
    print(f"\n缺失的事件:")
    for e in missing_events:
        print(f"  - {e}")




