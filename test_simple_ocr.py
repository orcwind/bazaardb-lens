#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单OCR测试"""

import os
import sys
import cv2
import pytesseract

# 设置Tesseract路径
tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"Tesseract路径: {tesseract_path}")
else:
    print(f"警告: Tesseract路径不存在: {tesseract_path}")
    print("尝试在PATH中查找Tesseract...")

# 测试一张图片
temp_dir = "data/temp"
image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
image_files.sort(reverse=True)  # 按时间倒序

if image_files:
    test_image = os.path.join(temp_dir, image_files[0])
    print(f"\n测试图片: {test_image}")
    
    # 读取图片
    img = cv2.imread(test_image)
    if img is not None:
        print(f"图片尺寸: {img.shape}")
        
        # 转换为RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 简单OCR测试
        try:
            text = pytesseract.image_to_string(
                img_rgb,
                lang='chi_sim',
                config='--oem 1 --psm 11'
            )
            print(f"\nOCR结果:")
            print(f"  {repr(text.strip())}")
            
            # 测试清理
            import re
            cleaned = re.sub(r'[{}[\]()<>`~!@#$%^&*_+=;:"\',.?\\|]', '', text)
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            cleaned = cleaned.strip()
            print(f"\n清理后:")
            print(f"  {repr(cleaned)}")
            
        except Exception as e:
            print(f"OCR错误: {e}")
    else:
        print(f"无法读取图片: {test_image}")
else:
    print(f"没有找到测试图片")