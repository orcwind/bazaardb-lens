#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试OCR优化效果"""

import os
import sys
import cv2
import numpy as np
from PIL import Image
import logging

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'main_script'))

# 导入优化后的OCR处理器
try:
    from core.ocr_processor import OCRProcessor
    from data.matcher import TextMatcher
    from data.loader import DataLoader
except ImportError as e:
    print(f"导入错误: {e}")
    print("尝试直接导入...")
    # 尝试直接导入
    import importlib.util
    
    # 导入OCRProcessor
    ocr_processor_path = os.path.join(project_root, 'main_script', 'core', 'ocr_processor.py')
    spec = importlib.util.spec_from_file_location("ocr_processor", ocr_processor_path)
    ocr_processor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ocr_processor_module)
    OCRProcessor = ocr_processor_module.OCRProcessor
    
    # 导入TextMatcher
    matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
    spec = importlib.util.spec_from_file_location("matcher", matcher_path)
    matcher_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matcher_module)
    TextMatcher = matcher_module.TextMatcher
    
    # 导入DataLoader
    loader_path = os.path.join(project_root, 'main_script', 'data', 'loader.py')
    spec = importlib.util.spec_from_file_location("loader", loader_path)
    loader_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader_module)
    DataLoader = loader_module.DataLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_ocr_on_specific_image(image_path):
    """测试特定图片的OCR识别效果"""
    print(f"\n{'='*80}")
    print(f"测试图片: {os.path.basename(image_path)}")
    print(f"{'='*80}")
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误：无法读取图片 {image_path}")
        return
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print(f"图片尺寸: {img_rgb.shape}")
    
    # 创建OCR处理器
    ocr_processor = OCRProcessor()
    
    # 测试不同模式
    modes = ['fast', 'balanced', 'accurate']
    
    for mode in modes:
        print(f"\n--- {mode.upper()} 模式 ---")
        
        # 执行OCR
        text = ocr_processor.ocr_for_game(
            img_rgb,
            mode=mode,
            region_type='monster',
            use_preprocess=True
        )
        
        if text:
            print(f"OCR结果: {repr(text)}")
            
            # 加载数据并测试匹配
            try:
                data_loader = DataLoader()
                matcher = TextMatcher(
                    monster_data=data_loader.monster_data,
                    event_data=data_loader.event_data
                )
                
                match_type, match_name = matcher.find_best_match(text)
                if match_type and match_name:
                    print(f"匹配结果: {match_type} = {match_name}")
                else:
                    print(f"匹配结果: 未匹配")
            except Exception as e:
                print(f"匹配失败: {e}")
        else:
            print(f"OCR结果: 无结果")

def test_multiple_images():
    """测试多张图片"""
    temp_dir = "data/temp"
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 获取最新的几张图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort(reverse=True)  # 按时间倒序
    image_files = image_files[:5]  # 只测试最新的5张
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    for img_file in image_files:
        img_path = os.path.join(temp_dir, img_file)
        test_ocr_on_specific_image(img_path)

def test_specific_case():
    """测试特定案例：舞火大师 vs 火灵"""
    print(f"\n{'='*80}")
    print("测试特定案例：舞火大师 vs 火灵")
    print(f"{'='*80}")
    
    # 模拟OCR识别结果
    ocr_texts = [
        "舞火大师 ER",      # 原始OCR结果
        "舞火大师",         # 清理后的结果
        "火大师",           # 可能的部分识别
        "火灵",             # 错误匹配的结果
    ]
    
    # 加载数据
    data_loader = DataLoader()
    matcher = TextMatcher(
        monster_data=data_loader.monster_data,
        event_data=data_loader.event_data
    )
    
    for ocr_text in ocr_texts:
        print(f"\nOCR文本: {repr(ocr_text)}")
        match_type, match_name = matcher.find_best_match(ocr_text)
        if match_type and match_name:
            print(f"匹配结果: {match_type} = {match_name}")
            
            # 获取怪物数据验证
            if match_type == 'monster':
                monster = data_loader.find_monster_by_name(match_name)
                if monster:
                    print(f"怪物ID: {monster.get('id', 'N/A')}")
                    print(f"英文名: {monster.get('name', 'N/A')}")
        else:
            print(f"匹配结果: 未匹配")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试OCR优化效果")
    parser.add_argument('--test-all', action='store_true', help='测试所有图片')
    parser.add_argument('--test-case', action='store_true', help='测试特定案例')
    parser.add_argument('--image', type=str, help='测试特定图片路径')
    
    args = parser.parse_args()
    
    if args.test_all:
        test_multiple_images()
    elif args.test_case:
        test_specific_case()
    elif args.image:
        test_ocr_on_specific_image(args.image)
    else:
        # 默认测试最新图片
        test_multiple_images()
        print(f"\n{'='*80}")
        print("提示：")
        print("  使用 --test-all 测试所有图片")
        print("  使用 --test-case 测试特定案例（舞火大师 vs 火灵）")
        print("  使用 --image <路径> 测试特定图片")
        print(f"{'='*80}")