#!/usr/bin/env python3
"""
分析 Bazaar_Lens.py 文件结构，识别主要功能模块
"""
import re
import ast


def analyze_file(filename):
    """分析文件结构"""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 查找所有类定义
    classes = []
    functions = []
    imports = []
    
    # 分析导入
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append((i+1, stripped))
    
    # 查找类和函数（基于缩进和关键字）
    current_indent = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        
        # 查找类定义（模块级别，缩进为0）
        if re.match(r'^class\s+\w+', stripped):
            class_name = re.match(r'^class\s+(\w+)', stripped).group(1)
            classes.append({
                'name': class_name,
                'line': i+1,
                'indent': indent
            })
        
        # 查找函数定义（模块级别，缩进为0）
        if indent == 0 and re.match(r'^def\s+\w+', stripped):
            func_name = re.match(r'^def\s+(\w+)', stripped).group(1)
            functions.append({
                'name': func_name,
                'line': i+1,
                'indent': indent
            })
    
    # 分析主要功能区域
    sections = []
    section_keywords = [
        ('日志', ['logging', 'log', 'RotatingFileHandler']),
        ('OCR', ['ocr', 'tesseract', 'pytesseract', 'image_to_string']),
        ('GUI', ['tkinter', 'tk.', 'ttk.', 'Frame', 'Label', 'Window']),
        ('配置', ['config', 'ConfigManager', 'load_config']),
        ('数据加载', ['load_monster', 'load_event', 'load_items', 'json.load']),
        ('匹配', ['match', 'fuzzy', 'difflib', 'similarity']),
        ('系统托盘', ['pystray', 'SystemTray', 'tray']),
        ('更新', ['update', 'check_update', 'version']),
        ('游戏监控', ['log_monitor', 'game_log', 'instance']),
    ]
    
    for section_name, keywords in section_keywords:
        matches = []
        for i, line in enumerate(lines):
            if any(keyword.lower() in line.lower() for keyword in keywords):
                matches.append(i+1)
        if matches:
            sections.append({
                'name': section_name,
                'lines': matches[:5]  # 只显示前5个匹配
            })
    
    return {
        'classes': classes,
        'functions': functions,
        'imports': imports[:20],  # 前20个导入
        'sections': sections,
        'total_lines': len(lines)
    }


def print_analysis(result):
    """打印分析结果"""
    print("=" * 80)
    print("Bazaar_Lens.py 结构分析")
    print("=" * 80)
    print(f"\n总行数: {result['total_lines']}")
    
    print(f"\n📦 类定义 ({len(result['classes'])} 个):")
    for cls in result['classes']:
        print(f"  - {cls['name']} (第 {cls['line']} 行)")
    
    print(f"\n🔧 模块级函数 ({len(result['functions'])} 个):")
    for func in result['functions']:
        print(f"  - {func['name']}() (第 {func['line']} 行)")
    
    print(f"\n📥 导入语句 (前20个):")
    for line_num, import_stmt in result['imports']:
        print(f"  第 {line_num:4} 行: {import_stmt[:70]}")
    
    print(f"\n📋 功能模块:")
    for section in result['sections']:
        print(f"  - {section['name']}: 出现在第 {', '.join(map(str, section['lines']))} 行等")


if __name__ == "__main__":
    result = analyze_file('Bazaar_Lens.py')
    print_analysis(result)
    
    # 建议的拆分方案
    print("\n" + "=" * 80)
    print("💡 建议的模块拆分方案:")
    print("=" * 80)
    print("""
1. config.py - 配置管理
   - ConfigManager 类
   - 配置文件读写

2. logger.py - 日志管理
   - 日志配置
   - get_log_file_path()
   - hide_console() / show_console()

3. ocr.py - OCR功能
   - ocr_task()
   - direct_ocr()
   - OCR相关工具函数

4. ui/ - GUI相关
   - ui/components.py - IconFrame, ScrollableFrame
   - ui/window.py - 主窗口相关
   - ui/info_window.py - 信息显示窗口

5. data/ - 数据管理
   - data/loader.py - 数据加载函数
   - data/matcher.py - 匹配逻辑

6. game/ - 游戏相关
   - game/monitor.py - 游戏日志监控
   - game/position.py - 位置配置

7. system/ - 系统功能
   - system/tray.py - 系统托盘
   - system/update.py - 更新检查
   - system/admin.py - 管理员权限

8. Bazaar_Lens.py - 主程序
   - BazaarHelper 主类
   - 程序入口
    """)
