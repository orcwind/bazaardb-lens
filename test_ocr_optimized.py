#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全面测试OCR识别 - 尝试多种预处理方法和配置组合"""

import os
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import logging
import re
import time
import json
import difflib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 加载已知的怪物和事件名称（用于验证）
def load_known_names():
    """加载已知的怪物和事件名称"""
    monsters = []
    events = []
    
    # 加载怪物名称
    try:
        with open('data/Json/monsters.json', 'r', encoding='utf-8') as f:
            monster_data = json.load(f)
            monsters = [item.get('name_zh', '') for item in monster_data if item.get('name_zh')]
    except Exception as e:
        logging.warning(f"无法加载怪物数据: {e}")
    
    # 加载事件名称
    try:
        with open('data/Json/events_from_html.json', 'r', encoding='utf-8') as f:
            event_data = json.load(f)
            events = [item.get('name', '') for item in event_data if item.get('name')]
    except Exception as e:
        logging.warning(f"无法加载事件数据: {e}")
    
    return monsters, events

def load_items_data():
    """加载物品数据"""
    items = []
    items_dict = {}
    try:
        with open('data/Json/items.json', 'r', encoding='utf-8') as f:
            items_list = json.load(f)
            for item in items_list:
                name_zh = item.get('name_zh', '')
                if name_zh:
                    items.append(name_zh)
                    items_dict[item.get('name', '')] = item
    except Exception as e:
        logging.warning(f"无法加载物品数据: {e}")
    return items, items_dict

KNOWN_MONSTERS, KNOWN_EVENTS = load_known_names()
KNOWN_ITEMS, ITEMS_DATA = load_items_data()

def fuzzy_match(text, known_list, threshold=0.3):
    """模糊匹配OCR结果与已知名称"""
    if not text or len(text.strip()) < 2:
        return None, 0
    
    text_clean = re.sub(r'\s+', '', text.strip())
    best_match = None
    best_score = 0
    
    for name in known_list:
        name_clean = re.sub(r'\s+', '', name)
        score = difflib.SequenceMatcher(None, text_clean, name_clean).ratio()
        if score > best_score:
            best_score = score
            best_match = name
    
    if best_score >= threshold:
        return best_match, best_score
    return None, 0

# ==================== 预处理方法 ====================

def preprocess_method_1_original(img_array):
    """方法1：原始图像（无预处理）"""
    if len(img_array.shape) == 3:
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return img_array.copy()

def preprocess_method_2_clahe(img_array):
    """方法2：CLAHE对比度增强"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def preprocess_method_3_adaptive_thresh(img_array):
    """方法3：自适应阈值"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

def preprocess_method_4_otsu(img_array):
    """方法4：OTSU二值化"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def preprocess_method_5_morphology(img_array):
    """方法5：形态学操作去除阴影"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 顶帽变换去除阴影
    kernel = np.ones((5, 5), np.uint8)
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    
    # CLAHE增强
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(tophat)
    
    # OTSU二值化
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def preprocess_method_6_sharpen(img_array):
    """方法6：锐化处理"""
    if len(img_array.shape) == 3:
        pil_img = Image.fromarray(img_array)
    else:
        pil_img = Image.fromarray(img_array)
    
    # 锐化
    enhancer = ImageEnhance.Sharpness(pil_img)
    sharpened = enhancer.enhance(2.0)
    
    # 对比度增强
    enhancer = ImageEnhance.Contrast(sharpened)
    contrasted = enhancer.enhance(1.5)
    
    return np.array(contrasted)

def preprocess_method_7_denoise(img_array):
    """方法7：去噪 + 对比度增强"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 去噪
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # CLAHE增强
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    return enhanced

def preprocess_method_8_histogram_eq(img_array):
    """方法8：直方图均衡化"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    return cv2.equalizeHist(gray)

