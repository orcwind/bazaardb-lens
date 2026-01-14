"""
物品OCR识别和匹配测试脚本
测试 data/temp 目录下的图片，验证识别和匹配效果

测试内容：
1. 使用 ocr_for_item 方法识别图片中的物品名称（按字体大小排序）
2. 使用 find_item_by_name 匹配物品数据
3. 结合日志中的手牌/背包物品名称，提高匹配率
4. 排除游戏关键字（如武器、食物等），提高匹配准确率
"""
import os
import sys
import logging
import glob
import csv

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, project_root)

# 全局变量：需要排除的游戏关键字（中文）
EXCLUDE_KEYWORDS = set()


def load_exclude_keywords():
    """
    从 key_word.csv 加载需要排除的关键字
    规则：第三列（包含关键字物品数量）为空的关键字需要排除
    """
    global EXCLUDE_KEYWORDS
    keyword_file = os.path.join(project_root, 'data', 'Json', 'key_word.csv')
    
    if not os.path.exists(keyword_file):
        print(f"⚠ 关键字文件不存在: {keyword_file}")
        return
    
    try:
        with open(keyword_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # 跳过标题行
            
            for row in reader:
                if len(row) >= 2:
                    keyword_zh = row[1].strip()  # 第二列：中文翻译
                    count = row[2].strip() if len(row) >= 3 else ''  # 第三列：物品数量
                    
                    # 如果没有数量（空），则加入排除列表
                    if keyword_zh and not count:
                        EXCLUDE_KEYWORDS.add(keyword_zh)
        
        print(f"✓ 已加载 {len(EXCLUDE_KEYWORDS)} 个排除关键字: {list(EXCLUDE_KEYWORDS)[:10]}...")
    except Exception as e:
        print(f"✗ 加载关键字文件失败: {e}")


def remove_keywords_from_text(text):
    """
    从文本中移除游戏关键字（作为整体移除）
    例如：'武器磨刀石' -> '磨刀石'
    """
    if not text or not EXCLUDE_KEYWORDS:
        return text
    
    result = text
    removed = []
    
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in result:
            result = result.replace(keyword, '')
            removed.append(keyword)
    
    if removed:
        logging.debug(f"  [关键字过滤] '{text}' -> '{result}' (移除: {removed})")
    
    return result


def get_ocr_with_size_details(img_array):
    """
    获取详细的OCR结果，包含每个文字的字体大小信息
    返回：{
        'top5': [{'text': '文字', 'height': 高度, 'conf': 置信度}, ...],
        'top5_combined': '前5大组合文本',
        'all_text': '全部中文文本'
    }
    """
    import re
    import time
    
    try:
        # 转换图像格式
        if isinstance(img_array, np.ndarray):
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                pil_img = Image.fromarray(img_array)
            elif len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array)
            else:
                pil_img = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
        else:
            pil_img = img_array
        
        # 使用 image_to_data 获取详细信息
        start_time = time.time()
        config = '--psm 6 --oem 1'
        data = pytesseract.image_to_data(
            pil_img,
            lang='chi_sim',
            config=config,
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
            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
            
            # 只保留置信度大于0的结果
            if conf > 0:
                text_items.append({
                    'text': text,
                    'height': height,
                    'conf': conf
                })
        
        if not text_items:
            return None
        
        # 按高度（字体大小）降序排序
        text_items.sort(key=lambda x: x['height'], reverse=True)
        
        # 提取中文字符
        chinese_texts = []
        for item in text_items:
            chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', item['text'])
            if chinese_chars:
                chinese_texts.append({
                    'text': chinese_chars,
                    'height': item['height'],
                    'conf': item['conf']
                })
        
        if not chinese_texts:
            return None
        
        # 按高度排序
        chinese_texts.sort(key=lambda x: x['height'], reverse=True)
        
        # 前5个最大的
        top5 = chinese_texts[:5]
        top5_combined = ''.join([t['text'] for t in top5])
        all_text = ''.join([t['text'] for t in chinese_texts])
        
        return {
            'top5': top5,
            'top5_combined': top5_combined,
            'all_text': all_text,
            'ocr_time': ocr_time
        }
        
    except Exception as e:
        logging.error(f"获取OCR详细信息失败: {e}")
        return None

# 直接设置便携版 Tesseract 路径（和主程序一致）
import pytesseract
tesseract_path = os.path.join(project_root, 'Tesseract-OCR', 'tesseract.exe')
if os.path.exists(tesseract_path):
    # 必须用 pytesseract.pytesseract.tesseract_cmd，和主程序一样
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✓ Tesseract路径: {tesseract_path}")
else:
    print(f"✗ Tesseract未找到: {tesseract_path}")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 导入模块
from PIL import Image
import numpy as np
import cv2

from core.ocr_processor import OCRProcessor
from data.loader import DataLoader
import threading


class SimpleLogScanner:
    """简化版日志扫描器，用于测试"""
    
    def __init__(self, uuid_to_item_data):
        self.uuid_to_item_data = uuid_to_item_data
        self.instance_to_template = {}
        self.template_to_name_zh = {}
        self.hand_items = set()
        self.stash_items = set()
        self.equipped_items = set()
    
    def _update_template_name_mapping(self, template_id):
        """更新TemplateId到中文名称的映射"""
        if template_id in self.template_to_name_zh:
            return
        if template_id in self.uuid_to_item_data:
            item_data = self.uuid_to_item_data[template_id]
            name_zh = item_data.get('name_zh', '')
            if name_zh:
                self.template_to_name_zh[template_id] = name_zh
    
    def get_current_items(self):
        """获取当前玩家的所有物品中文名称列表"""
        item_names = []
        for instance_id in self.equipped_items:
            template_id = self.instance_to_template.get(instance_id)
            if template_id:
                name_zh = self.template_to_name_zh.get(template_id)
                if name_zh and name_zh not in item_names:
                    item_names.append(name_zh)
        return item_names
    
    def get_hand_item_names(self):
        """获取手牌物品的中文名称列表"""
        item_names = []
        for instance_id in self.hand_items:
            template_id = self.instance_to_template.get(instance_id)
            if template_id:
                name_zh = self.template_to_name_zh.get(template_id)
                if name_zh and name_zh not in item_names:
                    item_names.append(name_zh)
        return item_names
    
    def get_stash_item_names(self):
        """获取仓库物品的中文名称列表"""
        item_names = []
        for instance_id in self.stash_items:
            template_id = self.instance_to_template.get(instance_id)
            if template_id:
                name_zh = self.template_to_name_zh.get(template_id)
                if name_zh and name_zh not in item_names:
                    item_names.append(name_zh)
        return item_names
    
    def get_item_count(self):
        """获取物品统计"""
        return {
            'hand': len(self.hand_items),
            'stash': len(self.stash_items),
            'total': len(self.equipped_items),
            'mapped': len(self.template_to_name_zh)
        }


def test_single_image(image_path, ocr_processor, data_loader, log_item_names=None):
    """
    测试单张图片的识别和匹配
    返回: (直接匹配结果, 日志辅助匹配结果, 匹配到的物品名)
    """
    print(f"\n{'='*60}")
    print(f"测试图片: {os.path.basename(image_path)}")
    print('='*60)
    
    direct_match = None
    log_match = None
    matched_name = None
    
    try:
        # 加载图片
        img = Image.open(image_path)
        img_array = np.array(img)
        
        print(f"图片尺寸: {img.size}")
        
        # 1. 使用物品专用OCR识别 + 获取详细字体大小信息
        print("\n--- 物品OCR识别 (按字体大小排序) ---")
        
        # 获取详细的OCR结果（包含字体大小）
        ocr_details = get_ocr_with_size_details(img_array)
        
        if ocr_details:
            print(f"【前5大字体】")
            for i, item in enumerate(ocr_details['top5'], 1):
                print(f"  {i}. '{item['text']}' (高度: {item['height']}px, 置信度: {item['conf']})")
            
            text = ocr_details['top5_combined']
            all_text = ocr_details['all_text']
            print(f"\n前5大组合: '{text}'")
            print(f"全部文本: '{all_text[:60]}{'...' if len(all_text) > 60 else ''}'")
        else:
            # 回退到普通OCR
            ocr_result = ocr_processor.ocr_for_item(img_array)
            if ocr_result and '|' in ocr_result:
                text, all_text = ocr_result.split('|', 1)
            else:
                text = ocr_result
                all_text = ocr_result
            print(f"识别结果: '{text}'")
        
        if not text:
            print("❌ OCR识别失败，无文本")
            return (None, None, None)
        
        # 2. 全库匹配（使用全部文本，应用关键字过滤）
        print("\n--- 全库匹配 ---")
        match_text = all_text if all_text else text
        log_match = find_best_match_full_library(match_text, data_loader)
        if log_match:
            matched_name = log_match.get('name_zh', '')
            print(f"✅ 全库匹配成功: {matched_name}")
        else:
            print(f"❌ 全库匹配失败")
        
        # 注：日志辅助匹配暂时禁用
        # if log_item_names:
        #     print(f"\n--- 日志辅助匹配 (手牌/背包: {len(log_item_names)}个物品) ---")
        #     log_match = find_best_match_with_log(match_text, log_item_names, data_loader)
        
        return (None, log_match, matched_name)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return (None, None, None)


def find_best_match_full_library(ocr_text, data_loader):
    """
    全库匹配：从所有物品中查找最佳匹配（使用打分系统）
    """
    import re
    import difflib
    
    if not ocr_text:
        return None
    
    # 清理OCR文本，只保留中文
    def clean_chinese(s):
        return re.sub(r'[^\u4e00-\u9fff]', '', s)
    
    text_clean = clean_chinese(ocr_text)
    if not text_clean or len(text_clean) < 1:
        return None
    
    # 移除游戏关键字（如武器、食物等）
    text_filtered = remove_keywords_from_text(text_clean)
    
    print(f"  OCR清理后: '{text_clean}'")
    if text_filtered != text_clean:
        print(f"  关键字过滤后: '{text_filtered}'")
    
    # 使用过滤后的文本进行匹配（如果过滤后为空，则用原文本）
    match_text = text_filtered if text_filtered else text_clean
    
    # 全库打分
    all_scores = []
    
    for uuid, item_data in data_loader.uuid_to_item_data.items():
        name_zh = item_data.get('name_zh', '')
        if not name_zh:
            continue
        
        name_clean = clean_chinese(name_zh)
        if not name_clean:
            continue
        
        score = 0.0
        match_details = []
        
        # 1. 完全匹配 (100分)
        if match_text == name_clean:
            score = 100.0
            match_details.append("完全匹配")
        else:
            # 2. 字符匹配打分
            matched_chars = sum(1 for char in name_clean if char in match_text)
            if matched_chars > 0:
                char_coverage = matched_chars / len(name_clean)
                score += char_coverage * 40
                match_details.append(f"字符{matched_chars}/{len(name_clean)}")
            
            # 3. 连续字符匹配
            if name_clean in match_text:
                score += 35
                match_details.append("完整子串")
            else:
                longest_common = 0
                for i in range(len(name_clean)):
                    for j in range(i + 1, len(name_clean) + 1):
                        substr = name_clean[i:j]
                        if substr in match_text and len(substr) > longest_common:
                            longest_common = len(substr)
                
                if longest_common > 0:
                    seq_score = (longest_common / len(name_clean)) * 30
                    score += seq_score
                    match_details.append(f"连续{longest_common}字")
            
            # 4. 模糊匹配
            ratio = difflib.SequenceMatcher(None, match_text, name_clean).ratio()
            fuzzy_score = ratio * 20
            score += fuzzy_score
            if ratio > 0.3:
                match_details.append(f"模糊{ratio:.0%}")
        
        if score >= 25:
            all_scores.append((name_zh, score, match_details, item_data))
    
    # 按分数排序
    all_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 显示前5个匹配结果
    if all_scores:
        print(f"  【全库打分前5】")
        for name, score, details, _ in all_scores[:5]:
            print(f"    {name}: {score:.1f}分 ({', '.join(details)})")
        
        # 返回最高分的匹配
        if all_scores[0][1] >= 30:
            best_name, best_score, _, best_data = all_scores[0]
            print(f"  ✅ 最佳匹配: {best_name} (得分: {best_score:.1f})")
            return best_data
    
    return None


def find_best_match_with_log(ocr_text, log_item_names, data_loader):
    """
    结合日志中的物品名称进行匹配（使用打分系统）
    手牌和背包物品已经从日志获取了名称，应该达到近乎100%匹配
    【暂时禁用】
    """
    import re
    import difflib
    
    if not ocr_text or not log_item_names:
        return None
    
    # 清理OCR文本，只保留中文
    def clean_chinese(s):
        return re.sub(r'[^\u4e00-\u9fff]', '', s)
    
    text_clean = clean_chinese(ocr_text)
    if not text_clean or len(text_clean) < 1:
        return None
    
    # 移除游戏关键字（如武器、食物等）
    text_filtered = remove_keywords_from_text(text_clean)
    
    print(f"  OCR清理后: '{text_clean}'")
    if text_filtered != text_clean:
        print(f"  关键字过滤后: '{text_filtered}'")
    print(f"  日志物品: {log_item_names}")
    
    # 使用过滤后的文本进行匹配（如果过滤后为空，则用原文本）
    match_text = text_filtered if text_filtered else text_clean
    
    # 打分系统
    scores = []
    
    for name_zh in log_item_names:
        name_clean = clean_chinese(name_zh)
        if not name_clean:
            continue
        
        score = 0.0
        match_details = []
        
        # 1. 完全匹配 (100分)
        if match_text == name_clean:
            score = 100.0
            match_details.append("完全匹配")
        else:
            # 2. 字符匹配打分
            # 计算物品名称中有多少字符出现在OCR文本中
            matched_chars = 0
            for char in name_clean:
                if char in match_text:
                    matched_chars += 1
            
            if matched_chars > 0:
                # 字符覆盖率 (物品名称被OCR文本覆盖的比例)
                char_coverage = matched_chars / len(name_clean)
                # 基础分 = 字符覆盖率 * 40
                score += char_coverage * 40
                match_details.append(f"字符覆盖{matched_chars}/{len(name_clean)}={char_coverage:.0%}")
            
            # 3. 连续字符匹配打分
            # 检查物品名称是否作为子串出现在OCR文本中
            if name_clean in match_text:
                score += 30
                match_details.append("完整子串")
            else:
                # 检查最长公共子串
                longest_common = 0
                for i in range(len(name_clean)):
                    for j in range(i + 1, len(name_clean) + 1):
                        substr = name_clean[i:j]
                        if substr in match_text and len(substr) > longest_common:
                            longest_common = len(substr)
                
                if longest_common > 0:
                    # 连续匹配得分
                    seq_score = (longest_common / len(name_clean)) * 25
                    score += seq_score
                    match_details.append(f"连续{longest_common}字")
            
            # 4. 模糊匹配得分
            ratio = difflib.SequenceMatcher(None, match_text, name_clean).ratio()
            fuzzy_score = ratio * 20
            score += fuzzy_score
            match_details.append(f"模糊{ratio:.0%}")
            
            # 5. 位置权重 - OCR文本前几个字符匹配得分更高
            first_chars = match_text[:3]  # 取前3个字符
            first_match = 0
            for char in first_chars:
                if char in name_clean:
                    first_match += 1
            if first_match > 0:
                position_score = (first_match / len(first_chars)) * 10
                score += position_score
                match_details.append(f"首字{first_match}个")
        
        if score > 0:
            scores.append((name_zh, score, match_details))
    
    # 按分数排序
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # 显示打分结果
    if scores:
        print(f"  【打分结果】")
        for name, score, details in scores[:5]:  # 显示前5个
            print(f"    {name}: {score:.1f}分 ({', '.join(details)})")
    
    # 选择最高分且超过阈值的匹配
    threshold = 20.0  # 最低分数阈值（降低以支持单字匹配）
    
    if scores and scores[0][1] >= threshold:
        best_name = scores[0][0]
        best_score = scores[0][1]
        
        # 从 items_db 获取完整数据
        for uuid, item_data in data_loader.uuid_to_item_data.items():
            if item_data.get('name_zh') == best_name:
                print(f"  ✅ 日志匹配: {best_name} (得分: {best_score:.1f})")
                return item_data
    
    # 如果日志匹配失败，尝试全库匹配
    print(f"  日志匹配失败，尝试全库匹配...")
    all_scores = []
    
    for uuid, item_data in data_loader.uuid_to_item_data.items():
        name_zh = item_data.get('name_zh', '')
        if not name_zh:
            continue
        
        name_clean = re.sub(r'[^\u4e00-\u9fff]', '', name_zh)
        if not name_clean:
            continue
        
        score = 0.0
        
        # 字符匹配（使用过滤后的文本）
        matched_chars = sum(1 for char in name_clean if char in match_text)
        if matched_chars > 0:
            char_coverage = matched_chars / len(name_clean)
            score += char_coverage * 50  # 全库匹配权重更高
            
            # 连续匹配
            if name_clean in match_text:
                score += 40
            else:
                for i in range(len(name_clean)):
                    for j in range(i + 1, len(name_clean) + 1):
                        if name_clean[i:j] in match_text:
                            score = max(score, char_coverage * 50 + len(name_clean[i:j]) * 10)
        
        if score >= 20:
            all_scores.append((name_zh, score, item_data))
    
    all_scores.sort(key=lambda x: x[1], reverse=True)
    
    if all_scores:
        print(f"  【全库打分前5】")
        for name, score, _ in all_scores[:5]:
            print(f"    {name}: {score:.1f}分")
        
        if all_scores[0][1] >= 25:
            best_name, best_score, best_data = all_scores[0]
            print(f"  ✅ 全库匹配: {best_name} (得分: {best_score:.1f})")
            return best_data
    
    return None


def get_sample_log_items(data_loader, count=20):
    """
    模拟从日志获取的手牌/背包物品名称
    实际使用时应该从游戏日志中获取
    """
    sample_items = []
    for uuid, item_data in list(data_loader.uuid_to_item_data.items())[:count]:
        name_zh = item_data.get('name_zh', '')
        if name_zh:
            sample_items.append(name_zh)
    return sample_items


def scan_game_log(scanner, log_path):
    """
    一次性扫描游戏日志，获取物品信息
    """
    import re
    
    # 编译正则表达式
    re_purchase = re.compile(
        r"Card Purchased: InstanceId:\s*([^\s]+)\s*-\s*TemplateId([^\s-]+(?:-[^\s-]+){4})\s*-\s*Target:([^\s]+)"
    )
    re_id = re.compile(r"ID:\s*\[([^\]]+)\]")
    re_owner = re.compile(r"- Owner:\s*\[([^\]]+)\]")
    re_section = re.compile(r"- Section:\s*\[([^\]]+)\]")
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 解析购买记录
        for match in re_purchase.finditer(content):
            instance_id = match.group(1)
            template_id = match.group(2)
            target = match.group(3)
            
            scanner.instance_to_template[instance_id] = template_id
            scanner._update_template_name_mapping(template_id)
            
            if "Storage" in target:
                scanner.equipped_items.add(instance_id)
        
        # 解析物品位置信息
        lines = content.split('\n')
        current_instance_id = None
        current_owner = None
        
        for line in lines:
            line = line.strip()
            
            id_match = re_id.search(line)
            if id_match:
                current_instance_id = id_match.group(1)
                if current_instance_id.startswith('itm_'):
                    current_owner = None
            
            owner_match = re_owner.search(line)
            if owner_match:
                current_owner = owner_match.group(1)
            
            section_match = re_section.search(line)
            if section_match:
                current_section = section_match.group(1)
                
                if (current_owner == "Player" and 
                    current_instance_id and 
                    current_instance_id.startswith('itm_')):
                    if current_section == "Hand":
                        scanner.hand_items.add(current_instance_id)
                        scanner.equipped_items.add(current_instance_id)
                    elif current_section in ("Stash", "Storage"):
                        scanner.stash_items.add(current_instance_id)
                        scanner.equipped_items.add(current_instance_id)
        
        # 统计
        stats = scanner.get_item_count()
        print(f"  日志扫描完成: 手牌{stats['hand']}个, 仓库{stats['stash']}个, 已映射{stats['mapped']}种")
        
    except Exception as e:
        print(f"  扫描日志失败: {e}")


def main():
    print("=" * 60)
    print("物品OCR识别和匹配测试")
    print("=" * 60)
    
    # 加载需要排除的游戏关键字
    load_exclude_keywords()
    
    # 初始化OCR处理器
    ocr_processor = OCRProcessor()
    print("OCR处理器初始化完成")
    
    # 初始化数据加载器
    data_loader = DataLoader()
    data_loader.load_monster_data()
    data_loader.load_event_data()
    print(f"物品数据加载完成: {len(data_loader.uuid_to_item_data)} 个物品(items_db)")
    print(f"物品数据加载完成: {len(data_loader.items_data)} 个物品(items)")
    
    # 初始化日志扫描器
    print("\n" + "=" * 60)
    print("【第一步】扫描游戏日志，获取当前物品")
    print("=" * 60)
    scanner = SimpleLogScanner(data_loader.uuid_to_item_data)
    print(f"已设置UUID映射数据: {len(data_loader.uuid_to_item_data)} 个物品")
    
    # 直接构建游戏日志路径
    userprofile = os.environ.get('USERPROFILE', '')
    log_path = os.path.join(
        userprofile,
        'AppData', 'LocalLow', 'Tempo Storm', 'The Bazaar', 'Player.log'
    ) if userprofile else None
    if log_path and os.path.exists(log_path):
        print(f"✓ 游戏日志路径: {log_path}")
        # 扫描日志
        scan_game_log(scanner, log_path)
        
        # 获取所有物品
        log_item_names = scanner.get_current_items()
        hand_items = scanner.get_hand_item_names()
        stash_items = scanner.get_stash_item_names()
        
        print(f"\n【日志物品统计】")
        print(f"  手牌物品: {len(hand_items)} 个")
        print(f"  仓库物品: {len(stash_items)} 个")
        print(f"  总计: {len(log_item_names)} 个")
        
        # 列出所有手牌物品
        if hand_items:
            print(f"\n【手牌物品列表】")
            for i, name in enumerate(hand_items, 1):
                print(f"  {i:2}. {name}")
        
        # 列出所有仓库物品
        if stash_items:
            print(f"\n【仓库物品列表】")
            for i, name in enumerate(stash_items, 1):
                print(f"  {i:2}. {name}")
        
        if not log_item_names:
            print("\n⚠ 日志中未找到物品，可能是新游戏或日志已重置")
            print("  使用模拟数据进行测试...")
            log_item_names = get_sample_log_items(data_loader, 50)
    else:
        print(f"✗ 游戏日志不存在: {log_path}")
        print("  使用模拟数据进行测试...")
        log_item_names = get_sample_log_items(data_loader, 50)
        print(f"  模拟日志物品数量: {len(log_item_names)}")
    
    # 获取测试图片
    temp_dir = os.path.join(project_root, 'data', 'temp')
    if not os.path.exists(temp_dir):
        print(f"错误: 测试图片目录不存在: {temp_dir}")
        return
    
    # 获取所有PNG图片
    image_files = glob.glob(os.path.join(temp_dir, '*.png'))
    if not image_files:
        print(f"错误: 没有找到测试图片: {temp_dir}/*.png")
        return
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    # 测试每张图片
    direct_success = 0
    log_success = 0
    total_count = min(len(image_files), 10)  # 最多测试10张
    results = []
    
    for image_path in image_files[:total_count]:
        direct_match, log_match, matched_name = test_single_image(
            image_path, ocr_processor, data_loader, log_item_names
        )
        
        # 记录结果
        results.append({
            'file': os.path.basename(image_path),
            'direct': direct_match is not None,
            'log': log_match is not None,
            'name': matched_name
        })
        
        if direct_match:
            direct_success += 1
        if log_match:
            log_success += 1
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)
    print(f"测试图片数: {total_count}")
    print(f"\n【直接OCR匹配】")
    print(f"  成功数: {direct_success}")
    print(f"  成功率: {direct_success/total_count*100:.1f}%")
    print(f"\n【日志辅助匹配】(包含全库回退)")
    print(f"  成功数: {log_success}")
    print(f"  成功率: {log_success/total_count*100:.1f}%")
    
    # 显示每张图片的匹配结果
    print(f"\n【详细结果】")
    for i, r in enumerate(results, 1):
        direct_str = "✅" if r['direct'] else "❌"
        log_str = "✅" if r['log'] else "❌"
        name_str = r['name'] if r['name'] else "无"
        print(f"  {i}. {r['file'][:30]:30} 直接:{direct_str} 日志:{log_str} => {name_str}")
    
    print("\n注意:")
    print("1. 日志辅助匹配对手牌/背包物品效果最好（已知物品名称范围）")
    print("2. 非日志物品会回退到全库匹配，准确率较低")
    print("3. 物品OCR使用字体大小排序，优先识别最大的中文字符")


if __name__ == '__main__':
    main()
