#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试实际OCR识别效果"""

import os
import sys
import cv2
import numpy as np
from PIL import Image
import logging

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'main_script'))

# 导入OCR处理器
import importlib.util
ocr_processor_path = os.path.join(project_root, 'main_script', 'core', 'ocr_processor.py')
spec = importlib.util.spec_from_file_location("ocr_processor", ocr_processor_path)
ocr_processor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr_processor_module)
OCRProcessor = ocr_processor_module.OCRProcessor

# 导入匹配器
matcher_path = os.path.join(project_root, 'main_script', 'data', 'matcher.py')
spec = importlib.util.spec_from_file_location("matcher", matcher_path)
matcher_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matcher_module)
TextMatcher = matcher_module.TextMatcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_monster_data():
    """加载怪物数据"""
    import json
    
    monster_data = {}
    
    # 加载monsters.json
    monsters_path = os.path.join(project_root, 'data', 'Json', 'monsters.json')
    if os.path.exists(monsters_path):
        try:
            with open(monsters_path, 'r', encoding='utf-8') as f:
                monsters = json.load(f)
                for monster in monsters:
                    name_zh = monster.get('name_zh', '')
                    if name_zh:
                        monster_data[name_zh] = monster
        except Exception as e:
            print(f"加载monsters.json失败: {e}")
    
    # 加载monsters_detail.json
    detail_path = os.path.join(project_root, 'data', 'Json', 'monsters_detail.json')
    if os.path.exists(detail_path):
        try:
            with open(detail_path, 'r', encoding='utf-8') as f:
                monsters_detail = json.load(f)
                for monster in monsters_detail:
                    name_zh = monster.get('name_zh', '')
                    if name_zh and name_zh not in monster_data:
                        monster_data[name_zh] = monster
        except Exception as e:
            print(f"加载monsters_detail.json失败: {e}")
    
    print(f"加载了 {len(monster_data)} 个怪物")
    return monster_data

def test_single_image(image_path, mode='balanced'):
    """测试单张图片"""
    print(f"\n{'='*80}")
    print(f"测试图片: {os.path.basename(image_path)}")
    print(f"模式: {mode}")
    print(f"{'='*80}")
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误：无法读取图片 {image_path}")
        return None
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print(f"图片尺寸: {img_rgb.shape}")
    
    # 设置Tesseract路径
    tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"已设置Tesseract路径: {tesseract_path}")
    else:
        print(f"警告: Tesseract路径不存在: {tesseract_path}")
        # 尝试在PATH中查找
        import pytesseract
        print(f"使用系统PATH中的Tesseract")
    
    # 创建OCR处理器
    ocr_processor = OCRProcessor()
    
    # 执行OCR
    text = ocr_processor.ocr_for_game(
        img_rgb,
        mode=mode,
        region_type='monster',
        use_preprocess=True
    )
    
    if text:
        print(f"OCR结果: {repr(text)}")
        return text
    else:
        print(f"OCR结果: 无结果")
        return None

def test_multiple_images():
    """测试多张图片"""
    temp_dir = os.path.join(project_root, "data", "temp")
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 获取最新的5张图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort(reverse=True)  # 按时间倒序
    image_files = image_files[:5]  # 只测试最新的5张
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    # 加载怪物数据
    monster_data = load_monster_data()
    
    # 创建匹配器
    matcher = TextMatcher(monster_data=monster_data)
    
    results = []
    
    for img_file in image_files:
        img_path = os.path.join(temp_dir, img_file)
        
        # 测试不同模式
        for mode in ['fast', 'balanced', 'accurate']:
            text = test_single_image(img_path, mode)
            if text:
                # 尝试匹配
                match_type, match_name = matcher.find_best_match(text)
                if match_type and match_name:
                    print(f"匹配结果: {match_type} = {match_name}")
                    results.append({
                        'image': img_file,
                        'mode': mode,
                        'text': text,
                        'match_type': match_type,
                        'match_name': match_name
                    })
                else:
                    print(f"匹配结果: 未匹配")
                    results.append({
                        'image': img_file,
                        'mode': mode,
                        'text': text,
                        'match_type': None,
                        'match_name': None
                    })
    
    # 统计结果
    print(f"\n{'='*80}")
    print("测试结果统计")
    print(f"{'='*80}")
    
    successful_matches = [r for r in results if r['match_type']]
    total_tests = len(results)
    
    if total_tests > 0:
        success_rate = len(successful_matches) / total_tests * 100
        print(f"总测试次数: {total_tests}")
        print(f"成功匹配: {len(successful_matches)}")
        print(f"失败匹配: {total_tests - len(successful_matches)}")
        print(f"成功率: {success_rate:.1f}%")
        
        # 按模式统计
        print(f"\n按模式统计:")
        for mode in ['fast', 'balanced', 'accurate']:
            mode_results = [r for r in results if r['mode'] == mode]
            mode_success = [r for r in mode_results if r['match_type']]
            if mode_results:
                mode_rate = len(mode_success) / len(mode_results) * 100
                print(f"  {mode:10s}: {len(mode_success)}/{len(mode_results)} ({mode_rate:.1f}%)")
        
        # 显示成功匹配的示例
        if successful_matches:
            print(f"\n成功匹配示例:")
            for result in successful_matches[:3]:  # 显示前3个
                print(f"  图片: {result['image']}")
                print(f"  模式: {result['mode']}")
                print(f"  OCR: {repr(result['text'][:50])}")
                print(f"  匹配: {result['match_type']} = {result['match_name']}")
                print()

if __name__ == "__main__":
    print("=" * 80)
    print("实际OCR识别效果测试")
    print("=" * 80)
    
    test_multiple_images()