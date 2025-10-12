# 图标长宽比功能 - 快速指南

## 💡 核心概念

游戏中卡片有3种尺寸，对应不同的图标显示比例：

| 卡片尺寸 | 长宽比 | 显示效果 | 示例（高度96px） |
|---------|--------|----------|-----------------|
| **Small** | 0.5 | 竖长图 | 48×96 |
| **Medium** | 1.0 | 正方形 | 96×96 |
| **Large** | 1.5 | 横长图 | 144×96 |

---

## 🚀 快速开始

### 方式一：运行爬虫（推荐）⭐

```bash
cd 6.0/crawlers
python selenium_monster_v3.py
```

**自动完成：**
1. ✅ 检查已有数据，补充缺失的长宽比
2. ✅ 爬取新怪物，自动包含长宽比
3. ✅ 增量保存，支持断点续传

---

### 方式二：测试验证

```bash
cd 6.0/crawlers
python test_extract_size.py
```

**测试内容：**
- 测试 Ahexa 的4个物品
- 验证3种不同比例的提取
- 成功率应该是 4/4

---

## 📊 运行效果

### 首次运行（补充现有数据）

```
Selenium怪物爬虫 V3 - 处理所有怪物（增量保存 + 长宽比更新）
================================================================================

总怪物数: 104
已处理: 104
待处理: 0

================================================================================
检查并更新缺失的长宽比
================================================================================

发现 50 个怪物需要更新长宽比
共 400 个卡片缺失长宽比

[更新] Banannibal - 3 个项目
  物品: Med Kit
    ✓ Small → 0.5
  物品: Bluenanas
    ✓ Small → 0.5
  物品: Duct Tape
    ✓ Medium → 1.0

...

✓ 已更新 400 个卡片的长宽比
✓ 长宽比已更新并保存
✓ 所有怪物已处理完成！
```

---

### 后续运行（只处理新增）

```
总怪物数: 110
已处理: 104
待处理: 6

================================================================================
检查并更新缺失的长宽比
================================================================================
✓ 所有怪物已有完整的长宽比信息

将继续处理剩余的 6 个怪物...
================================================================================

[1/6] 处理: New Monster 1
  ...
  物品: New Item
    ✓ 描述: Deal 10 Damage... [Medium, 比例:1.0]
```

---

## 📝 数据格式

### 更新后的 monsters_v3.json

```json
{
  "name": "Ahexa",
  "skills": [],
  "items": [
    {
      "name": "Crypto",
      "icon": "icons/Ahexa_Crypto.webp",
      "description": "...",
      "aspect_ratio": 0.5
    },
    {
      "name": "Rapid Injection System",
      "icon": "icons/Ahexa_Rapid Injection System.webp",
      "description": "...",
      "aspect_ratio": 1.0
    },
    {
      "name": "Solar Farm",
      "icon": "icons/Ahexa_Solar Farm.webp",
      "description": "...",
      "aspect_ratio": 1.5
    }
  ]
}
```

---

## ❓ 常见问题

### Q1: 需要为事件数据更新长宽比吗？
**A:** 不需要。所有事件选择图标都是1:1，默认值已经正确。

### Q2: 运行需要多长时间？
**A:** 
- 如果所有数据都有长宽比：几秒钟（只检查）
- 如果需要补充400+项：约15-20分钟（访问网页）

### Q3: 可以中断后继续吗？
**A:** 可以！脚本支持增量保存，每处理完一个怪物就保存。

### Q4: 如何验证更新是否成功？
**A:** 
```bash
# 方法1: 检查JSON文件
# 打开 monsters_v3.json，搜索 "aspect_ratio"

# 方法2: 运行Bazaar_Lens.py
# 悬停在不同尺寸的物品上，查看图标显示效果
```

---

## 🔧 技术实现

### 核心代码

```python
# 1. 从HTML提取尺寸
def extract_card_size(html):
    pattern = r'<span[^>]*>\s*(Small|Medium|Large)\s*</span>'
    match = re.search(pattern, html, re.IGNORECASE)
    return match.group(1) if match else None

# 2. 尺寸转长宽比
def size_to_aspect_ratio(size):
    mapping = {'SMALL': 0.5, 'MEDIUM': 1.0, 'LARGE': 1.5}
    return mapping.get(size.upper(), 1.0)

# 3. 获取卡片信息
description, size = get_card_description(driver, card_url)
aspect_ratio = size_to_aspect_ratio(size)
```

---

## ✅ 完成清单

使用前检查：
- [ ] Chrome浏览器已安装
- [ ] 网络连接正常
- [ ] 已运行测试脚本（test_extract_size.py）
- [ ] 测试成功率 4/4

更新数据：
- [ ] 运行 `python selenium_monster_v3.py`
- [ ] 等待完成（15-20分钟）
- [ ] 检查 monsters_v3.json 中有 aspect_ratio 字段
- [ ] 测试 Bazaar_Lens.py 显示效果

---

**版本：** v6.0  
**最后更新：** 2025-10-10  
**测试状态：** ✅ Ahexa 4/4 通过



