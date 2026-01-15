"""
OCR处理和图像捕获模块
"""
import os
import re
import time
import threading
import logging
import traceback
import numpy as np
import cv2
import pytesseract
from PIL import Image
from ocr import direct_ocr


class OCRProcessor:
    """OCR处理器"""

    def __init__(self):
        self.ocr_lock = threading.Lock()
        self.ocr_cache = {}  # 图像hash -> OCR文本
        self.match_cache = {}  # OCR文本 -> 匹配结果
        self.ocr_cache_max_size = 20
        self.match_cache_max_size = 50
        self.last_image = None  # 保存最后一次OCR的原始图像，用于匹配失败时的微调
        self.last_region_type = None  # 保存最后一次OCR的区域类型
        # 是否保存调试截图到磁盘（默认关闭，避免按住Ctrl产生大量temp文件）
        self.enable_debug_screenshot = False
        # 微调方法统计：记录每个方法的成功次数和总尝试次数
        self.micro_adjustment_stats = {
            'balanced': {'success': 0, 'total': 0},
            'accurate': {'success': 0, 'total': 0},
            'fast': {'success': 0, 'total': 0},
            'crop_edge': {'success': 0, 'total': 0},
            'contrast_up': {'success': 0, 'total': 0},
            'brightness_up': {'success': 0, 'total': 0},
            'sharpen': {'success': 0, 'total': 0},
            'gamma_up': {'success': 0, 'total': 0},
            'scale_up': {'success': 0, 'total': 0},
            'contrast_down': {'success': 0, 'total': 0},
            'brightness_down': {'success': 0, 'total': 0},
        }

    def preprocess_image(self, img, method='balanced'):
        """图像预处理优化，提高OCR识别质量
        
        Args:
            img: 输入图像
            method: 预处理方法
                - 'fast': 原始图像（最快）
                - 'balanced': 直方图均衡化+Padding（平衡模式，测试中匹配次数最多）
                - 'accurate': 去噪+CLAHE+Padding（最准确，测试中表现最好）
                - 'complex_border': 去噪+CLAHE+自适应阈值+形态学操作（专门处理复杂边框和装饰元素）
        """
        try:
            if method == 'fast':
                # 快速模式：只转换为灰度图
                if len(img.shape) == 3:
                    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                return img.copy()
                
            elif method == 'balanced':
                # 平衡模式：直方图均衡化 + Padding（测试中匹配次数最多）
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
                # 直方图均衡化
                equalized = cv2.equalizeHist(gray)
                
                # 添加白色边框（Padding）消除边界效应
                height, width = equalized.shape
                pad_size = max(20, int(min(width, height) * 0.1))
                padded = cv2.copyMakeBorder(
                    equalized, 
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT, 
                    value=255
                )
                
                return padded
                
            elif method == 'accurate':
                # 准确模式：去噪+CLAHE增强+Padding（测试中分数最高）
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
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
                
            elif method == 'complex_border':
                # 复杂边框模式：专门处理复杂边框和装饰元素
                # 针对右侧怪物卡片的复杂边框优化
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
                # 1. 强去噪处理（针对复杂边框的噪声）
                denoised = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)  # 增强去噪强度
                
                # 2. 高斯模糊平滑（减少边框线条干扰）
                blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
                
                # 3. CLAHE增强对比度（先增强对比度，有助于后续处理）
                clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))  # 稍微增强对比度
                enhanced = clahe.apply(blurred)
                
                # 4. 尝试OTSU二值化（可能比自适应阈值更适合复杂背景）
                _, otsu_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # 5. 也尝试自适应阈值（作为备选）
                adaptive_thresh = cv2.adaptiveThreshold(
                    enhanced, 
                    255, 
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 
                    15,  # 增大块大小，更好地处理复杂背景
                    3    # 增大常数C
                )
                
                # 6. 结合两种二值化结果（取交集，保留两者都认为是文字的部分）
                combined = cv2.bitwise_and(otsu_thresh, adaptive_thresh)
                
                # 7. 形态学操作：去除小的装饰元素和噪声
                # 使用开运算去除小的装饰点和线条，同时保持文字完整性
                kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                opened = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_small, iterations=1)
                
                # 8. 闭运算：连接文字笔画，去除小间隙
                kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close, iterations=1)
                
                # 9. 添加白色边框（Padding）消除边界效应
                height, width = closed.shape
                pad_size = max(20, int(min(width, height) * 0.1))
                padded = cv2.copyMakeBorder(
                    closed,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                return padded
            
            elif method == 'complex_border_enhanced':
                # 增强版复杂边框处理：更强的去噪和形态学操作
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
                # 1. 超强去噪（深度处理专用）
                denoised = cv2.fastNlMeansDenoising(gray, None, 20, 7, 21)
                
                # 2. 多次高斯模糊（更强平滑）
                blurred1 = cv2.GaussianBlur(denoised, (5, 5), 0)
                blurred2 = cv2.GaussianBlur(blurred1, (3, 3), 0)
                
                # 3. 更强的CLAHE增强
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(blurred2)
                
                # 4. 多种二值化方法结合
                _, otsu_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                adaptive1 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
                adaptive2 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 5)
                
                # 5. 结合多种二值化结果
                combined = cv2.bitwise_and(otsu_thresh, adaptive1)
                combined = cv2.bitwise_and(combined, adaptive2)
                
                # 6. 更强的形态学操作
                kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                opened = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open, iterations=2)
                kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close, iterations=2)
                
                # 7. 添加更大的Padding
                height, width = closed.shape
                pad_size = max(30, int(min(width, height) * 0.15))
                padded = cv2.copyMakeBorder(
                    closed,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                return padded
            
            elif method == 'aggressive_denoise':
                # 强去噪模式：专门处理噪声严重的图像
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
                # 1. 多次去噪
                denoised1 = cv2.fastNlMeansDenoising(gray, None, 25, 7, 21)
                denoised2 = cv2.fastNlMeansDenoising(denoised1, None, 20, 7, 21)
                
                # 2. 双边滤波（保留边缘的同时去噪）
                filtered = cv2.bilateralFilter(denoised2, 9, 75, 75)
                
                # 3. CLAHE增强
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(filtered)
                
                # 4. OTSU二值化
                _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # 5. 形态学操作
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
                
                # 6. Padding
                height, width = closed.shape
                pad_size = max(25, int(min(width, height) * 0.12))
                padded = cv2.copyMakeBorder(
                    closed,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                return padded
            
            elif method == 'hsv_gold_text':
                # HSV空间精准抠图 - 针对淡黄色/米色文字（如"辣火狂徒"）
                # 1. 极大倍率放大（4倍，牺牲速度换精度）
                if len(img.shape) == 3:
                    # 确保是BGR格式（OpenCV默认）
                    if img.shape[2] == 3:
                        img_bgr = img.copy()
                    else:
                        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                else:
                    # 如果是灰度图，先转换为BGR
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                
                # 放大图像
                img_large = cv2.resize(img_bgr, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
                
                # 2. 转换到HSV空间
                hsv = cv2.cvtColor(img_large, cv2.COLOR_BGR2HSV)
                
                # 3. 设定文字颜色的HSV范围（淡黄色/橙色）
                # 这能过滤掉左侧红色的头像背景和底部的黑色框
                lower_gold = np.array([10, 20, 150])
                upper_gold = np.array([30, 150, 255])
                mask = cv2.inRange(hsv, lower_gold, upper_gold)
                
                # 4. 中值滤波去噪（消除背景碎点）
                mask = cv2.medianBlur(mask, 3)
                
                # 5. 反转颜色：Tesseract识别"白底黑字"最准
                final_img = cv2.bitwise_not(mask)
                
                # 6. 添加Padding
                height, width = final_img.shape
                pad_size = max(30, int(min(width, height) * 0.1))
                padded = cv2.copyMakeBorder(
                    final_img,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                return padded
            
            elif method == 'multi_threshold':
                # 多阈值遍历法 - 遍历不同的二值化阈值（从100到200，步长10）
                # 注意：这个方法返回第一个阈值的结果，实际遍历在deep_ocr_processing中完成
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img.copy()
                
                # 使用默认阈值（150）作为示例
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                
                # 添加Padding
                height, width = thresh.shape
                pad_size = max(20, int(min(width, height) * 0.1))
                padded = cv2.copyMakeBorder(
                    thresh,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                return padded
                
            else:
                # 默认使用平衡模式
                return self.preprocess_image(img, 'balanced')

        except Exception as e:
            logging.error(f"图像预处理失败: {e}")
            logging.error(traceback.format_exc())
            try:
                if len(img.shape) == 3:
                    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                return img.copy()
            except BaseException:
                return img

    def get_game_tesseract_config(self, mode='balanced', psm_override=None):
        """
        游戏专用Tesseract配置 - 基于全面测试结果优化
        
        测试结果统计（35张图片）：
        - 最佳组合：直方图均衡化 + PSM11_OEM1（匹配34次，成功率97.1%）
        - 次佳组合：去噪+增强+Padding + PSM11_OEM1（匹配28次，成功率80%）
        - 所有组合使用PSM11_OEM1共匹配220次
        
        mode: 'fast' - 最快速度（原始图像+PSM11+OEM1）
              'balanced' - 平衡模式（直方图均衡化+PSM11+OEM1，推荐，成功率97.1%）
              'accurate' - 最高准确率（去噪+CLAHE+Padding+PSM11+OEM1，稍慢）
              'line_text' - 单行文字模式（PSM7+OEM1，针对短文本+特定字体）
        psm_override: 如果指定，覆盖默认PSM值（用于深度处理）
        """
        # 如果指定了PSM覆盖，使用它
        if psm_override:
            psm = str(psm_override)
        else:
            configs_psm = {
                'fast': '11',
                'balanced': '11',
                'accurate': '11',
                'line_text': '7'  # 单行文字模式
            }
            psm = configs_psm.get(mode, '11')
        
        configs = {
            'fast': {
                'psm': psm,
                'oem': '1',
                'config': f'--oem 1 --psm {psm} -c preserve_interword_spaces=1'
            },
            'balanced': {
                'psm': psm,
                'oem': '1',
                'config': f'--oem 1 --psm {psm} -c preserve_interword_spaces=1'
            },
            'accurate': {
                'psm': psm,
                'oem': '1',
                'config': f'--oem 1 --psm {psm} -c preserve_interword_spaces=1'
            },
            'line_text': {
                'psm': '7',
                'oem': '1',
                'config': '--oem 1 --psm 7 -c preserve_interword_spaces=1'
            }
        }
        return configs.get(mode, configs['balanced'])

    def _evaluate_text_quality(self, text):
        """评估OCR文本质量
        
        Returns:
            (quality_score, is_good): quality_score范围0-1，is_good表示是否质量足够好
        """
        if not text or not text.strip():
            return 0.0, False
        
        # 提取纯中文字符
        chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', text)
        total_chars = len(re.sub(r'\s', '', text))  # 总字符数（不含空格）
        
        if total_chars == 0:
            return 0.0, False
        
        # 1. 中文字符比例（权重40%）
        chinese_ratio = len(chinese_chars) / total_chars if total_chars > 0 else 0
        
        # 2. 中文字符数量（权重30%）
        # 怪物名称通常2-6个中文字符
        chinese_count_score = min(len(chinese_chars) / 4.0, 1.0)  # 4个中文字符为满分
        
        # 3. 检测明显错误模式（权重30%）
        # 检查是否包含大量单个字母、数字、无意义组合
        error_patterns = [
            r'\b[A-Z]{1,2}\s+[A-Z]{1,2}\b',  # 多个单字母或双字母组合（如"CC AAA"）
            r'\b\d+\s+\d+\b',  # 多个数字组合（如"1 2"）
            r'[A-Z]{3,}',  # 连续3个以上大写字母（可能是错误识别）
            r'\b[A-Z]{2}\s+[A-Z]{2}\s+[A-Z]{2}\b',  # 多个双字母组合（如"ER AR"）
        ]
        error_score = 1.0
        for pattern in error_patterns:
            matches = len(re.findall(pattern, text))
            if matches > 0:
                error_score -= min(matches * 0.25, 0.7)  # 每个错误模式最多扣0.7分，提高惩罚力度
        
        # 综合评分
        quality_score = (chinese_ratio * 0.4 + chinese_count_score * 0.3 + max(error_score, 0) * 0.3)
        
        # 判断是否质量足够好
        # 关键改进：
        # 1. 如果没有中文字符，即使评分高也标记为质量不好
        # 2. 如果中文字符数量太少（<2个），也标记为质量不好
        # 3. 如果中文字符比例太低（<0.3），也标记为质量不好
        # 4. 如果综合评分太低（<0.5），也标记为质量不好（提高阈值）
        has_chinese = len(chinese_chars) > 0
        is_good = (has_chinese and 
                   chinese_ratio > 0.3 and 
                   len(chinese_chars) >= 2 and 
                   quality_score > 0.5)  # 提高阈值，更严格的质量要求
        
        return quality_score, is_good

    def _clean_ocr_text(self, text):
        """清理OCR结果，移除明显错误的字符"""
        if not text:
            return ""

        # 1. 移除游戏文本中不常见的特殊字符
        text = re.sub(r'[{}[\]()<>`~!@#$%^&*_+=;:"\',.?\\|]', '', text)

        # 2. 合并过多的空格
        text = re.sub(r'\s{2,}', ' ', text)

        # 3. 移除首尾空白
        text = text.strip()

        # 4. 移除纯数字的短行（通常是游戏UI的干扰）
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # 如果整行都是数字且长度短，可能是干扰
                if len(line) < 4 and line.isdigit():
                    continue
                # 如果行太长（超过40字符），可能是识别错误，截断
                if len(line) > 40:
                    line = line[:40] + "..."
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def ocr_for_game(
            self,
            img_array,
            mode='balanced',
            region_type='monster',
            use_preprocess=True,
            psm_override=None):
        """
        游戏专用OCR - 使用测试验证的最佳配置
        
        基于35张图片的全面测试结果：
        - 最佳组合：直方图均衡化 + PSM11_OEM1（成功率97.1%）
        - 所有模式使用PSM11_OEM1配置
        
        Args:
            img_array: 输入图像
            mode: OCR模式
                - 'fast': 最快速度（原始图像）
                - 'balanced': 平衡模式（直方图均衡化，推荐）
                - 'accurate': 最高准确率（去噪+CLAHE+Padding）
                - 'line_text': 单行文字模式（PSM7+OEM1）
            region_type: 区域类型（monster/event）
            use_preprocess: 是否使用预处理（默认True）
            psm_override: 如果指定，覆盖默认PSM值（用于深度处理）
        """
        try:
            # 根据区域类型选择模式
            if region_type == 'monster':
                # 怪物名称通常较短，使用平衡模式
                if mode == 'balanced':
                    preprocess_method = 'balanced'
                elif mode == 'accurate':
                    preprocess_method = 'accurate'
                else:
                    preprocess_method = 'fast'
            else:
                # 事件描述可能较长，使用准确模式
                if mode == 'balanced' or mode == 'accurate':
                    preprocess_method = 'accurate'
                else:
                    preprocess_method = 'balanced'

            config = self.get_game_tesseract_config(mode, psm_override=psm_override)

            # 图像预处理
            if isinstance(img_array, np.ndarray):
                if use_preprocess:
                    processed_img = self.preprocess_image(img_array, preprocess_method)
                else:
                    # 如果不使用预处理，只转换为灰度图
                    if len(img_array.shape) == 3:
                        processed_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    else:
                        processed_img = img_array.copy()
                
                pil_img = Image.fromarray(processed_img)
            else:
                pil_img = img_array

            # 执行OCR
            start_time = time.time()
            text = pytesseract.image_to_string(
                pil_img,
                lang='chi_sim',
                config=config['config']
            )
            ocr_time = time.time() - start_time

            # 清理结果
            text = self._clean_ocr_text(text)

            if text:
                logging.info(
                    f"[游戏OCR] 模式={mode}, 预处理={preprocess_method}, "
                    f"耗时={ocr_time:.3f}s, 结果={repr(text[:100])}")

            return text

        except Exception as e:
            logging.error(f"游戏OCR失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def ocr_for_item(self, img_array):
        """
        物品专用OCR - 使用 image_to_data 获取文字大小，选取最大的中文文字
        目标文字（物品名称）是所有文字中字体最大的前几名
        """
        try:
            import pandas as pd
            
            # 转换图像格式
            if isinstance(img_array, np.ndarray):
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    pil_img = Image.fromarray(img_array)
                elif len(img_array.shape) == 2:
                    pil_img = Image.fromarray(img_array)
                else:
                    pil_img = Image.fromarray(
                        cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
            else:
                pil_img = img_array

            # 使用 image_to_data 获取详细信息
            start_time = time.time()
            config = self.get_game_tesseract_config('balanced')
            data = pytesseract.image_to_data(
                pil_img,
                lang='chi_sim',
                config=config['config'],
                output_type=pytesseract.Output.DICT
            )
            ocr_time = time.time() - start_time

            # 提取文字及其高度信息
            text_items = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if not text:
                    continue
                height = data['height'][i]
                width = data['width'][i]
                conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                
                # 只保留置信度大于0的结果
                if conf > 0:
                    text_items.append({
                        'text': text,
                        'height': height,
                        'width': width,
                        'conf': conf,
                        'area': height * width
                    })

            if not text_items:
                logging.warning("[物品OCR] 未识别到任何文字")
                return None

            # 按高度（字体大小）降序排序
            text_items.sort(key=lambda x: x['height'], reverse=True)
            
            logging.info(f"[物品OCR] 识别到 {len(text_items)} 个文字块，耗时={ocr_time:.3f}s")
            
            # 提取中文字符，按大小排序后选取前5个最大的
            chinese_texts = []
            for item in text_items:
                # 只保留包含中文的文字
                chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', item['text'])
                if chinese_chars:
                    chinese_texts.append({
                        'text': chinese_chars,
                        'height': item['height'],
                        'conf': item['conf']
                    })
                    logging.debug(f"  中文: '{chinese_chars}', 高度: {item['height']}, 置信度: {item['conf']}")
            
            if not chinese_texts:
                logging.warning("[物品OCR] 未识别到中文字符")
                # 回退到普通OCR
                return self.ocr_for_game(img_array, region_type='item')

            # 按高度排序
            chinese_texts.sort(key=lambda x: x['height'], reverse=True)
            
            # 将所有中文拼接起来，供匹配算法使用
            all_chinese = ''.join([t['text'] for t in chinese_texts])
            
            # 前5个最大的作为主要候选
            top_texts = chinese_texts[:5]
            top_combined = ''.join([t['text'] for t in top_texts])
            
            logging.info(f"[物品OCR] 最大字体中文（前5）: {[t['text'] for t in top_texts]}")
            logging.info(f"[物品OCR] 组合文本: '{top_combined}'")
            logging.info(f"[物品OCR] 全部中文({len(chinese_texts)}个): '{all_chinese[:50]}{'...' if len(all_chinese) > 50 else ''}'")
            
            # 返回格式：主要文本|全部文本（用于增强匹配）
            combined_text = f"{top_combined}|{all_chinese}"
            
            return combined_text

        except ImportError:
            logging.warning("[物品OCR] pandas未安装，回退到普通OCR")
            return self.ocr_for_game(img_array, region_type='item')
        except Exception as e:
            logging.error(f"物品OCR失败: {e}")
            logging.error(traceback.format_exc())
            # 回退到普通OCR
            return self.ocr_for_game(img_array, region_type='item')

    def capture_and_ocr(self, area, region_type='monster'):
        """捕获指定区域并进行OCR识别（包含截图保存功能）"""
        try:
            import tempfile
            import sys
            from PIL import ImageGrab
            
            # 捕获指定区域
            x1, y1, x2, y2 = area
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            
            # 如需调试时保存截图到磁盘，可打开 enable_debug_screenshot 开关
            if getattr(self, "enable_debug_screenshot", False):
                try:
                    # 获取项目根目录
                    if getattr(sys, 'frozen', False):
                        # 打包环境：使用可执行文件所在目录
                        base_dir = os.path.dirname(os.path.abspath(sys.executable))
                    else:
                        # 开发环境：使用项目根目录（main_script的父目录）
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    
                    temp_dir = os.path.join(base_dir, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    timestamp = int(time.time() * 1000)  # 毫秒时间戳
                    screenshot_path = os.path.join(
                        temp_dir, f"debug_capture_{region_type}_{timestamp}.png")
                    img.save(screenshot_path)
                    logging.info(f"已保存截图: {screenshot_path}")
                except Exception as e:
                    logging.warning(f"保存截图失败: {e}")
            
            # 转换为numpy数组
            img_array = np.array(img)
            
            # 执行OCR
            return self.ocr_for_game(img_array, region_type=region_type)
        except Exception as e:
            logging.error(f"捕获并OCR失败: {e}")
            return None

    def get_text_at_cursor(self, region_type='monster', window_detector=None, position_config=None, skip_checks=False):
        """
        获取鼠标指向位置的文字（完全按照旧脚本逻辑）
        """
        try:
            import win32gui
            import pyautogui
            from PIL import ImageGrab
            import cv2
            
            # 获取游戏窗口
            if window_detector:
                hwnd, window_rect = window_detector.get_game_window()
            else:
                from .window_detector import WindowDetector
                window_detector = WindowDetector()
                hwnd, window_rect = window_detector.get_game_window()
            
            if not hwnd or not window_rect:
                logging.warning("未找到游戏窗口")
                return None
            
            # 额外检查：确保窗口没有最小化（双重保险）
            try:
                import win32gui
                if win32gui.IsIconic(hwnd):
                    logging.warning("游戏窗口已最小化，跳过OCR识别")
                    return None
            except Exception as e:
                logging.debug(f"检查窗口最小化状态失败: {e}")

            # 获取鼠标位置
            cursor_x, cursor_y = win32gui.GetCursorPos()
            
            # 检查窗口坐标有效性
            if len(window_rect) != 4 or window_rect[0] >= window_rect[2] or window_rect[1] >= window_rect[3]:
                logging.error(f"无效的游戏窗口坐标: {window_rect}")
                return None
            
            # 新的截图区域逻辑：以鼠标坐标为(0,0)，使用固定的相对偏移
            # 屏幕坐标系说明（左上角为原点，y轴向下）：
            # - x轴：向右为正，向左为负
            # - y轴：向下为正，向上为负
            # 
            # 偏移量设置规则：
            # - 鼠标右侧：使用正数（如 200）
            # - 鼠标左侧：使用负数（如 -50）
            # - 鼠标下方：使用正数（如 300）
            # - 鼠标上方：使用负数（如 -120）
            #
            # 截图区域计算：
            # - x1 = cursor_x + offset_left  (左边界)
            # - x2 = cursor_x + offset_right (右边界)
            # - y2 = cursor_y + offset_top   (上边界，y值较小，如果为负数则在鼠标上方)
            # - y1 = cursor_y + offset_bottom (下边界，y值较大，如果为负数则在鼠标上方)
            #
            # 注意：在屏幕坐标系中，上边界的y值 < 下边界的y值
            # 所以如果 offset_top < offset_bottom，截图区域在鼠标上方
            # 如果 offset_top > offset_bottom，截图区域在鼠标下方
            if region_type == 'monster':
                # 相对于鼠标的偏移量
                offset_left = 50
                offset_right = 600
                offset_top = -250
                offset_bottom = 20 # 下边界在鼠标下300（屏幕坐标系中y值较大）
                
                # 计算截图区域（以鼠标为参考点）
                # 左边界和上边界（左上角）
                x1 = cursor_x + offset_left
                y2 = cursor_y + offset_top
                # 右边界和下边界（右下角）
                x2 = cursor_x + offset_right
                y1 = cursor_y + offset_bottom
                
                # 确保截图区域在窗口内（可选：如果超出窗口边界，可以裁剪或调整）
                # 这里我们只记录警告，不强制裁剪
                # 截图区域是 (x1, y2, x2, y1)，所以检查 y2（上边界）和 y1（下边界）
                if x1 < window_rect[0] or y2 < window_rect[1] or x2 > window_rect[2] or y1 > window_rect[3]:
                    logging.warning(f"[区域检测] 截图区域部分超出窗口边界: 左上({x1}, {y2}) -> 右下({x2}, {y1}), 窗口: {window_rect}")
                
                logging.info(f"[区域检测] 使用固定相对偏移区域(怪物): 鼠标({cursor_x}, {cursor_y}), 截图区域左上({x1}, {y2}) -> 右下({x2}, {y1}), 尺寸: {x2-x1}x{y1-y2}")
            else:  # region_type == 'item'
                # 物品识别使用固定偏移区域
                offset_left = -1300
                offset_right = 1300
                offset_top = -900
                offset_bottom = 350
                
                x1 = cursor_x + offset_left
                y2 = cursor_y + offset_top
                x2 = cursor_x + offset_right
                y1 = cursor_y + offset_bottom
                
                if x1 < window_rect[0] or y2 < window_rect[1] or x2 > window_rect[2] or y1 > window_rect[3]:
                    logging.warning(f"[区域检测] 截图区域部分超出窗口边界: 左上({x1}, {y2}) -> 右下({x2}, {y1}), 窗口: {window_rect}")
                
                logging.info(f"[区域检测] 使用固定相对偏移区域(物品): 鼠标({cursor_x}, {cursor_y}), 截图区域左上({x1}, {y2}) -> 右下({x2}, {y1}), 尺寸: {x2-x1}x{y1-y2}")

            # 检查截图坐标有效性
            # 注意：x1 < x2（左边界 < 右边界），y2 < y1（上边界y值 < 下边界y值）
            if x1 >= x2 or y2 >= y1:
                logging.warning(f"[区域检测] 截图坐标无效: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                return None

            # 截取区域图像
            # ImageGrab.grab(bbox=(left, top, right, bottom))
            # left=x1, top=y2(上边界，y值较小), right=x2, bottom=y1(下边界，y值较大)
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y2, x2, y1))
            except Exception as e:
                logging.error(f'截图失败: {e}')
                return None
            img_array = np.array(screenshot)
            
            # 保存调试图像到磁盘（可选），默认关闭，避免按住Ctrl时产生大量temp文件
            if getattr(self, "enable_debug_screenshot", False):
                try:
                    debug_img = img_array.copy()
                    # 在调试图像上画一个红色十字光标（鼠标在截图区域中的位置）
                    # 截图区域是 (x1, y2, x2, y1)，所以：
                    # - 鼠标在截图区域中的x坐标：cursor_x - x1
                    # - 鼠标在截图区域中的y坐标：cursor_y - y2（因为y2是上边界，是截图区域的top）
                    mouse_in_region_x = cursor_x - x1
                    mouse_in_region_y = cursor_y - y2
                    cv2.line(debug_img, (mouse_in_region_x-10, mouse_in_region_y), (mouse_in_region_x+10, mouse_in_region_y), (0,0,255), 2)
                    cv2.line(debug_img, (mouse_in_region_x, mouse_in_region_y-10), (mouse_in_region_x, mouse_in_region_y+10), (0,0,255), 2)
                    # 画区域边界（绿色矩形）
                    cv2.rectangle(debug_img, (0, 0), (x2-x1-1, y2-y1-1), (0, 255, 0), 2)
                    
                    import sys
                    # 计算项目根目录（main_script的父目录）
                    if getattr(sys, 'frozen', False):
                        # 打包环境：使用可执行文件所在目录
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        # 开发环境：从 main_script/core/ocr_processor.py 向上3级到项目根目录
                        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    
                    # 保存到根目录的debug_capture.png（会被覆盖，但旧脚本就是这样）
                    debug_path = os.path.join(base_dir, 'debug_capture.png')
                    cv2.imwrite(debug_path, cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
                    logging.info(f"[截图保存] 已保存调试图像: {debug_path}")
                    
                    # 保存带时间戳的截图到项目根目录下的data/temp目录
                    try:
                        temp_dir = os.path.join(base_dir, 'data', 'temp')
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        # 生成时间戳文件名
                        import datetime
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 精确到毫秒
                        screenshot_filename = f'ocr_region_{timestamp}.png'
                        screenshot_path = os.path.join(temp_dir, screenshot_filename)
                        
                        # 保存截图
                        cv2.imwrite(screenshot_path, cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR))
                        logging.info(f"[截图保存] 识别区域截图已保存: {screenshot_path}")
                    except Exception as e:
                        logging.error(f"[截图保存] 保存识别区域截图失败: {e}")
                        logging.error(traceback.format_exc())
                except Exception as e:
                    logging.error(f"保存调试图像失败: {e}")
                    logging.error(traceback.format_exc())
            
            logging.debug(f"截图区域: ({x1}, {y1}) -> ({x2}, {y2}), 尺寸: {x2-x1}x{y2-y1}")
            
            # 保存原始图像，用于匹配失败时的微调
            self.last_image = img_array.copy()
            self.last_region_type = region_type
            
            # OCR识别：根据区域类型选择不同的OCR方法
            if region_type == 'item':
                # 物品识别：使用专用的物品OCR方法，按字体大小选取最大的中文
                text = self.ocr_for_item(img_array)
                if text and text.strip():
                    logging.info(f"[OCR] 物品OCR识别成功: {repr(text[:100])}")
                else:
                    # 回退到普通OCR
                    logging.debug("物品OCR失败，尝试普通OCR")
                    text = self.ocr_for_game(img_array, mode='balanced', region_type=region_type, use_preprocess=False)
            else:
                # 怪物/事件识别：使用普通OCR，并根据文本质量自动尝试其他预处理模式
                text = self.ocr_for_game(img_array, mode='balanced', region_type=region_type, use_preprocess=False)
                quality_score, is_good = self._evaluate_text_quality(text) if text else (0.0, False)
                
                if text and text.strip():
                    logging.info(f"[OCR] 原始图像识别: {repr(text[:100])}, 质量评分: {quality_score:.2f}, 质量良好: {is_good}")
                
                # 如果原始图像失败或质量不好，尝试其他预处理模式
                if not text or not text.strip() or not is_good:
                    if not text or not text.strip():
                        logging.debug("原始图像识别失败，尝试balanced预处理模式")
                    else:
                        logging.debug(f"原始图像识别质量不佳(评分: {quality_score:.2f})，尝试balanced预处理模式")
                    
                    processed_img = self.preprocess_image(img_array, 'balanced')
                    text_balanced = self.ocr_for_game(processed_img, mode='balanced', region_type=region_type, use_preprocess=True)
                    quality_score_balanced, is_good_balanced = self._evaluate_text_quality(text_balanced) if text_balanced else (0.0, False)
                    
                    if text_balanced and text_balanced.strip():
                        logging.info(f"[OCR] balanced模式识别: {repr(text_balanced[:100])}, 质量评分: {quality_score_balanced:.2f}, 质量良好: {is_good_balanced}")
                        # 如果balanced模式质量更好，使用它
                        if quality_score_balanced > quality_score:
                            text = text_balanced
                            quality_score = quality_score_balanced
                            is_good = is_good_balanced
                    
                    # 如果balanced模式仍然失败或质量不好，尝试complex_border模式（针对复杂边框）
                    # 即使balanced模式有结果，如果质量评分仍然较低（<0.5），也尝试complex_border模式
                    should_try_complex = (not text or not text.strip() or not is_good or quality_score < 0.5)
                    if should_try_complex:
                        if not text or not text.strip():
                            logging.debug("balanced模式识别失败，尝试complex_border模式处理复杂边框")
                        else:
                            logging.debug(f"balanced模式质量不佳(评分: {quality_score:.2f})，尝试complex_border模式处理复杂边框")
                        
                        processed_img_complex = self.preprocess_image(img_array, 'complex_border')
                        text_complex = self.ocr_for_game(processed_img_complex, mode='balanced', region_type=region_type, use_preprocess=True)
                        quality_score_complex, is_good_complex = self._evaluate_text_quality(text_complex) if text_complex else (0.0, False)
                        
                        if text_complex and text_complex.strip():
                            logging.info(f"[OCR] complex_border模式识别: {repr(text_complex[:100])}, 质量评分: {quality_score_complex:.2f}, 质量良好: {is_good_complex}")
                            # 如果complex_border模式质量更好，使用它
                            if quality_score_complex > quality_score:
                                text = text_complex
                                quality_score = quality_score_complex
                                is_good = is_good_complex
                        
                        # 最后尝试accurate模式
                        if not text or not text.strip() or not is_good:
                            if not text or not text.strip():
                                logging.debug("complex_border模式失败，尝试accurate模式")
                            else:
                                logging.debug(f"complex_border模式质量不佳(评分: {quality_score:.2f})，尝试accurate模式")
                            
                            processed_img_accurate = self.preprocess_image(img_array, 'accurate')
                            text_accurate = self.ocr_for_game(processed_img_accurate, mode='accurate', region_type=region_type, use_preprocess=True)
                            quality_score_accurate, is_good_accurate = self._evaluate_text_quality(text_accurate) if text_accurate else (0.0, False)
                            
                            if text_accurate and text_accurate.strip():
                                logging.info(f"[OCR] accurate模式识别: {repr(text_accurate[:100])}, 质量评分: {quality_score_accurate:.2f}, 质量良好: {is_good_accurate}")
                                # 如果accurate模式质量更好，使用它
                                if quality_score_accurate > quality_score:
                                    text = text_accurate
                                    quality_score = quality_score_accurate
                                    is_good = is_good_accurate
                
                # 关键改进：如果最终结果仍然质量不好，自动触发深度处理
                # 这符合用户需求：失败时牺牲速度换质量
                if text and text.strip():
                    final_quality_score, final_is_good = self._evaluate_text_quality(text)
                    chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', text)
                    has_chinese = len(chinese_chars) > 0
                    
                    # 触发深度处理的条件：
                    # 1. 没有中文字符
                    # 2. 质量评估认为不好
                    # 3. 中文字符数量少于2个（即使有中文，但太少也无法匹配）
                    # 4. 质量评分低于0.6（更严格，确保有足够质量才不触发深度处理）
                    should_trigger_deep = (not has_chinese or 
                                          not final_is_good or 
                                          len(chinese_chars) < 2 or 
                                          final_quality_score < 0.6)
                    
                    if should_trigger_deep:
                        logging.warning(f"[OCR] 最终结果质量不佳(评分: {final_quality_score:.2f}, 有中文: {has_chinese}, 中文数: {len(chinese_chars)})，触发深度OCR处理...")
                        deep_text = self.deep_ocr_processing(img_array, region_type)
                        if deep_text:
                            deep_quality_score, deep_is_good = self._evaluate_text_quality(deep_text)
                            deep_chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', deep_text)
                            deep_has_chinese = len(deep_chinese_chars) > 0
                            
                            # 如果深度处理结果更好（有中文字符且质量更好），使用它
                            if deep_has_chinese and (deep_quality_score > final_quality_score or not has_chinese or len(deep_chinese_chars) > len(chinese_chars)):
                                logging.info(f"[OCR] 深度处理成功，使用深度处理结果: {repr(deep_text[:100])}, 质量评分: {deep_quality_score:.2f}")
                                text = deep_text
                            else:
                                logging.info(f"[OCR] 深度处理未改善结果，保持原结果")
            
            return text.strip() if text else None
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def deep_ocr_processing(self, img_array, region_type='monster'):
        """
        深度OCR处理 - 在匹配失败时使用，牺牲速度换取质量
        尝试多种预处理方法和OCR配置，找到最佳结果
        
        新增方法：
        1. HSV空间精准抠图（针对淡黄色/米色文字）
        2. 多阈值遍历法（遍历不同二值化阈值）
        3. Tesseract PSM7配置（单行文字模式）
        
        Args:
            img_array: 原始图像数组
            region_type: 区域类型（'monster'/'event'/'item'）
        
        Returns:
            最佳OCR结果文本，如果所有尝试都失败则返回None
        """
        logging.info("[深度OCR] 开始深度处理，尝试多种预处理方法...")
        best_text = None
        best_score = 0.0
        
        # 深度处理方法列表（按优先级排序）
        # 格式：(预处理方法, OCR模式, PSM覆盖值)
        deep_methods = [
            ('hsv_gold_text', 'line_text', 7),  # HSV空间精准抠图 + PSM7（针对淡黄色文字）
            ('complex_border', 'balanced', None),  # 复杂边框处理
            ('accurate', 'accurate', None),       # 精确模式
            ('complex_border_enhanced', 'balanced', None),  # 增强版复杂边框
            ('aggressive_denoise', 'balanced', None),      # 强去噪模式
        ]
        
        for method_idx, method_info in enumerate(deep_methods, 1):
            try:
                if len(method_info) == 3:
                    preprocess_method, ocr_mode, psm_override = method_info
                else:
                    preprocess_method, ocr_mode = method_info
                    psm_override = None
                
                logging.info(f"[深度OCR] 尝试方法 {method_idx}/{len(deep_methods)}: {preprocess_method} + {ocr_mode}" + (f" (PSM{psm_override})" if psm_override else ""))
                
                # 预处理图像
                processed_img = self.preprocess_image(img_array, preprocess_method)
                
                # OCR识别（使用PSM覆盖）
                text = self.ocr_for_game(processed_img, mode=ocr_mode, region_type=region_type, use_preprocess=True, psm_override=psm_override)
                
                if text and text.strip():
                    # 评估质量
                    quality_score, is_good = self._evaluate_text_quality(text)
                    logging.info(f"[深度OCR] 方法 {method_idx} 结果: {repr(text[:100])}, 质量评分: {quality_score:.2f}, 质量良好: {is_good}")
                    
                    # 如果质量更好，更新最佳结果
                    if quality_score > best_score:
                        best_text = text
                        best_score = quality_score
                        
                        # 如果质量足够好，提前返回
                        if is_good and quality_score > 0.7:
                            logging.info(f"[深度OCR] 找到高质量结果，提前结束深度处理")
                            return best_text.strip()
            except Exception as e:
                logging.warning(f"[深度OCR] 方法 {method_idx} 失败: {e}")
                continue
        
        # 如果前面的方法都失败，尝试多阈值遍历法
        if not best_text or best_score < 0.5:
            logging.info("[深度OCR] 尝试多阈值遍历法（遍历不同二值化阈值）...")
            multi_threshold_text = self._multi_threshold_ocr(img_array, region_type)
            if multi_threshold_text:
                multi_score, _ = self._evaluate_text_quality(multi_threshold_text)
                logging.info(f"[深度OCR] 多阈值遍历结果: {repr(multi_threshold_text[:100])}, 质量评分: {multi_score:.2f}")
                if multi_score > best_score:
                    best_text = multi_threshold_text
                    best_score = multi_score
        
        if best_text:
            logging.info(f"[深度OCR] 深度处理完成，最佳结果: {repr(best_text[:100])}, 质量评分: {best_score:.2f}")
        else:
            logging.warning("[深度OCR] 所有深度处理方法均失败")
        
        return best_text.strip() if best_text else None
    
    def _multi_threshold_ocr(self, img_array, region_type='monster'):
        """
        多阈值遍历法 - 遍历不同的二值化阈值（从100到200，步长为10）
        只要有一个版本匹配到词库，就算成功
        
        Args:
            img_array: 原始图像数组
            region_type: 区域类型
        
        Returns:
            最佳OCR结果文本，如果所有尝试都失败则返回None
        """
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        best_text = None
        best_score = 0.0
        
        # 遍历阈值：从100到200，步长10
        thresholds = range(100, 210, 10)
        logging.info(f"[多阈值遍历] 开始遍历 {len(thresholds)} 个阈值: {list(thresholds)}")
        
        for threshold in thresholds:
            try:
                # 二值化
                _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
                
                # 添加Padding
                height, width = thresh.shape
                pad_size = max(20, int(min(width, height) * 0.1))
                padded = cv2.copyMakeBorder(
                    thresh,
                    pad_size, pad_size, pad_size, pad_size,
                    cv2.BORDER_CONSTANT,
                    value=255
                )
                
                # OCR识别（使用PSM7，单行文字模式）
                pil_img = Image.fromarray(padded)
                config = self.get_game_tesseract_config('line_text')
                text = pytesseract.image_to_string(
                    pil_img,
                    lang='chi_sim',
                    config=config['config']
                )
                
                if text and text.strip():
                    text = self._clean_ocr_text(text)
                    quality_score, is_good = self._evaluate_text_quality(text)
                    
                    logging.debug(f"[多阈值遍历] 阈值={threshold}: {repr(text[:50])}, 质量评分: {quality_score:.2f}, 质量良好: {is_good}")
                    
                    # 如果质量更好，更新最佳结果
                    if quality_score > best_score:
                        best_text = text
                        best_score = quality_score
                        
                        # 如果质量足够好，提前返回
                        if is_good and quality_score > 0.7:
                            logging.info(f"[多阈值遍历] 阈值={threshold}找到高质量结果，提前结束遍历")
                            return best_text
                
            except Exception as e:
                logging.debug(f"[多阈值遍历] 阈值={threshold}失败: {e}")
                continue
        
        if best_text:
            logging.info(f"[多阈值遍历] 遍历完成，最佳阈值结果: {repr(best_text[:100])}, 质量评分: {best_score:.2f}")
        
        return best_text
    
    def _adjust_image_micro(self, img, adjustment_type):
        """
        对图像进行微调操作（不改变预处理方法）
        
        Args:
            img: 原始图像
            adjustment_type: 微调类型
                - 'contrast_up': 轻微提高对比度
                - 'contrast_down': 轻微降低对比度
                - 'brightness_up': 轻微提高亮度
                - 'brightness_down': 轻微降低亮度
                - 'gamma_up': 轻微提高gamma
                - 'gamma_down': 轻微降低gamma
                - 'sharpen': 轻微锐化
                - 'crop_edge': 轻微裁剪边缘（去除1-2%的边缘）
                - 'scale_up': 轻微放大（1-2%）
                - 'scale_down': 轻微缩小（1-2%）
        
        Returns:
            微调后的图像
        """
        try:
            if img is None:
                return None
            
            # 确保是RGB格式
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            
            result = img.copy()
            
            if adjustment_type == 'contrast_up':
                # 轻微提高对比度（1.05倍）
                result = cv2.convertScaleAbs(result, alpha=1.05, beta=0)
            elif adjustment_type == 'contrast_down':
                # 轻微降低对比度（0.95倍）
                result = cv2.convertScaleAbs(result, alpha=0.95, beta=0)
            elif adjustment_type == 'brightness_up':
                # 轻微提高亮度（+5）
                result = cv2.convertScaleAbs(result, alpha=1.0, beta=5)
            elif adjustment_type == 'brightness_down':
                # 轻微降低亮度（-5）
                result = cv2.convertScaleAbs(result, alpha=1.0, beta=-5)
            elif adjustment_type == 'gamma_up':
                # 轻微提高gamma（1.1）
                gamma = 1.1
                inv_gamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                result = cv2.LUT(result, table)
            elif adjustment_type == 'gamma_down':
                # 轻微降低gamma（0.9）
                gamma = 0.9
                inv_gamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                result = cv2.LUT(result, table)
            elif adjustment_type == 'sharpen':
                # 轻微锐化
                kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]]) * 0.1  # 轻微锐化
                result = cv2.filter2D(result, -1, kernel)
                result = np.clip(result, 0, 255).astype(np.uint8)
            elif adjustment_type == 'crop_edge':
                # 轻微裁剪边缘（去除1%的边缘）
                h, w = result.shape[:2]
                crop_h = int(h * 0.01)
                crop_w = int(w * 0.01)
                result = result[crop_h:h-crop_h, crop_w:w-crop_w]
            elif adjustment_type == 'scale_up':
                # 轻微放大（1.02倍）
                h, w = result.shape[:2]
                result = cv2.resize(result, (int(w * 1.02), int(h * 1.02)), interpolation=cv2.INTER_LANCZOS4)
            elif adjustment_type == 'scale_down':
                # 轻微缩小（0.98倍）
                h, w = result.shape[:2]
                result = cv2.resize(result, (int(w * 0.98), int(h * 0.98)), interpolation=cv2.INTER_LANCZOS4)
            
            return result
            
        except Exception as e:
            logging.warning(f"[图像微调] {adjustment_type}失败: {e}")
            return img
    
    def retry_ocr_with_micro_adjustments(self, region_type='monster', matcher=None):
        """
        在匹配失败时，对原始图像进行微调并重新OCR
        使用固定的预处理方法（balanced + PSM11 + OEM1）
        
        Args:
            region_type: 区域类型
            matcher: 文本匹配器，用于立即检查匹配结果
        
        Returns:
            (最佳OCR结果文本, 匹配结果元组), 如果所有尝试都失败则返回(None, None)
            匹配结果元组: (match_type, match_name) 或 (None, None)
        """
        if self.last_image is None:
            logging.warning("[图像微调] 没有保存的原始图像，无法进行微调")
            return None, None
        
        logging.info("[图像微调] 开始对原始图像进行微调并重新OCR...")
        best_text = None
        best_score = 0.0
        best_match = (None, None)
        
        # 微调类型列表（按优先级排序）
        # 只使用轻微的调整，避免过度改变图像
        micro_adjustments = [
            'crop_edge',      # 裁剪边缘（去除背景干扰）
            'contrast_up',    # 提高对比度
            'brightness_up',  # 提高亮度
            'sharpen',        # 锐化
            'gamma_up',       # 提高gamma
            'scale_up',       # 轻微放大
            'contrast_down',  # 降低对比度
            'brightness_down', # 降低亮度
        ]
        
        # 辅助函数：尝试OCR并立即匹配
        def try_ocr_and_match(img, method_name, ocr_mode='balanced', use_preprocess=True):
            """尝试OCR并立即匹配，如果匹配成功则返回结果"""
            nonlocal best_text, best_score, best_match
            
            try:
                text = self.ocr_for_game(img, mode=ocr_mode, region_type=region_type, use_preprocess=use_preprocess)
                if not text or not text.strip():
                    return False
                
                # 评估质量
                score, is_good = self._evaluate_text_quality(text)
                logging.info(f"[图像微调] {method_name}: {repr(text[:100])}, 质量评分: {score:.2f}, 质量良好: {is_good}")
                
                # 更新统计
                if method_name in self.micro_adjustment_stats:
                    self.micro_adjustment_stats[method_name]['total'] += 1
                
                # 如果质量足够好（>=0.6），立即尝试匹配
                if score >= 0.6 and matcher:
                    match_type, match_name = matcher.find_best_match(text)
                    if match_type and match_name:
                        # 匹配成功！立即返回
                        logging.info(f"[图像微调] {method_name}找到匹配结果: {match_type} - {match_name}, 质量评分: {score:.2f}")
                        if method_name in self.micro_adjustment_stats:
                            self.micro_adjustment_stats[method_name]['success'] += 1
                        return (text, (match_type, match_name))
                
                # 更新最佳结果
                if score > best_score:
                    best_text = text
                    best_score = score
                    # 即使没有立即匹配成功，也尝试匹配一次
                    if matcher:
                        match_type, match_name = matcher.find_best_match(text)
                        if match_type and match_name:
                            best_match = (match_type, match_name)
                            # 如果匹配成功且质量足够好，立即返回
                            if score >= 0.7:
                                logging.info(f"[图像微调] {method_name}找到高质量匹配结果: {match_type} - {match_name}, 质量评分: {score:.2f}")
                                if method_name in self.micro_adjustment_stats:
                                    self.micro_adjustment_stats[method_name]['success'] += 1
                                return (text, (match_type, match_name))
                
                return False
                
            except Exception as e:
                logging.debug(f"[图像微调] {method_name}失败: {e}")
                return False
        
        # 首先尝试原始图像（使用balanced预处理）
        result = try_ocr_and_match(self.last_image, 'balanced', ocr_mode='balanced', use_preprocess=True)
        if result:
            return result
        
        # 尝试accurate预处理
        result = try_ocr_and_match(self.last_image, 'accurate', ocr_mode='accurate', use_preprocess=True)
        if result:
            return result
        
        # 尝试fast预处理（原始图像）
        result = try_ocr_and_match(self.last_image, 'fast', ocr_mode='fast', use_preprocess=True)
        if result:
            return result
        
        # 对每个微调类型进行尝试
        for adj_type in micro_adjustments:
            try:
                # 微调图像
                adjusted_img = self._adjust_image_micro(self.last_image, adj_type)
                if adjusted_img is None:
                    continue
                
                # 尝试OCR并立即匹配
                result = try_ocr_and_match(adjusted_img, adj_type, ocr_mode='balanced', use_preprocess=True)
                if result:
                    return result
                
            except Exception as e:
                logging.debug(f"[图像微调] {adj_type}失败: {e}")
                continue
        
        # 打印统计信息
        if best_text:
            logging.info(f"[图像微调] 微调完成，最佳结果: {repr(best_text[:100])}, 质量评分: {best_score:.2f}")
            if best_match[0]:
                logging.info(f"[图像微调] 最佳结果匹配: {best_match[0]} - {best_match[1]}")
        else:
            logging.warning("[图像微调] 所有微调尝试均失败")
        
        # 打印微调方法统计
        logging.info("[图像微调] 方法统计:")
        for method, stats in self.micro_adjustment_stats.items():
            if stats['total'] > 0:
                success_rate = stats['success'] / stats['total'] * 100
                logging.info(f"  {method}: 成功 {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        return best_text, best_match

    def process_ocr_text(self, ocr_text):
        """处理OCR识别的文本"""
        # TODO: 从Bazaar_Lens.py中提取完整的文本处理逻辑
        # 这个方法可能需要调用TextMatcher进行匹配
        return ocr_text
