#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试Tesseract配置"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 导入config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ConfigManager

def test_config():
    """测试配置管理器"""
    print("=" * 80)
    print("测试Tesseract配置")
    print("=" * 80)
    
    # 创建配置管理器
    config = ConfigManager()
    
    # 获取Tesseract路径
    tesseract_path = config.get_tesseract_path()
    print(f"\n获取的Tesseract路径: {tesseract_path}")
    print(f"路径是否存在: {os.path.exists(tesseract_path)}")
    
    # 检查便携版路径
    app_dir = os.path.dirname(os.path.abspath(__file__))
    portable_tesseract = os.path.join(app_dir, "Tesseract-OCR", "tesseract.exe")
    print(f"\n便携版Tesseract路径: {portable_tesseract}")
    print(f"便携版路径是否存在: {os.path.exists(portable_tesseract)}")
    
    # 检查配置文件
    config_file = "bazaar_lens_config.json"
    if os.path.exists(config_file):
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        print(f"\n配置文件中的Tesseract路径: {saved_config.get('tesseract_path')}")
    
    # 测试OCR
    print(f"\n测试OCR...")
    try:
        import pytesseract
        # 设置路径
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"已设置Tesseract路径: {tesseract_path}")
            
            # 测试版本
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract版本: {version}")
        else:
            print(f"错误: Tesseract路径不存在: {tesseract_path}")
            
    except Exception as e:
        print(f"OCR测试失败: {e}")

if __name__ == "__main__":
    test_config()