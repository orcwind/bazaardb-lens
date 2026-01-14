#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证优化后的OCR配置"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'main_script'))

def verify_ocr_config():
    """验证OCR配置"""
    print("=" * 80)
    print("验证优化后的OCR配置")
    print("=" * 80)
    
    # 导入OCR处理器
    try:
        import importlib.util
        ocr_processor_path = os.path.join(project_root, 'main_script', 'core', 'ocr_processor.py')
        spec = importlib.util.spec_from_file_location("ocr_processor", ocr_processor_path)
        ocr_processor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ocr_processor_module)
        OCRProcessor = ocr_processor_module.OCRProcessor
        
        print("✓ 成功导入OCRProcessor")
    except Exception as e:
        print(f"✗ 导入OCRProcessor失败: {e}")
        return
    
    # 创建OCR处理器实例
    try:
        ocr_processor = OCRProcessor()
        print("✓ 成功创建OCRProcessor实例")
    except Exception as e:
        print(f"✗ 创建OCRProcessor实例失败: {e}")
        return
    
    # 验证不同模式的配置
    print("\n验证OCR配置:")
    modes = ['fast', 'balanced', 'accurate']
    
    for mode in modes:
        try:
            config = ocr_processor.get_game_tesseract_config(mode)
            print(f"\n{mode.upper()} 模式:")
            print(f"  PSM: {config.get('psm')}")
            print(f"  OEM: {config.get('oem')}")
            print(f"  配置: {config.get('config')}")
            
            # 检查是否使用PSM11_OEM1
            if '--psm 11' in config.get('config', '') and '--oem 1' in config.get('config', ''):
                print(f"  ✅ 使用PSM11_OEM1（测试验证的最佳配置）")
            else:
                print(f"  ⚠️  未使用PSM11_OEM1")
                
        except Exception as e:
            print(f"\n{mode.upper()} 模式验证失败: {e}")
    
    # 验证预处理方法
    print("\n验证预处理方法描述:")
    try:
        import inspect
        source = inspect.getsource(ocr_processor.preprocess_image)
        if '直方图均衡化' in source:
            print("  ✅ 预处理方法包含直方图均衡化")
        else:
            print("  ⚠️  预处理方法可能未使用直方图均衡化")
            
        if 'balanced' in source and '直方图均衡化' in source:
            print("  ✅ 平衡模式使用直方图均衡化")
        else:
            print("  ⚠️  平衡模式可能未使用直方图均衡化")
            
    except Exception as e:
        print(f"  获取预处理方法源码失败: {e}")
    
    # 验证匹配逻辑优化
    print("\n验证匹配逻辑优化:")
    try:
        matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
        with open(matcher_path, 'r', encoding='utf-8') as f:
            matcher_code = f.read()
            
        if 'required_char_ratio = 0.60' in matcher_code and 'min_matched_chars = 2' in matcher_code:
            print("  ✅ 4字名称匹配要求已优化（0.60, 2字符）")
        else:
            print("  ⚠️  4字名称匹配要求可能未优化")
            
        if 'monster_clean_zh_only in line_clean_zh_only' in matcher_code:
            print("  ✅ 已添加完整匹配检查")
        else:
            print("  ⚠️  可能缺少完整匹配检查")
            
    except Exception as e:
        print(f"  验证匹配逻辑失败: {e}")
    
    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)

if __name__ == "__main__":
    verify_ocr_config()