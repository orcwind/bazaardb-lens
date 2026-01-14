#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试匹配逻辑"""

import re
import difflib

def clean_text_chinese_only(s):
    """清理文本：只保留纯中文字符，排除所有数字、字母、标点等"""
    if not isinstance(s, str):
        return ""
    # 只保留中文字符
    return re.sub(r'[^\u4e00-\u9fff]', '', s)

def analyze_matching(ocr_text, monster_name):
    """分析匹配过程"""
    print(f"\n{'='*80}")
    print(f"分析匹配: OCR文本='{ocr_text}' vs 怪物名称='{monster_name}'")
    print(f"{'='*80}")
    
    # 清理文本
    ocr_clean = clean_text_chinese_only(ocr_text)
    monster_clean = clean_text_chinese_only(monster_name)
    
    print(f"清理后: OCR='{ocr_clean}' ({len(ocr_clean)}字), 怪物='{monster_clean}' ({len(monster_clean)}字)")
    
    # 1. 检查完整匹配
    if monster_clean in ocr_clean:
        print(f"\n1. 完整匹配: ✅ 怪物名称在OCR文本中")
        print(f"   相似度: 1.0")
        return
    
    # 2. 检查部分匹配
    if ocr_clean in monster_clean:
        ratio = len(ocr_clean) / len(monster_clean)
        print(f"\n2. 部分匹配: OCR文本在怪物名称中")
        print(f"   匹配度: {ratio:.2f}")
        if ratio > 0.5:
            print(f"   ✅ 匹配度 > 0.5")
        else:
            print(f"   ❌ 匹配度 <= 0.5")
    
    # 3. 字符级别匹配
    monster_chars = set(monster_clean)
    ocr_chars = set(ocr_clean)
    matched_chars = monster_chars & ocr_chars
    
    print(f"\n3. 字符级别匹配:")
    print(f"   怪物字符集: {monster_chars}")
    print(f"   OCR字符集: {ocr_chars}")
    print(f"   匹配字符: {matched_chars} ({len(matched_chars)}个)")
    
    if monster_clean:
        char_match_ratio = len(matched_chars) / len(monster_clean)
        print(f"   字符匹配度: {char_match_ratio:.2f} ({len(matched_chars)}/{len(monster_clean)})")
        
        # 检查匹配要求
        monster_name_len = len(monster_clean)
        if monster_name_len == 2:
            required_char_ratio = 0.5
            min_matched_chars = 1
        elif monster_name_len == 3:
            required_char_ratio = 0.6
            min_matched_chars = 2
        elif monster_name_len == 4:
            required_char_ratio = 0.60
            min_matched_chars = 2
        else:
            required_char_ratio = 0.4
            min_matched_chars = max(2, int(monster_name_len * 0.4))
        
        print(f"   要求: 字符匹配度 >= {required_char_ratio}, 最小匹配字符 >= {min_matched_chars}")
        
        if char_match_ratio >= required_char_ratio and len(matched_chars) >= min_matched_chars:
            print(f"   ✅ 满足字符匹配要求")
            
            # 计算相似度
            ratio = difflib.SequenceMatcher(None, ocr_clean, monster_clean).ratio()
            similarity_threshold = 0.30 if monster_name_len >= 5 else 0.35
            
            print(f"   相似度: {ratio:.2f}, 阈值: {similarity_threshold}")
            if ratio > similarity_threshold:
                print(f"   ✅ 相似度 > 阈值")
            else:
                print(f"   ❌ 相似度 <= 阈值")
        else:
            print(f"   ❌ 不满足字符匹配要求")
    
    # 4. 模糊匹配
    print(f"\n4. 模糊匹配:")
    if len(ocr_clean) >= 2:
        ratio = difflib.SequenceMatcher(None, ocr_clean, monster_clean).ratio()
        monster_name_len = len(monster_clean)
        
        if monster_name_len <= 2:
            immediate_threshold = 0.35
            candidate_threshold = 0.20
        elif monster_name_len == 3:
            immediate_threshold = 0.5
            candidate_threshold = 0.35
        elif monster_name_len == 4:
            immediate_threshold = 0.45
            candidate_threshold = 0.35
        else:
            immediate_threshold = 0.40
            candidate_threshold = 0.30
        
        print(f"   相似度: {ratio:.2f}")
        print(f"   立即匹配阈值: {immediate_threshold}, 候选阈值: {candidate_threshold}")
        
        if ratio > immediate_threshold:
            print(f"   ✅ 立即匹配 (相似度 > {immediate_threshold})")
        elif ratio > candidate_threshold:
            print(f"   ⚠️  候选匹配 (相似度 > {candidate_threshold})")
        else:
            print(f"   ❌ 不匹配 (相似度 <= {candidate_threshold})")

def main():
    """主函数"""
    print("调试匹配逻辑")
    print("=" * 80)
    
    # 测试案例1：实际日志中的情况
    analyze_matching("2 和和 于 舞火大师", "舞火大师")
    analyze_matching("2 和和 于 舞火大师", "火灵")
    
    # 测试案例2：清理后的文本
    analyze_matching("和和于舞火大师", "舞火大师")
    analyze_matching("和和于舞火大师", "火灵")
    
    # 测试案例3：理想情况
    analyze_matching("舞火大师", "舞火大师")
    analyze_matching("火大师", "舞火大师")
    analyze_matching("火灵", "火灵")

if __name__ == "__main__":
    main()