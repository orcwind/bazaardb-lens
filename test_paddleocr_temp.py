#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试PaddleOCR识别temp文件夹中的图片"""

import os
import cv2
import numpy as np
from paddleocr import PaddleOCR
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_paddleocr_on_temp_images():
    """测试PaddleOCR识别temp文件夹中的图片"""
    temp_dir = "data/temp"
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 初始化PaddleOCR
    print("正在初始化PaddleOCR...")
    try:
        paddle_ocr = PaddleOCR(use_textline_orientation=True, lang='ch')
        print("PaddleOCR初始化成功")
    except Exception as e:
        print(f"PaddleOCR初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 获取所有PNG图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort()
    
    print(f"\n找到 {len(image_files)} 张图片，开始识别...\n")
    
    # 识别每张图片
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
            
            # 转换为RGB格式（PaddleOCR需要RGB）
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            print(f"  图片尺寸: {img_rgb.shape}")
            
            # 使用PaddleOCR识别
            print("  正在识别...")
            try:
                # 尝试使用predict方法
                result = paddle_ocr.predict(img_rgb)
                print(f"  predict返回类型: {type(result)}")
                print(f"  predict返回内容: {result}")
            except AttributeError:
                # 如果predict不存在，使用ocr方法
                print("  predict方法不存在，使用ocr方法")
                result = paddle_ocr.ocr(img_rgb)
                print(f"  ocr返回类型: {type(result)}")
                print(f"  ocr返回内容: {result}")
            except Exception as e:
                print(f"  识别出错: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            # 处理结果：新API返回格式是OCRResult对象列表
            if result:
                texts = []
                print(f"\n  处理结果...")
                print(f"  结果类型: {type(result)}")
                
                # 新API返回的是OCRResult对象列表
                if isinstance(result, list) and len(result) > 0:
                    print(f"  结果列表长度: {len(result)}")
                    for i, item in enumerate(result):
                        print(f"    第{i}项: 类型={type(item)}")
                        # OCRResult对象有rec_texts属性，直接访问
                        if hasattr(item, 'rec_texts') and item.rec_texts:
                            print(f"      rec_texts: {item.rec_texts}")
                            texts.extend(item.rec_texts)
                        elif hasattr(item, 'get') and isinstance(item, dict):
                            # 如果是字典格式，尝试获取rec_texts
                            if 'rec_texts' in item:
                                rec_texts = item['rec_texts']
                                print(f"      rec_texts (dict): {rec_texts}")
                                if isinstance(rec_texts, list):
                                    texts.extend(rec_texts)
                                elif rec_texts:
                                    texts.append(str(rec_texts))
                
                ocr_text = '\n'.join(texts).strip()
                if ocr_text:
                    print(f"\n  ✓ 识别成功:")
                    print(f"  {ocr_text}")
                else:
                    print(f"\n  ✗ 未识别到文本")
            else:
                print(f"\n  ✗ PaddleOCR返回空结果")
                
        except Exception as e:
            print(f"  处理图片时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_paddleocr_on_temp_images()
