import re

# 读取HTML
with open('../data/html/banannibal_detail.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"HTML文件大小: {len(html)} 字符\n")

# 查找 "Healthy" 的所有出现位置
positions = [m.start() for m in re.finditer('Healthy', html)]
print(f"找到 {len(positions)} 个 'Healthy'")

if positions:
    # 显示第一个出现的上下文
    pos = positions[0]
    context = html[max(0, pos-100):pos+200]
    print(f"\n第一个 'Healthy' 的上下文:")
    print(repr(context))

# 查找所有的 <script> 标签
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\n找到 {len(scripts)} 个 script 标签")

# 查找包含 "Healthy" 的 script
for i, script in enumerate(scripts):
    if 'Healthy' in script:
        print(f"\nScript #{i+1} 包含 'Healthy'")
        print(f"Script 大小: {len(script)} 字符")
        # 显示包含 "Healthy" 的片段
        pos = script.find('Healthy')
        snippet = script[max(0, pos-50):pos+100]
        print(f"片段: {repr(snippet[:200])}")
