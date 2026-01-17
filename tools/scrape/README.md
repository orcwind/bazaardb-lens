# 怪物信息抓取脚本说明

简短说明：本目录下脚本用于抓取、提取并补充怪物/事件数据，最终产物用于生成加密数据包 `data_json.enc` 并供程序运行时加载。

主要脚本一览（按推荐执行顺序）
- `fetch_html.py`：抓取目标网站的原始 HTML（支持分页与重试），将页面保存到 `data/source_html/`。
- `extract_monsters.py`：从已抓取的 HTML 中解析出结构化怪物信息，输出中间文件 `data/intermediate/extracted_monsters_raw.jsonl`（每行一条 JSON）。
- `enrich_with_json.py`：加载 `data/json/items.json` 和 `data/json/skills.json`，为 `extracted_monsters_raw.jsonl` 中的 `drops`、`skills` 等引用补充中文名称和描述，输出 `data/intermediate/monsters_enriched.json`。
- `selenium_event_final.py`：使用 Selenium 抓取事件（event）详情，输出到 `event_details_final/events_final.json`。
- `fetch_event_name.py`：从 HTML 中提取事件名称列表，生成 `events_from_html.json`。
- `add_event_english_names.py`：为 `events_from_html.json` 补充 `name_en` 字段（英文名）。
- `validate_and_pack.py`：对最终数据做完整性检查并打包/加密为 `data_json.enc`（用于发布/打包时使用）。

输入 / 输出 目录约定
- `data/source_html/`：抓取到的原始 HTML（按日期/来源分文件保存）。
- `data/intermediate/extracted_monsters_raw.jsonl`：解析出的原始怪物条目（未补中文）。
- `data/intermediate/monsters_enriched.json`：补充中文和引用后生成的最终怪物数据（可进一步校验打包）。
- `data/json/items.json`：物品数据（含 `id`/`name`/`zh_name`/`aliases` 等）。
- `data/json/skills.json`：技能数据（含 `id`/`name`/`zh_name`/`aliases` 等）。
- `data/manifest/data_manifest.json`：记录抓取来源、抓取时间、脚本版本与数据版本。

实现要点与注意事项
- 抓取：使用 `requests`（静态）或 Selenium（动态），需设置超时与重试，并控制请求间隔以防被封禁。
- 解析：使用 `BeautifulSoup` 或 `lxml`，输出中立中间格式（jsonl）以便重跑/逐条修复。
- 匹配策略：优先精确匹配（规范化后），其次使用别名表（`aliases`），最后可启用模糊匹配（Levenshtein），模糊匹配须有置信度阈值并记录来源。
- 可审计性：保留原始字符串、匹配方式（`exact|alias|fuzzy`）和置信度分数，未匹配项输出 `unmatched_references.csv` 供人工补全。
- 自动化：将各阶段脚本串联到 Makefile / CI，用版本号与 manifest 保证可复现。
- 本地开发：允许从 `data/json/` 读取做调试；发布（打包后）应只使用加密包 `data_json.enc`。

文件位置
- 已创建：`tools/scrape/README.md`

后续建议（可选）
- 如果需要，我可以把 README 的内容追加到仓库根目录的 `新需求.txt` 指定位置，或生成 `fetch_html.py` / `extract_monsters.py` 的模板实现。

