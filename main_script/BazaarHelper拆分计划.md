# BazaarHelper 类拆分计划

## ✅ 已创建的模块结构

### core/ 模块（核心功能）
- ✅ **core/__init__.py** - 模块初始化
- ✅ **core/gui_manager.py** - GUI窗口管理器（占位）
- ✅ **core/ocr_processor.py** - OCR处理器（占位）
- ✅ **core/window_detector.py** - 游戏窗口检测器（占位）
- ✅ **core/cleanup_manager.py** - 清理管理器（占位）
- ✅ **core/main_controller.py** - 主控制器（整合所有模块）

## 📋 拆分方案

### 1. GUIManager (GUI窗口管理)
**需要从BazaarHelper提取的方法：**
- `create_info_window()` - 创建信息窗口
- `update_info_window()` - 更新信息窗口
- `start_gui_update_timer()` - 启动GUI更新定时器
- `process_gui_updates()` - 处理GUI更新队列
- `destroy_info_window()` - 销毁信息窗口

**相关属性：**
- `info_window` - 信息窗口对象
- `gui_update_queue` - GUI更新队列
- `gui_update_lock` - GUI更新锁
- `current_text` - 当前文本

### 2. OCRProcessor (OCR处理)
**需要从BazaarHelper提取的方法：**
- `capture_and_ocr()` - 捕获图像并OCR
- `process_ocr_text()` - 处理OCR文本
- 图像预处理相关方法
- OCR缓存管理

**相关属性：**
- `ocr_lock` - OCR线程锁
- `ocr_cache` - OCR结果缓存
- `match_cache` - 匹配结果缓存

### 3. WindowDetector (窗口检测)
**需要从BazaarHelper提取的方法：**
- `get_game_window()` - 获取游戏窗口
- `is_cursor_in_icon_area()` - 检测光标是否在图标区域
- `calculate_name_area_from_icon()` - 根据图标计算名称区域
- `_build_icon_area_from_cursor()` - 从光标构建图标区域

**相关属性：**
- `game_hwnd` - 游戏窗口句柄
- `game_rect` - 游戏窗口位置

### 4. CleanupManager (清理管理)
**需要从BazaarHelper提取的方法：**
- `cleanup_temp_files()` - 清理临时文件
- `cleanup_system_tray_icons()` - 清理系统托盘图标
- `_cleanup_notification_area()` - 清理通知区域
- `_refresh_system_tray()` - 刷新系统托盘
- `_restart_explorer()` - 重启资源管理器
- `_cleanup_icon_cache()` - 清理图标缓存

### 5. MainController (主控制器)
**职责：**
- 整合所有功能模块
- 管理程序生命周期
- 协调各模块之间的交互
- 主循环控制

**需要从BazaarHelper提取的方法：**
- `keep_alive()` - 主循环
- `run()` - 运行程序
- `stop()` - 停止程序
- `__init__()` - 初始化（简化版，使用各模块）

## 🔄 拆分步骤

1. ✅ 创建core模块基础结构
2. ⏳ 从Bazaar_Lens.py提取GUI管理逻辑
3. ⏳ 从Bazaar_Lens.py提取OCR处理逻辑
4. ⏳ 从Bazaar_Lens.py提取窗口检测逻辑
5. ⏳ 从Bazaar_Lens.py提取清理逻辑
6. ⏳ 完善MainController整合所有模块
7. ⏳ 重构Bazaar_Lens.py使用新的core模块

## 📊 拆分效果

**拆分前：**
- BazaarHelper类：~5000行代码
- 所有功能混在一起
- 难以维护和测试

**拆分后：**
- MainController：~100行（整合逻辑）
- GUIManager：~200行（GUI相关）
- OCRProcessor：~300行（OCR相关）
- WindowDetector：~200行（窗口检测）
- CleanupManager：~150行（清理相关）
- 总计：~950行（更清晰、易维护）

## ⚠️ 注意事项

- 保持各模块之间的接口清晰
- 避免循环依赖
- 确保线程安全
- 保持原有功能不变
