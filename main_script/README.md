# Bazaar_Lens 主程序模块

## 📁 目录结构

```
main_script/
├── Bazaar_Lens.py          # 主程序（原文件，待重构）
├── config.py                # 配置管理模块
├── logger.py                # 日志管理模块
├── ocr.py                   # OCR功能模块
├── ui/                      # UI组件模块
│   ├── __init__.py
│   └── components.py        # IconFrame, ScrollableFrame
├── data/                    # 数据管理模块
│   ├── __init__.py
│   ├── loader.py            # 数据加载器
│   └── matcher.py           # 文本匹配器（占位）
├── game/                    # 游戏相关模块
│   ├── __init__.py
│   ├── position.py          # 位置配置
│   └── monitor.py           # 游戏日志监控（占位）
└── system/                  # 系统功能模块
    ├── __init__.py
    ├── admin.py             # 管理员权限
    ├── tray.py              # 系统托盘（占位）
    └── update.py            # 更新检查（占位）
```

## 📝 模块说明

### 已完成的模块
- ✅ **config.py** - ConfigManager类，配置管理
- ✅ **logger.py** - 日志系统配置和管理
- ✅ **ocr.py** - OCR功能函数
- ✅ **ui/components.py** - GUI组件（IconFrame, ScrollableFrame）
- ✅ **data/loader.py** - 数据加载器（DataLoader类）
- ✅ **game/position.py** - 位置配置管理

### 占位模块（需要完善）
- ⏳ **data/matcher.py** - 文本匹配逻辑（需要从Bazaar_Lens.py提取）
- ⏳ **game/monitor.py** - 游戏日志监控（需要从Bazaar_Lens.py提取）
- ⏳ **system/tray.py** - 系统托盘（需要从Bazaar_Lens.py提取）
- ⏳ **system/update.py** - 更新检查（需要从Bazaar_Lens.py提取）

## 🔄 下一步工作

1. **完善占位模块**：从 `Bazaar_Lens.py` 中提取完整实现
2. **重构主程序**：更新 `Bazaar_Lens.py` 的导入语句，使用新模块
3. **测试验证**：确保所有功能正常工作

## ⚠️ 注意事项

- 所有模块使用4空格缩进
- 确保没有循环导入
- 保持原有功能不变
