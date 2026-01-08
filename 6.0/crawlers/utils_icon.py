"""
图标处理工具函数
统一处理图标命名、下载、路径等
"""

import os
import re
import requests
from pathlib import Path

# 统一图标目录和JSON目录
ICONS_DIR = Path('../../data/icon')
NEW_JSON_DIR = Path('../../data/Json')
ICONS_DIR.mkdir(parents=True, exist_ok=True)
NEW_JSON_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name):
    """统一文件名规则：处理空格、引号等特殊字符
    
    Args:
        name: 原始名称
    
    Returns:
        规范化后的文件名（不含扩展名）
    """
    if not isinstance(name, str):
        return ""
    
    # 替换引号为下划线
    name = name.replace('"', '_').replace("'", '_')
    # 替换多个空格为单个下划线
    name = re.sub(r'\s+', '_', name)
    # 移除其他非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 移除首尾下划线和空格
    name = name.strip('_').strip()
    
    return name

def get_icon_filename(*names):
    """根据多个名称生成图标文件名
    
    Args:
        *names: 名称列表（例如：怪物名、技能名）
    
    Returns:
        完整的文件名（含.webp扩展名）
    """
    # 规范化所有名称并合并
    sanitized = [sanitize_filename(name) for name in names if name]
    filename = '_'.join(sanitized) + '.webp'
    return filename

def download_icon(icon_url, *names, category=None):
    """下载图标到分类目录
    
    Args:
        icon_url: 图标URL
        *names: 名称列表（用于生成文件名）
        category: 图标类别 ('item', 'skill', 'monster', 'event')，用于创建对应文件夹
    
    Returns:
        图标相对路径（如 'item/filename.webp' 或 'skill/filename.webp'），如果失败返回空字符串
    """
    if not icon_url:
        return ""
    
    try:
        # 生成文件名
        filename = get_icon_filename(*names)
        
        # 确定保存目录（根据category创建子文件夹）
        if category:
            # 规范化类别名称（item/skill/monster/event）
            category = category.lower()
            save_dir = ICONS_DIR / category
            save_dir.mkdir(parents=True, exist_ok=True)
            filepath = save_dir / filename
            relative_path = f"{category}/{filename}"
        else:
            # 如果没有指定类别，保存到根目录（向后兼容）
            filepath = ICONS_DIR / filename
            relative_path = filename
        
        # 如果文件已存在，跳过下载
        if filepath.exists():
            return relative_path
        
        # 下载图标
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(icon_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return relative_path
        else:
            return ""
            
    except Exception as e:
        print(f"        下载图标失败: {e}")
        return ""

def get_icon_path(icon_filename):
    """获取图标的完整路径（用于显示）
    
    Args:
        icon_filename: 图标文件名或相对路径（如 'item/filename.webp' 或 'filename.webp'）
    
    Returns:
        完整路径字符串
    """
    if not icon_filename:
        return ""
    # icon_filename 可能是相对路径（如 'item/filename.webp'）或文件名（如 'filename.webp'）
    # 直接拼接即可，Path 会自动处理路径分隔符
    return str(ICONS_DIR / icon_filename)

