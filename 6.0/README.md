# Bazaar数据库爬虫系统 v6.0

## 概述

这是一个完整的爬虫系统，用于从 https://bazaardb.gg 抓取游戏数据，包括怪物和事件信息。

## 功能特性

- ✅ 自动抓取所有怪物信息（技能、物品、图标）
- ✅ 自动抓取所有事件信息（选项、奖励、图标）
- ✅ 自动下载并保存高清图标到本地
- ✅ 生成标准化的JSON数据文件
- ✅ 完整的日志记录
- ✅ 支持断点续传（图标去重）

## 目录结构

```
6.0/
├── crawlers/          # 爬虫脚本
│   ├── monster_crawler.py  # 怪物爬虫
│   ├── event_crawler.py    # 事件爬虫
│   ├── utils.py            # 工具函数
│   └── main.py             # 主入口程序
├── data/              # 输出的JSON数据
│   ├── monsters.json       # 怪物数据
│   └── events.json         # 事件数据
├── icons/             # 下载的图标
│   ├── skills/             # 技能图标
│   └── items/              # 物品图标
└── logs/              # 日志文件
```

## 安装依赖

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装Chrome浏览器

确保系统已安装Chrome浏览器。

### 3. 安装ChromeDriver

#### 方法1：自动安装（推荐）
Selenium 4.x 会自动管理ChromeDriver。

#### 方法2：手动安装
1. 访问 https://chromedriver.chromium.org/downloads
2. 下载与Chrome版本匹配的ChromeDriver
3. 将ChromeDriver添加到系统PATH

## 使用方法

### 快速开始

在 `6.0/crawlers` 目录下运行：

```bash
# 爬取所有数据（怪物 + 事件）
python main.py

# 只爬取怪物
python main.py --type monster

# 只爬取事件
python main.py --type event

# 使用无头模式（后台运行，不显示浏览器）
python main.py --headless
```

### 单独运行爬虫

```bash
# 只运行怪物爬虫
python monster_crawler.py

# 只运行事件爬虫
python event_crawler.py
```

## 输出文件说明

### monsters.json

包含所有怪物的信息：

```json
{
  "monsters": [
    {
      "name": "怪物名称",
      "skills": [
        {
          "name": "技能名称",
          "icon": "icons/skills/技能图标.webp",
          "description": "技能描述",
          "aspect_ratio": 1.0
        }
      ],
      "items": [
        {
          "name": "物品名称",
          "icon": "icons/items/物品图标.webp",
          "description": "物品描述",
          "aspect_ratio": 0.5
        }
      ]
    }
  ]
}
```

### events.json

包含所有事件的信息：

```json
[
  {
    "name": "事件名称",
    "description": "事件描述",
    "options": [
      {
        "name": "选项名称",
        "icon": "icons/items/选项图标.webp",
        "description": "选项描述"
      }
    ]
  }
]
```

## 特性说明

### 1. 智能图标下载

- 自动检测已下载的图标，避免重复下载
- 使用文件名hash避免文件名冲突
- 保留原始图标格式（webp/png/jpg）

### 2. 日志记录

所有操作都会记录到 `6.0/logs/` 目录：

- `monster_crawler_YYYYMMDD_HHMMSS.log` - 怪物爬虫日志
- `event_crawler_YYYYMMDD_HHMMSS.log` - 事件爬虫日志
- `main_YYYYMMDD_HHMMSS.log` - 主程序日志

### 3. 错误处理

- 网络错误自动重试
- 页面加载超时处理
- 元素查找失败时的降级策略

## 常见问题

### Q: ChromeDriver版本不匹配

**A:** 使用Selenium 4.x会自动处理。如果仍有问题，请手动下载匹配版本的ChromeDriver。

### Q: 爬取速度慢

**A:** 为了避免对服务器造成压力，爬虫在每次请求之间都有延迟。这是正常的。

### Q: 部分图标下载失败

**A:** 查看日志文件了解详情。可能是网络问题或图标URL失效。

### Q: 页面元素查找失败

**A:** 网站可能更新了HTML结构。需要更新爬虫代码中的CSS选择器。

## 注意事项

1. **遵守网站条款**：请遵守 bazaardb.gg 的使用条款和robots.txt
2. **合理使用**：不要频繁运行爬虫，避免对服务器造成负担
3. **数据使用**：抓取的数据仅供个人学习使用
4. **网络连接**：确保网络连接稳定

## 更新日志

### v6.0 (2025-10-08)

- ✨ 全新的爬虫架构
- ✨ 直接从网页提取信息，不保存中间HTML
- ✨ 适配新版网站（Patch 6.0）的hash格式图标
- ✨ 完整的图标下载和管理系统
- ✨ 统一的日志记录
- ✨ 模块化设计，易于维护和扩展

## 技术栈

- Python 3.8+
- Selenium - 浏览器自动化
- Requests - HTTP请求
- Chrome/ChromeDriver - 浏览器驱动

## 开发者

如需修改或扩展功能，请参考代码注释。主要模块：

- `utils.py` - 工具函数（日志、图标下载等）
- `monster_crawler.py` - 怪物爬虫逻辑
- `event_crawler.py` - 事件爬虫逻辑
- `main.py` - 主程序入口

## 许可证

本项目仅供学习交流使用。






