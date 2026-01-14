#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单测试优化后的OCR效果"""

import os
import sys
import cv2
import numpy as np
import pytesseract
from PIL import Image

# 设置Tesseract路径
tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"Tesseract路径: {tesseract_path}")
else:
    print(f"警告: Tesseract路径不存在: {tesseract_path}")

def preprocess_denoise_clahe_padding(img_array):
    """预处理：去噪+CLAHE增强+Padding（测试中表现很好）"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 去噪
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # CLAHE增强
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 添加白色边框（Padding）
    height, width = enhanced.shape
    pad_size = max(20, int(min(width, height) * 0.1))
    padded = cv2.copyMakeBorder(
        enhanced, 
        pad_size, pad_size, pad_size, pad_size,
        cv2.BORDER_CONSTANT, 
        value=255
    )
    
    return padded

def preprocess_histogram_equalization(img_array):
    """预处理：直方图均衡化（测试中匹配次数最多）"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 直方图均衡化
    equalized = cv2.equalizeHist(gray)
    
    # 添加白色边框（Padding）
    height, width = equalized.shape
    pad_size = max(20, int(min(width, height) * 0.1))
    padded = cv2.copyMakeBorder(
        equalized, 
        pad_size, pad_size, pad_size, pad_size,
        cv2.BORDER_CONSTANT, 
        value=255
    )
    
    return padded

def clean_ocr_text(text):
    """清理OCR结果"""
    if not text:
        return ""
    
    import re
    # 移除特殊字符
    text = re.sub(r'[{}[\]()<>`~!@#$%^&*_+=;:"\',.?\\|]', '', text)
    # 合并空格
    text = re.sub(r'\s{2,}', ' ', text)
    # 移除首尾空白
    return text.strip()

def test_image(image_path):
    """测试单张图片"""
    print(f"\n{'='*80}")
    print(f"测试图片: {os.path.basename(image_path)}")
    print(f"{'='*80}")
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误：无法读取图片")
        return
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print(f"图片尺寸: {img_rgb.shape}")
    
    # 测试不同预处理方法
    methods = [
        ('原始图像', lambda x: cv2.cvtColor(x, cv2.COLOR_RGB2GRAY) if len(x.shape) == 3 else x.copy()),
        ('直方图均衡化', preprocess_histogram_equalization),
        ('去噪+CLAHE+Padding', preprocess_denoise_clahe_padding),
    ]
    
    # OCR配置（测试中表现最好的）
    ocr_config = '--oem 1 --psm 11 -c preserve_interword_spaces=1'
    
    for method_name, preprocess_func in methods:
        try:
            # 预处理
            processed = preprocess_func(img_rgb)
            
            # 转换为PIL Image
            pil_img = Image.fromarray(processed)
            
            # 执行OCR
            text = pytesseract.image_to_string(
                pil_img,
                lang='chi_sim',
                config=ocr_config
            )
            
            # 清理结果
            text = clean_ocr_text(text)
            
            if text:
                print(f"\n{method_name}:")
                print(f"  结果: {repr(text)}")
                
                # 简单分析
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
                digits = sum(1 for c in text if '0' <= c <= '9')
                
                print(f"  中文字符: {chinese_chars}, 英文字母: {english_chars}, 数字: {digits}")
                
                if chinese_chars >= 2:
                    print(f"  ✅ 可能包含中文名称")
                elif chinese_chars == 1:
                    print(f"  ⚠️  只有一个中文字符")
                else:
                    print(f"  ❌ 没有中文字符")
            else:
                print(f"\n{method_name}: 无结果")
                
        except Exception as e:
            print(f"\n{method_name} 失败: {e}")

def main():
    """主函数"""
    print("=" * 80)
    print("优化OCR效果测试")
    print("=" * 80)
    
    # 测试data/temp中的最新图片
    temp_dir = "data/temp"
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 获取最新的3张图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort(reverse=True)  # 按时间倒序
    image_files = image_files[:3]  # 只测试最新的3张
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    for img_file in image_files:
        img_path = os.path.join(temp_dir, img_file)
        test_image(img_path)

if __name__ == "__main__":
    main()