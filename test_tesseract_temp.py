#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试Tesseract识别temp文件夹中的图片"""

import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def preprocess_image(img):
    """图像预处理优化，提高OCR识别质量"""
    try:
        # 转换为灰度图
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
        
        # 简单预处理：CLAHE增强对比度 + OTSU二值化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 放大图像以提高OCR准确性
        height, width = binary.shape
        if width < 400 or height < 200:
            scale = max(400 / width, 200 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            binary = cv2.resize(binary, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return binary
        
    except Exception as e:
        logging.error(f"图像预处理失败: {e}")
        return img

def test_tesseract_on_temp_images():
    """测试Tesseract识别temp文件夹中的图片"""
    temp_dir = "data/temp"
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 设置Tesseract路径（如果需要）
    tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"Tesseract路径设置为: {tesseract_path}")
    
    # 获取所有PNG图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort()
    
    print(f"\n找到 {len(image_files)} 张图片，开始识别...\n")
    
    # 识别每张图片
    success_count = 0
    for idx, img_file in enumerate(image_files, 1):
        img_path = os.path.join(temp_dir, img_file)
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(image_files)}] 处理: {img_file}")
        print(f"{'='*60}")
        
        try:
            # 读取图片
            img = cv2.imread(img_path)
            if img is None:
                print(f"  错误：无法读取图片 {img_path}")
                continue
            
            # 转换为RGB格式
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            print(f"  图片尺寸: {img_rgb.shape}")
            
            # 预处理图像
            processed_img = preprocess_image(img_rgb)
            processed_pil = Image.fromarray(processed_img)
            
            # 使用Tesseract识别，尝试多个PSM模式
            best_text = None
            best_psm = None
            
            psm_modes = [6, 7, 8]  # 6=统一文本块, 7=单行文本, 8=单个词
            
            for psm in psm_modes:
                try:
                    config = f'--psm {psm} --oem 3 -l chi_sim'
                    text = pytesseract.image_to_string(processed_pil, config=config).strip()
                    
                    if text:
                        print(f"  PSM {psm}: {repr(text[:100])}")
                        if not best_text or len(text) > len(best_text):
                            best_text = text
                            best_psm = psm
                except Exception as e:
                    print(f"  PSM {psm} 识别出错: {e}")
            
            if best_text:
                print(f"\n  ✓ 最佳识别结果 (PSM={best_psm}):")
                print(f"  {best_text}")
                success_count += 1
            else:
                print(f"\n  ✗ 未识别到文本")
                
        except Exception as e:
            print(f"  处理图片时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\n{'='*60}")
    print(f"测试完成: {success_count}/{len(image_files)} 张图片识别成功 ({success_count*100//len(image_files) if image_files else 0}%)")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_tesseract_on_temp_images()
