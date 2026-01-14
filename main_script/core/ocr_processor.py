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

    def preprocess_image(self, img):
        """图像预处理优化，提高OCR识别质量"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # 简单预处理：CLAHE增强对比度 + OTSU二值化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, binary = cv2.threshold(
                enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 放大图像以提高OCR准确性
            height, width = binary.shape
            if width < 400 or height < 200:
                scale = max(400 / width, 200 / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                binary = cv2.resize(
                    binary, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

            return binary

        except Exception as e:
            logging.error(f"图像预处理失败: {e}")
            logging.error(traceback.format_exc())
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                return binary
            except BaseException:
                return img

    def get_game_tesseract_config(self, mode='balanced'):
        """
        游戏专用Tesseract配置 - 基于测试结果优化

        测试结果显示：PSM 11 + OEM 1 效果最好
        - 原始图像：匹配次数最多（42次），平均分数0.42
        - 去噪+增强：分数最高（0.44），但速度较慢

        mode: 'fast' - 最快速度（原始图像+PSM11+OEM1）
              'balanced' - 平衡模式（原始图像+PSM11+OEM1，推荐）
              'accurate' - 最高准确率（去噪+增强+PSM11+OEM1，稍慢）
        """
        configs = {
            'fast': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            },
            'balanced': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            },
            'accurate': {
                'psm': '11',
                'oem': '1',
                'config': '--oem 1 --psm 11 -c preserve_interword_spaces=1'
            }
        }
        return configs.get(mode, configs['balanced'])

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
            use_preprocess=False):
        """
        游戏专用OCR - 使用平衡模式+无预处理（最佳效果）
        """
        try:
            # 根据区域类型选择模式
            if region_type == 'monster':
                # 怪物名称通常较短，但用户反馈平衡模式更好
                mode = 'balanced'
            else:
                # 事件描述可能较长，用balanced模式
                mode = 'balanced'

            config = self.get_game_tesseract_config(mode)

            # 直接识别，不预处理（用户反馈无预处理效果最好）
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
                    f"[游戏OCR] 模式={mode}, 预处理={use_preprocess}, "
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
            
            # 保存截图到项目根目录的temp目录（与旧脚本保持一致）
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
                offset_left = -900
                offset_right = 600
                offset_top = -700
                offset_bottom = 150
                
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
            
            # 保存调试图像（同步执行，确保保存成功）
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
                    # __file__ = main_script/core/ocr_processor.py
                    # dirname 1次 = main_script/core
                    # dirname 2次 = main_script
                    # dirname 3次 = 项目根目录
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
                # 怪物/事件识别：使用普通OCR
                text = self.ocr_for_game(img_array, mode='balanced', region_type=region_type, use_preprocess=False)
                if text and text.strip():
                    logging.info(f"[OCR] 原始图像识别成功: {repr(text[:100])}")
                else:
                    # 如果原始图像失败，尝试去噪+增强
                    logging.debug("原始图像识别失败，尝试预处理图像")
                    processed_img = self.preprocess_image(img_array)
                    text = self.ocr_for_game(processed_img, mode='balanced', region_type=region_type, use_preprocess=True)
            
            return text.strip() if text else None
            
        except Exception as e:
            logging.error(f"获取文字失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def process_ocr_text(self, ocr_text):
        """处理OCR识别的文本"""
        # TODO: 从Bazaar_Lens.py中提取完整的文本处理逻辑
        # 这个方法可能需要调用TextMatcher进行匹配
        return ocr_text