def preprocess_method_9_scale_up(img_array):
    """方法9：放大图像（提高分辨率）"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    height, width = gray.shape
    # 放大到至少400x200
    scale = max(400 / width, 200 / height, 2.0)  # 至少放大2倍
    new_width = int(width * scale)
    new_height = int(height * scale)
    scaled = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # CLAHE增强
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(scaled)
    
    return enhanced

def preprocess_method_10_combined(img_array):
    """方法10：组合方法（去噪+形态学+CLAHE+OTSU）"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 去噪
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # 顶帽变换
    kernel = np.ones((3, 3), np.uint8)
    tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT, kernel)
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(tophat)
    
    # OTSU
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 放大
    height, width = binary.shape
    if width < 400 or height < 200:
        scale = max(400 / width, 200 / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        binary = cv2.resize(binary, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    return binary

def preprocess_method_11_hsv_filter(img_array):
    """方法11：HSV颜色过滤 - 提取文字颜色（浅黄色/白色）"""
    if len(img_array.shape) != 3:
        # 如果是灰度图，转换回RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
    
    # 转换到HSV空间
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # 定义文字颜色范围（浅黄色/金色/白色）
    # H: 色调 (0-180), S: 饱和度 (0-255), V: 明度 (0-255)
    # 浅黄色/金色: H在15-30之间，S较低，V较高
    # 白色: S很低，V很高
    
    # 创建掩码：提取浅黄色/金色文字
    lower_yellow = np.array([15, 50, 150])   # 浅黄色下限
    upper_yellow = np.array([35, 255, 255])   # 浅黄色上限
    
    # 创建掩码：提取白色文字
    lower_white = np.array([0, 0, 200])       # 白色下限
    upper_white = np.array([180, 30, 255])  # 白色上限
    
    # 合并两个掩码
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    mask = cv2.bitwise_or(mask_yellow, mask_white)
    
    # 应用掩码，提取文字区域
    result = cv2.bitwise_and(img_array, img_array, mask=mask)
    
    # 转换为灰度
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    
    # 反转（文字变白，背景变黑）
    inverted = cv2.bitwise_not(gray)
    
    return inverted

def preprocess_method_12_add_padding(img_array):
    """方法12：添加白色边框（Padding）- 消除边界效应"""
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 计算padding大小（至少20像素，或图像尺寸的10%）
    height, width = gray.shape
    pad_size = max(20, int(min(width, height) * 0.1))
    
    # 添加白色边框
    padded = cv2.copyMakeBorder(
        gray, 
        pad_size, pad_size, pad_size, pad_size,
        cv2.BORDER_CONSTANT, 
        value=255  # 白色边框
    )
    
    return padded

def preprocess_method_13_hsv_padding(img_array):
    """方法13：HSV过滤 + Padding"""
    # 先HSV过滤
    hsv_filtered = preprocess_method_11_hsv_filter(img_array)
    
    # 再添加padding
    padded = preprocess_method_12_add_padding(hsv_filtered)
    
    return padded

def preprocess_method_14_original_padding(img_array):
    """方法14：原始图像 + Padding（测试建议的最优方法）"""
    # 先转换为灰度
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
    
    # 添加padding
    padded = preprocess_method_12_add_padding(gray)
    
    return padded

def preprocess_method_15_hsv_scale_padding(img_array):
    """方法15：HSV过滤 + 放大 + Padding"""
    # HSV过滤
    hsv_filtered = preprocess_method_11_hsv_filter(img_array)
    
    # 放大
    height, width = hsv_filtered.shape
    if width < 400 or height < 200:
        scale = max(400 / width, 200 / height, 2.0)
        new_width = int(width * scale)
        new_height = int(height * scale)
        scaled = cv2.resize(hsv_filtered, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    else:
        scaled = hsv_filtered
    
    # 添加padding
    padded = preprocess_method_12_add_padding(scaled)
    
    return padded

def preprocess_method_16_denoise_padding(img_array):
    """方法16：去噪+增强 + Padding（测试中表现最好的预处理+padding）"""
    # 去噪+增强
    denoised_enhanced = preprocess_method_7_denoise(img_array)
    
    # 添加padding
    padded = preprocess_method_12_add_padding(denoised_enhanced)
    
    return padded

def preprocess_method_17_extract_title_roi(img_array):
    """
    方法17：基于颜色区域定位提取标题栏ROI
    专门用于提取深褐色弹出框的标题区域（如"水车"、"火焰信号"）
    
    返回：(processed_image, roi_info_dict)
    roi_info_dict包含：
        - found: bool, 是否找到ROI
        - x, y, w, h: ROI坐标和尺寸
        - original_roi: 原始ROI图像(BGR格式)
        - processed_roi: 处理后的ROI图像(用于OCR)
    """
    if len(img_array.shape) == 3:
        # RGB转BGR（OpenCV格式）
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        # 如果是灰度图，转换回RGB再转BGR
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    
    # 转换到HSV空间
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # 定义深褐色/棕色弹出框背景的颜色范围
    # 深褐色在HSV中：H(色调)在10-30之间（棕色/橙色），S(饱和度)中等，V(明度)较低
    # 尝试多个颜色范围，选择最合适的
    color_ranges = [
        # 范围1：深褐色（主要）
        {
            'name': '深褐色',
            'lower': np.array([10, 50, 20]),   # H:10-30, S:50+, V:20-100
            'upper': np.array([30, 255, 100])
        },
        # 范围2：更深的棕色
        {
            'name': '深棕色',
            'lower': np.array([0, 30, 15]),    # H:0-40, S:30+, V:15-80
            'upper': np.array([40, 255, 80])
        },
        # 范围3：暗色（备用）
        {
            'name': '暗色',
            'lower': np.array([0, 0, 0]),       # 所有暗色
            'upper': np.array([180, 255, 60])
        }
    ]
    
    all_candidates = []
    
    for color_range in color_ranges:
        # 创建颜色掩码
        mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
        
        # 形态学操作：闭运算，连接相近的区域
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            if area < 500:  # 太小的话跳过
                continue
                
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # 筛选条件：标题栏通常是扁长的矩形
            # - 宽度通常在100-1000像素之间
            # - 宽高比通常是扁长的 (1.5 < ratio < 15)
            # - 高度通常在20-250像素之间
            if 1.5 < aspect_ratio < 15 and w > 100 and 20 < h < 250:
                all_candidates.append({
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'color_range': color_range['name']
                })
    
    # 按面积排序，选择最大的候选
    all_candidates.sort(key=lambda x: x['area'], reverse=True)
    
    # 存储所有候选信息用于调试
    if not hasattr(preprocess_method_17_extract_title_roi, '_all_candidates'):
        preprocess_method_17_extract_title_roi._all_candidates = []
    preprocess_method_17_extract_title_roi._all_candidates = all_candidates
    
    best_roi = None
    if all_candidates:
        # 选择面积最大的候选
        best_candidate = all_candidates[0]
        best_roi = (best_candidate['x'], best_candidate['y'], best_candidate['w'], best_candidate['h'])
    
    if best_roi:
        x, y, w, h = best_roi
        # 稍微扩展边界，避免裁剪到文字边缘
        padding = 10
        x_expanded = max(0, x - padding)
        y_expanded = max(0, y - padding)
        w_expanded = min(img_bgr.shape[1] - x_expanded, w + padding * 2)
        h_expanded = min(img_bgr.shape[0] - y_expanded, h + padding * 2)
        
        roi_original = img_bgr[y_expanded:y_expanded+h_expanded, x_expanded:x_expanded+w_expanded]
        
        # 转换为RGB并转为灰度
        roi_rgb = cv2.cvtColor(roi_original, cv2.COLOR_BGR2RGB)
        gray_roi = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2GRAY)
        
        # 放大2倍提高识别率
        resized_roi = cv2.resize(gray_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 二值化处理：白底黑字（翻转）
        _, binary_roi = cv2.threshold(resized_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 添加白色边框（Padding）
        final_roi = cv2.copyMakeBorder(binary_roi, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=[255])
        
        # 存储ROI信息到全局变量（用于调试输出）
        roi_info = {
            'found': True,
            'x': x_expanded,
            'y': y_expanded,
            'w': w_expanded,
            'h': h_expanded,
            'original_roi': roi_original,
            'processed_roi': final_roi,
            'mask': mask  # 保存掩码用于调试
        }
        
        # 将ROI信息附加到返回的图像上（通过全局变量传递）
        if not hasattr(preprocess_method_17_extract_title_roi, '_roi_info'):
            preprocess_method_17_extract_title_roi._roi_info = {}
        preprocess_method_17_extract_title_roi._roi_info = roi_info
        
        return final_roi
    
    # 如果找不到标题区域，返回原图的灰度版本
    roi_info = {
        'found': False,
        'x': 0,
        'y': 0,
        'w': 0,
        'h': 0,
        'original_roi': None,
        'processed_roi': None,
        'mask': mask
    }
    if not hasattr(preprocess_method_17_extract_title_roi, '_roi_info'):
        preprocess_method_17_extract_title_roi._roi_info = {}
    preprocess_method_17_extract_title_roi._roi_info = roi_info
    
    if len(img_array.shape) == 3:
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return img_array.copy()

def preprocess_method_18_extract_title_roi_clahe(img_array):
    """
    方法18：提取标题ROI + CLAHE增强
    """
    roi = preprocess_method_17_extract_title_roi(img_array)
    
    # 如果是灰度图，应用CLAHE
    if len(roi.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(roi)
    
    return roi

# 所有预处理方法
PREPROCESS_METHODS = [
    ('原始图像', preprocess_method_1_original),
    ('CLAHE增强', preprocess_method_2_clahe),
    ('自适应阈值', preprocess_method_3_adaptive_thresh),
    ('OTSU二值化', preprocess_method_4_otsu),
    ('形态学去阴影', preprocess_method_5_morphology),
    ('锐化+对比度', preprocess_method_6_sharpen),
    ('去噪+增强', preprocess_method_7_denoise),
    ('直方图均衡化', preprocess_method_8_histogram_eq),
    ('放大+CLAHE', preprocess_method_9_scale_up),
    ('组合方法', preprocess_method_10_combined),
    ('HSV颜色过滤', preprocess_method_11_hsv_filter),
    ('添加Padding', preprocess_method_12_add_padding),
    ('HSV+Padding', preprocess_method_13_hsv_padding),
    ('原始+Padding', preprocess_method_14_original_padding),
    ('HSV+放大+Padding', preprocess_method_15_hsv_scale_padding),
    ('去噪+增强+Padding', preprocess_method_16_denoise_padding),
    ('提取标题ROI', preprocess_method_17_extract_title_roi),
    ('提取标题ROI+CLAHE', preprocess_method_18_extract_title_roi_clahe),
]

# ==================== OCR配置 ====================

def get_ocr_configs():
    """获取所有OCR配置组合 - 基于测试结果优化"""
    configs = []
    
    # 根据测试结果，PSM 11效果最好，重点测试
    # PSM模式：6（统一文本块）、7（单行）、8（单词）、11（稀疏文本）、13（原始行）
    psm_modes = [6, 7, 8, 11, 13]
    
    # OEM模式：1（传统+LSTM）、3（仅LSTM）
    oem_modes = [1, 3]
    
    # 字符白名单：中文+数字+字母（游戏文本主要包含这些）
    char_whitelist = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\u4e00-\u9fff'
    
    for psm in psm_modes:
        for oem in oem_modes:
            # 基础配置
            base_config = f'--oem {oem} --psm {psm} -c preserve_interword_spaces=1'
            
            # 添加字符白名单（限制识别范围）
            config_with_whitelist = f'{base_config} -c tessedit_char_whitelist={char_whitelist}'
            
            # 标准配置（无白名单）
            configs.append({
                'name': f'PSM{psm}_OEM{oem}',
                'config': base_config,
                'psm': psm,
                'oem': oem,
                'has_whitelist': False
            })
            
            # 带白名单的配置（可能更准确）
            configs.append({
                'name': f'PSM{psm}_OEM{oem}_WL',
                'config': config_with_whitelist,
                'psm': psm,
                'oem': oem,
                'has_whitelist': True
            })
    
    return configs

def clean_ocr_text(text):
    """清理OCR结果"""
    if not text:
        return ""
    
    # 移除特殊字符
    text = re.sub(r'[{}[\]()<>`~!@#$%^&*_+=;:"\',.?\\|]', '', text)
    
    # 合并空格
    text = re.sub(r'\s{2,}', ' ', text)
    
    # 移除首尾空白
    text = text.strip()
    
    # 移除纯数字短行
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            if len(line) < 4 and line.isdigit():
                continue
            if len(line) > 50:
                line = line[:50] + "..."
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def ocr_with_config(img_array, config, lang='chi_sim'):
    """使用指定配置执行OCR"""
    try:
        # 转换为PIL Image
        if len(img_array.shape) == 2:
            pil_img = Image.fromarray(img_array)
        elif len(img_array.shape) == 3:
            pil_img = Image.fromarray(img_array)
        else:
            pil_img = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
        
        # 执行OCR
        start_time = time.time()
        text = pytesseract.image_to_string(
            pil_img,
            lang=lang,
            config=config['config']
        )
        ocr_time = time.time() - start_time
        
        # 清理结果
        text = clean_ocr_text(text)
        
        return text, ocr_time
        
    except Exception as e:
        logging.error(f"OCR失败 ({config['name']}): {e}")
        return None, 0

def get_fast_mode_configs():
    """快速模式：只测试最有效的组合"""
    # 基于测试结果，只测试最有效的预处理方法
    # 优先测试基于颜色区域定位的方法（ROI提取），这是最准确的方法
    fast_preprocess_methods = [
        ('提取标题ROI', preprocess_method_17_extract_title_roi),
        ('提取标题ROI+CLAHE', preprocess_method_18_extract_title_roi_clahe),
        ('原始图像', preprocess_method_1_original),
        ('原始+Padding', preprocess_method_14_original_padding),
        ('HSV颜色过滤', preprocess_method_11_hsv_filter),
        ('HSV+Padding', preprocess_method_13_hsv_padding),
        ('去噪+增强', preprocess_method_7_denoise),
        ('去噪+增强+Padding', preprocess_method_16_denoise_padding),
        ('直方图均衡化', preprocess_method_8_histogram_eq),
        ('CLAHE增强', preprocess_method_2_clahe),
    ]
    
    # 只测试PSM 11 + OEM 1（测试结果显示OEM1和OEM3没有区别，只测试OEM1节省时间）
    # 白名单版本效果很差（只有1次匹配），所以也不测试
    fast_ocr_configs = []
    
    # 只测试标准配置（OEM1 + PSM11）
    base_config = '--oem 1 --psm 11 -c preserve_interword_spaces=1'
    fast_ocr_configs.append({
        'name': 'PSM11_OEM1',
        'config': base_config,
        'psm': 11,
        'oem': 1,
        'has_whitelist': False
    })
    
    return fast_preprocess_methods, fast_ocr_configs

def test_ocr_on_temp_images(fast_mode=False):
    """全面测试OCR识别
    
    Args:
        fast_mode: 如果为True，只测试最有效的组合（约32种），否则测试全部（320种）
    """
    temp_dir = "data/temp"
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    # 设置Tesseract路径
    tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"Tesseract路径: {tesseract_path}")
    
    # 检查best版本
    tessdata_best = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tessdata_best"
    if os.path.exists(tessdata_best):
        print(f"使用best版本语言包: {tessdata_best}")
        lang = 'chi_sim'
    else:
        print("使用标准版本语言包")
        lang = 'chi_sim'
    
    # 获取所有PNG图片
    image_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.png')]
    image_files.sort()
    
    # 选择测试模式
    if fast_mode:
        preprocess_methods, ocr_configs = get_fast_mode_configs()
        print(f"\n{'='*100}")
        print("快速模式：只测试最有效的组合")
        print(f"{'='*100}")
    else:
        preprocess_methods = PREPROCESS_METHODS
        ocr_configs = get_ocr_configs()
        print(f"\n{'='*100}")
        print("完整模式：测试所有组合")
        print(f"{'='*100}")
    
    print(f"\n找到 {len(image_files)} 张图片")
    print(f"测试 {len(preprocess_methods)} 种预处理方法")
    print(f"测试 {len(ocr_configs)} 种OCR配置")
    print(f"总计: {len(preprocess_methods) * len(ocr_configs)} 种组合")
    
    if fast_mode:
        print(f"\n快速模式预计耗时: 约 {len(image_files) * len(preprocess_methods) * len(ocr_configs) * 0.1:.0f} 秒")
    else:
        print(f"\n完整模式预计耗时: 约 {len(image_files) * len(preprocess_methods) * len(ocr_configs) * 0.1 / 60:.1f} 分钟")
    print()
    
    # 存储所有结果
    all_results = []
    
    # 识别每张图片
    for idx, img_file in enumerate(image_files, 1):
        img_path = os.path.join(temp_dir, img_file)
        print(f"\n{'='*100}")
        print(f"[{idx}/{len(image_files)}] {img_file}")
        print(f"{'='*100}")
        
        try:
            # 读取图片
            img = cv2.imread(img_path)
            if img is None:
                print(f"  错误：无法读取图片")
                continue
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            print(f"  图片尺寸: {img_rgb.shape}")
            
            # 测试所有组合
            best_result = None
            best_score = 0
            
            for preprocess_name, preprocess_func in preprocess_methods:
                # 预处理
                try:
                    processed = preprocess_func(img_rgb)
                except Exception as e:
                    logging.warning(f"预处理失败 ({preprocess_name}): {e}")
                    continue
                
                # 测试所有OCR配置
                for config in ocr_configs:
                    text, ocr_time = ocr_with_config(processed, config, lang=lang)
                    
                    if text and len(text.strip()) > 1:
                        # 尝试匹配已知名称
                        monster_match, monster_score = fuzzy_match(text, KNOWN_MONSTERS, threshold=0.3)
                        event_match, event_score = fuzzy_match(text, KNOWN_EVENTS, threshold=0.3)
                        
                        match_type = None
                        match_name = None
                        match_score = 0
                        
                        if monster_score > event_score:
                            match_type = 'monster'
                            match_name = monster_match
                            match_score = monster_score
                        elif event_score > 0:
                            match_type = 'event'
                            match_name = event_match
                            match_score = event_score
                        
                        # 记录结果
                        result = {
                            'image': img_file,
                            'preprocess': preprocess_name,
                            'config': config['name'],
                            'text': text,
                            'time': ocr_time,
                            'match_type': match_type,
                            'match_name': match_name,
                            'match_score': match_score
                        }
                        all_results.append(result)
                        
                        # 更新最佳结果
                        if match_score > best_score:
                            best_score = match_score
                            best_result = result
                        
                        # 只显示匹配成功的结果
                        if match_score >= 0.3:
                            print(f"  ✓ {preprocess_name:15s} | {config['name']:12s} | "
                                  f"匹配: {match_type}={match_name} (分数:{match_score:.2f}) | "
                                  f"文本: {repr(text[:40])}")
            
            # 显示最佳结果
            if best_result and best_result['match_score'] >= 0.3:
                print(f"\n  ★ 最佳结果:")
                print(f"    预处理: {best_result['preprocess']}")
                print(f"    配置: {best_result['config']}")
                print(f"    匹配: {best_result['match_type']} = {best_result['match_name']} (分数: {best_result['match_score']:.2f})")
                print(f"    文本: {repr(best_result['text'])}")
            else:
                print(f"\n  ✗ 未找到匹配结果")
                
        except Exception as e:
            print(f"  处理图片时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 统计结果
    print(f"\n\n{'='*100}")
    print("测试结果统计")
    print(f"{'='*100}")
    
    # 按图片统计
    image_stats = {}
    for result in all_results:
        img = result['image']
        if img not in image_stats:
            image_stats[img] = {'total': 0, 'matched': 0, 'best_score': 0}
        image_stats[img]['total'] += 1
        if result['match_score'] >= 0.3:
            image_stats[img]['matched'] += 1
            if result['match_score'] > image_stats[img]['best_score']:
                image_stats[img]['best_score'] = result['match_score']
    
    success_count = sum(1 for stats in image_stats.values() if stats['matched'] > 0)
    total_count = len(image_stats)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n图片识别统计:")
    print(f"  总图片数: {total_count}")
    print(f"  成功识别: {success_count}")
    print(f"  识别失败: {total_count - success_count}")
    print(f"  成功率: {success_rate:.1f}%")
    
    # 统计最佳预处理方法
    preprocess_stats = {}
    for result in all_results:
        if result['match_score'] >= 0.3:
            preprocess = result['preprocess']
            if preprocess not in preprocess_stats:
                preprocess_stats[preprocess] = {'count': 0, 'avg_score': 0, 'scores': []}
            preprocess_stats[preprocess]['count'] += 1
            preprocess_stats[preprocess]['scores'].append(result['match_score'])
    
    if preprocess_stats:
        print(f"\n最佳预处理方法 (按匹配次数):")
        for preprocess, stats in sorted(preprocess_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            avg_score = sum(stats['scores']) / len(stats['scores'])
            print(f"  {preprocess:20s} | 匹配次数: {stats['count']:3d} | 平均分数: {avg_score:.2f}")
    
    # 统计最佳OCR配置
    config_stats = {}
    for result in all_results:
        if result['match_score'] >= 0.3:
            config = result['config']
            if config not in config_stats:
                config_stats[config] = {'count': 0, 'avg_score': 0, 'scores': []}
            config_stats[config]['count'] += 1
            config_stats[config]['scores'].append(result['match_score'])
    
    if config_stats:
        print(f"\n最佳OCR配置 (按匹配次数):")
        for config, stats in sorted(config_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            avg_score = sum(stats['scores']) / len(stats['scores'])
            print(f"  {config:15s} | 匹配次数: {stats['count']:3d} | 平均分数: {avg_score:.2f}")
    
    # 统计最佳组合
    combo_stats = {}
    for result in all_results:
        if result['match_score'] >= 0.3:
            combo = f"{result['preprocess']} + {result['config']}"
            if combo not in combo_stats:
                combo_stats[combo] = {'count': 0, 'avg_score': 0, 'scores': []}
            combo_stats[combo]['count'] += 1
            combo_stats[combo]['scores'].append(result['match_score'])
    
    if combo_stats:
        print(f"\n最佳组合 (前10名):")
        for combo, stats in sorted(combo_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            avg_score = sum(stats['scores']) / len(stats['scores'])
            print(f"  {combo:50s} | 匹配次数: {stats['count']:3d} | 平均分数: {avg_score:.2f}")
    
    print(f"{'='*100}")

def test_item_recognition_on_fullscreen_images(fast_mode=False, roi_only=False):
    """测试物品识别 - 使用全屏截图和字体大小筛选
    
    Args:
        fast_mode: 快速模式，只测试最有效的组合
        roi_only: 如果为True，只测试ROI提取，不进行OCR
    """
    from PIL import Image as PILImage
    
    temp_dir = "data/temp"
    
    if not os.path.exists(temp_dir):
        print(f"错误：目录 {temp_dir} 不存在")
        return
    
    if roi_only:
        print(f"\n{'='*100}")
        print("ROI提取测试模式：只测试区域提取，不进行OCR")
        print(f"{'='*100}\n")
    else:
        # 设置Tesseract路径
        tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"Tesseract路径: {tesseract_path}")
        
        lang = 'chi_sim'
    
    # 只获取前10张全屏截图
    image_files = [f for f in os.listdir(temp_dir) if f.startswith('ocr_item_fullscreen_') and f.endswith('.png')]
    image_files.sort()
    image_files = image_files[:10]  # 只测试前10张
    
    if roi_only:
        # 只测试ROI提取方法
        preprocess_methods = [
            ('提取标题ROI', preprocess_method_17_extract_title_roi),
            ('提取标题ROI+CLAHE', preprocess_method_18_extract_title_roi_clahe),
        ]
        print(f"找到 {len(image_files)} 张物品全屏截图")
        print(f"测试 {len(preprocess_methods)} 种ROI提取方法")
        print()
    else:
        # 选择测试模式
        if fast_mode:
            preprocess_methods, ocr_configs = get_fast_mode_configs()
            print(f"\n{'='*100}")
            print("快速模式：只测试最有效的组合")
            print(f"{'='*100}")
        else:
            preprocess_methods = PREPROCESS_METHODS
            ocr_configs = get_ocr_configs()
            print(f"\n{'='*100}")
            print("完整模式：测试所有组合")
            print(f"{'='*100}")
        
        print(f"\n找到 {len(image_files)} 张物品全屏截图")
        print(f"测试 {len(preprocess_methods)} 种预处理方法")
        print(f"测试 {len(ocr_configs)} 种OCR配置")
        print(f"总计: {len(preprocess_methods) * len(ocr_configs)} 种组合")
        print()
    
    # 存储所有结果
    all_results = []
    
    # 识别每张图片
    for idx, img_file in enumerate(image_files, 1):
        img_path = os.path.join(temp_dir, img_file)
        print(f"\n{'='*100}")
        print(f"[{idx}/{len(image_files)}] {img_file}")
        print(f"{'='*100}")
        
        try:
            # 读取图片
            img = cv2.imread(img_path)
            if img is None:
                print(f"  错误：无法读取图片")
                continue
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            print(f"  图片尺寸: {img_rgb.shape}")
            
            # 测试所有组合
            best_result = None
            best_score = 0
            
            for preprocess_name, preprocess_func in preprocess_methods:
                # 预处理
                try:
                    processed = preprocess_func(img_rgb)
                except Exception as e:
                    logging.warning(f"预处理失败 ({preprocess_name}): {e}")
                    continue
                
                # 如果是ROI提取方法，保存和显示ROI信息
                roi_info = None
                if '提取标题ROI' in preprocess_name and hasattr(preprocess_method_17_extract_title_roi, '_roi_info'):
                    roi_info = preprocess_method_17_extract_title_roi._roi_info
                    
                    # 显示所有候选区域（用于调试）
                    if hasattr(preprocess_method_17_extract_title_roi, '_all_candidates'):
                        all_candidates = preprocess_method_17_extract_title_roi._all_candidates
                        if all_candidates:
                            print(f"\n  [ROI提取] 找到 {len(all_candidates)} 个候选区域:")
                            for idx, cand in enumerate(all_candidates[:10], 1):  # 只显示前10个
                                print(f"    {idx}. 位置: ({cand['x']}, {cand['y']}) | "
                                      f"尺寸: {cand['w']}x{cand['h']} | "
                                      f"面积: {cand['area']} | "
                                      f"宽高比: {cand['aspect_ratio']:.2f} | "
                                      f"颜色范围: {cand['color_range']}")
                            if len(all_candidates) > 10:
                                print(f"    ... 还有 {len(all_candidates) - 10} 个候选区域")
                    
                    if roi_info['found']:
                        print(f"\n  [ROI提取] ✓ 选择的最佳区域:")
                        print(f"    位置: ({roi_info['x']}, {roi_info['y']})")
                        print(f"    尺寸: {roi_info['w']}x{roi_info['h']} 像素")
                        print(f"    面积: {roi_info['w'] * roi_info['h']} 像素²")
                        
                        # 保存ROI图像到文件
                        try:
                            roi_dir = os.path.join(temp_dir, 'roi_debug')
                            os.makedirs(roi_dir, exist_ok=True)
                            
                            # 生成文件名
                            base_name = os.path.splitext(img_file)[0]
                            method_short = preprocess_name.replace('提取标题ROI', 'ROI').replace('+', '_').replace(' ', '_')
                            
                            # 保存原始ROI（彩色）
                            roi_original_path = os.path.join(roi_dir, f"{base_name}_{method_short}_original.png")
                            cv2.imwrite(roi_original_path, roi_info['original_roi'])
                            
                            # 保存处理后的ROI（用于OCR）
                            roi_processed_path = os.path.join(roi_dir, f"{base_name}_{method_short}_processed.png")
                            cv2.imwrite(roi_processed_path, roi_info['processed_roi'])
                            
                            # 保存掩码（调试用）
                            roi_mask_path = os.path.join(roi_dir, f"{base_name}_{method_short}_mask.png")
                            cv2.imwrite(roi_mask_path, roi_info['mask'])
                            
                            # 在原图上标记ROI区域（绿色矩形框）和所有候选区域（蓝色矩形框）
                            img_with_roi = img_rgb.copy()
                            
                            # 先标记所有候选区域（蓝色，较细）
                            if hasattr(preprocess_method_17_extract_title_roi, '_all_candidates'):
                                all_candidates = preprocess_method_17_extract_title_roi._all_candidates
                                for idx, cand in enumerate(all_candidates[:20]):  # 最多标记20个候选
                                    cv2.rectangle(img_with_roi, 
                                                (cand['x'], cand['y']), 
                                                (cand['x'] + cand['w'], cand['y'] + cand['h']), 
                                                (255, 0, 0), 1)  # 蓝色矩形框，线宽1
                            
                            # 再标记最佳ROI区域（绿色，较粗）
                            cv2.rectangle(img_with_roi, 
                                        (roi_info['x'], roi_info['y']), 
                                        (roi_info['x'] + roi_info['w'], roi_info['y'] + roi_info['h']), 
                                        (0, 255, 0), 3)  # 绿色矩形框，线宽3
                            
                            roi_marked_path = os.path.join(roi_dir, f"{base_name}_{method_short}_marked.png")
                            cv2.imwrite(roi_marked_path, cv2.cvtColor(img_with_roi, cv2.COLOR_RGB2BGR))
                            
                            print(f"    ✓ ROI调试图像已保存到: {roi_dir}")
                            print(f"      - 原始ROI: {os.path.basename(roi_original_path)}")
                            print(f"      - 处理后ROI: {os.path.basename(roi_processed_path)}")
                            print(f"      - 标记ROI的原图: {os.path.basename(roi_marked_path)}")
                            print(f"      - 颜色掩码: {os.path.basename(roi_mask_path)}")
                        except Exception as e:
                            logging.warning(f"保存ROI图像失败: {e}")
                    else:
                        print(f"\n  [ROI提取] ✗ 未找到标题区域")
                
                # 如果是ROI测试模式，跳过OCR，只显示ROI信息
                if roi_only:
                    continue
                
                # 转换为PIL Image
                if len(processed.shape) == 3:
                    pil_img = PILImage.fromarray(processed)
                else:
                    pil_img = PILImage.fromarray(processed)
                
                # 如果图像太大，先缩放以加快OCR速度并防止挂起
                max_dimension = 2000
                if pil_img.width > max_dimension or pil_img.height > max_dimension:
                    scale = min(max_dimension / pil_img.width, max_dimension / pil_img.height)
                    new_width = int(pil_img.width * scale)
                    new_height = int(pil_img.height * scale)
                    # 使用LANCZOS重采样（兼容新旧版本PIL）
                    try:
                        pil_img = pil_img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    except AttributeError:
                        pil_img = pil_img.resize((new_width, new_height), PILImage.LANCZOS)
                
                # 如果使用了ROI提取方法，改用PSM 7（单行文本）配置
                # 因为ROI已经裁剪出了标题区域，通常只有一行文字
                use_psm7 = '提取标题ROI' in preprocess_name
                
                # 测试所有OCR配置
                for config in ocr_configs:
                    try:
                        start_time = time.time()
                        
                        # 如果使用ROI提取，强制使用PSM 7（单行文本模式）
                        ocr_config = config['config']
                        if use_psm7:
                            # 替换PSM模式为7
                            ocr_config = re.sub(r'--psm \d+', '--psm 7', ocr_config)
                            if '--psm' not in ocr_config:
                                ocr_config = ocr_config + ' --psm 7'
                        
                        # 使用image_to_data获取文本位置和大小信息
                        ocr_data = pytesseract.image_to_data(
                            pil_img,
                            lang=lang,
                            config=ocr_config,
                            output_type=pytesseract.Output.DICT
                        )
                        ocr_time = time.time() - start_time
                    except Exception as e:
                        logging.warning(f"OCR失败 ({config['name']}): {e}")
                        continue
                    
                    # 解析OCR数据，提取文本和字体大小
                    text_items = []
                    n_boxes = len(ocr_data['text'])
                    
                    for i in range(n_boxes):
                        text = ocr_data['text'][i].strip()
                        if not text or int(ocr_data['conf'][i]) < 0:
                            continue
                        
                        height = ocr_data['height'][i]
                        width = ocr_data['width'][i]
                        left = ocr_data['left'][i]
                        top = ocr_data['top'][i]
                        conf = int(ocr_data['conf'][i])
                        
                        # 只保留中文字符较多的文本
                        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                        if chinese_chars >= 1:
                            # 排除类型标签和描述词汇
                            type_labels = ['武器', '伙伴', '小型', '中型', '大型', '水系', '火系', '科技', '奖励',
                                          '物品', '造成', '攻克', '持续', '减速', '加速', '冻结', '治疗', '护盾',
                                          '伤害', '获得', '使用', '触发', '秒', '倍', '提高', '降低', '增加', '减少']
                            if text not in type_labels and not all(c in type_labels for c in text):
                                text_items.append({
                                    'text': text,
                                    'height': height,
                                    'width': width,
                                    'left': left,
                                    'top': top,
                                    'chinese_count': chinese_chars
                                })
                    
                    # 尝试合并相邻的文本（如"水"+"车"合并为"水车"）
                    # 按位置排序，找出可能相邻的文本
                    text_items_sorted = sorted(text_items, key=lambda x: (x['top'], x['left']))
                    merged_texts = []
                    
                    # 合并逻辑：支持多次合并（如"临"+"时"+"大"+"棒"）
                    used_indices = set()
                    for i, item in enumerate(text_items_sorted):
                        if i in used_indices:
                            continue
                            
                        merged_text = item['text']
                        merged_height = item['height']
                        merged_width = item['width']
                        merged_left = item['left']
                        merged_top = item['top']
                        current_indices = {i}
                        
                        # 多次合并：继续查找右侧相邻的文本
                        changed = True
                        while changed:
                            changed = False
                            for j, other_item in enumerate(text_items_sorted):
                                if j in used_indices or j in current_indices:
                                    continue
                                # 检查是否在同一行（垂直距离小于字体高度的1.5倍）
                                vertical_distance = abs(merged_top - other_item['top'])
                                if vertical_distance <= merged_height * 1.5:
                                    # 检查是否在右侧（水平距离小于字体宽度的3倍）
                                    horizontal_distance = other_item['left'] - (merged_left + merged_width)
                                    if 0 <= horizontal_distance <= merged_width * 3:
                                        # 合并文本
                                        merged_text = merged_text + other_item['text']
                                        merged_width = other_item['left'] + other_item['width'] - merged_left
                                        merged_height = max(merged_height, other_item['height'])
                                        current_indices.add(j)
                                        changed = True
                                        break
                        
                        # 标记已使用的索引
                        used_indices.update(current_indices)
                        
                        merged_texts.append({
                            'text': merged_text,
                            'height': merged_height,
                            'width': merged_width,
                            'chinese_count': sum(1 for c in merged_text if '\u4e00' <= c <= '\u9fff')
                        })
                    
                    # 按字体高度排序合并后的文本
                    merged_texts.sort(key=lambda x: x['height'], reverse=True)
                    
                    # 显示字体大小统计（仅对第一种预处理方法显示，避免输出过多）
                    if preprocess_name == preprocess_methods[0][0] and config == ocr_configs[0]:
                        print(f"\n  [字体大小分析] 识别到 {len(text_items)} 个原始文本项，合并后 {len(merged_texts)} 个文本")
                        print(f"    前10个最大的合并文本（按字体高度排序）:")
                        for idx, item in enumerate(merged_texts[:10], 1):
                            print(f"      {idx}. {repr(item['text'][:30]):35s} | 高度: {item['height']:4d}px | 宽度: {item['width']:4d}px | 中文字数: {item['chinese_count']}")
                        if len(merged_texts) > 10:
                            print(f"      ... 还有 {len(merged_texts) - 10} 个文本")
                    
                    # 选择前5个最大的合并文本进行匹配
                    top5_candidates = []
                    if merged_texts:
                        # 获取前5个包含中文字符的合并文本
                        for item in merged_texts:
                            if item['chinese_count'] >= 1:
                                top5_candidates.append(item)
                                if len(top5_candidates) >= 5:
                                    break
                    
                    # 对前5个候选文本都进行匹配，选择最佳匹配
                    selected_text = None
                    item_match = None
                    item_score = 0
                    font_height = 0
                    best_candidate_index = -1
                    
                    if top5_candidates:
                        for idx, candidate in enumerate(top5_candidates):
                            match_name, match_score = fuzzy_match(candidate['text'], KNOWN_ITEMS, threshold=0.3)
                            if match_score > item_score:
                                item_score = match_score
                                item_match = match_name
                                selected_text = candidate['text']
                                font_height = candidate['height']
                                best_candidate_index = idx
                        
                        # 如果没有匹配成功，至少选择第一个候选
                        if not selected_text and top5_candidates:
                            selected_text = top5_candidates[0]['text']
                            font_height = top5_candidates[0]['height']
                    
                    # 记录结果（包括没有找到文本的情况）
                    result = {
                        'image': img_file,
                        'preprocess': preprocess_name,
                        'config': config['name'],
                        'text': selected_text or '',
                        'time': ocr_time,
                        'match_type': 'item' if item_score >= 0.3 else None,
                        'match_name': item_match,
                        'match_score': item_score,
                        'text_count': len(text_items),
                        'merged_count': len(merged_texts) if merged_texts else 0,
                        'font_height': font_height
                    }
                    all_results.append(result)
                    
                    # 更新最佳结果
                    if item_score > best_score:
                        best_score = item_score
                        best_result = result
                    
                    # 显示所有结果（包括未匹配成功的）
                    if selected_text:
                        status = '✓' if item_score >= 0.3 else '○'
                        match_info = f"匹配: {item_match} (分数:{item_score:.2f})" if item_match else f"未匹配 (分数:{item_score:.2f})"
                        candidate_info = f"前5候选中第{best_candidate_index+1}个" if best_candidate_index >= 0 else "无候选"
                        print(f"  {status} {preprocess_name:15s} | {config['name']:12s} | "
                              f"{match_info} | "
                              f"文本: {repr(selected_text[:40])} ({candidate_info}) | "
                              f"候选数: {len(top5_candidates)} | 字体高度: {font_height}px | 耗时: {ocr_time:.2f}s")
                    else:
                        print(f"  ✗ {preprocess_name:15s} | {config['name']:12s} | "
                              f"未找到中文文本 | 原始文本数: {len(text_items)} | 合并后: {len(merged_texts) if merged_texts else 0} | 耗时: {ocr_time:.2f}s")
            
            # 显示最佳结果
            if best_result and best_result['match_score'] >= 0.3:
                print(f"\n  ★ 最佳结果:")
                print(f"    预处理: {best_result['preprocess']}")
                print(f"    配置: {best_result['config']}")
                print(f"    匹配: {best_result['match_name']} (分数: {best_result['match_score']:.2f})")
                print(f"    文本: {repr(best_result['text'])}")
            else:
                print(f"\n  ✗ 未找到匹配结果")
                
        except Exception as e:
            print(f"  处理图片时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 如果是ROI测试模式，不进行OCR统计
    if roi_only:
        print(f"\n\n{'='*100}")
        print("ROI提取测试完成")
        print(f"{'='*100}")
        print(f"\n✓ 所有ROI调试图像已保存到: {os.path.join(temp_dir, 'roi_debug')}")
        return
    
    # 统计结果（类似monster/event的统计逻辑）
    print(f"\n\n{'='*100}")
    print("物品识别测试结果统计")
    print(f"{'='*100}")
    
    image_stats = {}
    for result in all_results:
        img = result['image']
        if img not in image_stats:
            image_stats[img] = {'total': 0, 'matched': 0, 'best_score': 0}
        image_stats[img]['total'] += 1
        if result['match_score'] >= 0.3:
            image_stats[img]['matched'] += 1
            if result['match_score'] > image_stats[img]['best_score']:
                image_stats[img]['best_score'] = result['match_score']
    
    success_count = sum(1 for stats in image_stats.values() if stats['matched'] > 0)
    total_count = len(image_stats)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n图片识别统计:")
    print(f"  总图片数: {total_count}")
    print(f"  成功识别: {success_count}")
    print(f"  识别失败: {total_count - success_count}")
    print(f"  成功率: {success_rate:.1f}%")
    
    # 统计最佳预处理方法和OCR配置
    preprocess_stats = {}
    config_stats = {}
    for result in all_results:
        if result['match_score'] >= 0.3:
            preprocess = result['preprocess']
            config = result['config']
            
            if preprocess not in preprocess_stats:
                preprocess_stats[preprocess] = {'count': 0, 'scores': []}
            preprocess_stats[preprocess]['count'] += 1
            preprocess_stats[preprocess]['scores'].append(result['match_score'])
            
            if config not in config_stats:
                config_stats[config] = {'count': 0, 'scores': []}
            config_stats[config]['count'] += 1
            config_stats[config]['scores'].append(result['match_score'])
    
    if preprocess_stats:
        print(f"\n最佳预处理方法 (按匹配次数):")
        for preprocess, stats in sorted(preprocess_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            avg_score = sum(stats['scores']) / len(stats['scores'])
            print(f"  {preprocess:20s} | 匹配次数: {stats['count']:3d} | 平均分数: {avg_score:.2f}")
    
    if config_stats:
        print(f"\n最佳OCR配置 (按匹配次数):")
        for config, stats in sorted(config_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            avg_score = sum(stats['scores']) / len(stats['scores'])
            print(f"  {config:15s} | 匹配次数: {stats['count']:3d} | 平均分数: {avg_score:.2f}")
    
    print(f"{'='*100}")

if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    fast_mode = '--fast' in sys.argv or '-f' in sys.argv
    test_items = '--items' in sys.argv or '-i' in sys.argv
    roi_only = '--roi-only' in sys.argv or '--roi' in sys.argv
    
    if test_items:
        if roi_only:
            print("ROI提取测试模式：只测试区域提取，不进行OCR")
        elif fast_mode:
            print("使用快速模式测试物品识别（只测试最有效的组合）")
        else:
            print("使用完整模式测试物品识别（测试所有组合）")
        test_item_recognition_on_fullscreen_images(fast_mode=fast_mode, roi_only=roi_only)
    else:
        if fast_mode:
            print("使用快速模式（只测试最有效的组合）")
            print("如需完整测试，请运行: python test_ocr_optimized.py")
        else:
            print("使用完整模式（测试所有组合）")
            print("如需快速测试，请运行: python test_ocr_optimized.py --fast")
        print("\n提示: 使用 --items 或 -i 参数测试物品识别")
        test_ocr_on_temp_images(fast_mode=fast_mode)
