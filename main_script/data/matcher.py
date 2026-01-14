"""
文本匹配模块 - 完全按照旧脚本Bazaar_Lens.py的逻辑实现
"""
import re
import difflib
import logging


class TextMatcher:
    """文本匹配器类 - 完全按照旧脚本的逻辑"""

    def __init__(self, monster_data=None, event_data=None, events=None):
        self.monster_data = monster_data or {}
        self.event_data = event_data or {}
        self.events = events or []  # 事件列表（用于匹配）
        self.match_cache = {}  # OCR文本 -> 匹配结果缓存
        self.match_cache_max_size = 100  # 缓存最大大小

    def find_best_match(self, text):
        """
        统一识别怪物或事件，返回('monster'/'event', 名称)或(None, None)
        完全按照旧脚本Bazaar_Lens.py的逻辑实现
        """
        if not text:
            return None, None
        
        # 检查匹配结果缓存（基于OCR文本）
        text_key = text.strip()[:100]  # 使用前100个字符作为key
        if text_key in self.match_cache:
            logging.debug("使用匹配结果缓存")
            return self.match_cache[text_key]
            
        def clean_text(s):
            """清理英文文本：保留字母和空格"""
            if not isinstance(s, str):
                return ""
            # 保留字母和空格，移除其他字符
            s = re.sub(r'[^a-zA-Z\s]', ' ', s)
            # 合并多个空格为单个空格并转小写
            return ' '.join(s.split()).lower()
            
        def clean_text_chinese(s):
            """清理中文文本：保留中文字符、字母、数字和空格"""
            if not isinstance(s, str):
                return ""
            # 保留中文字符、字母、数字和空格
            s = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', s)
            # 合并多个空格为单个空格
            return ' '.join(s.split())
        
        def clean_text_chinese_no_space(s):
            """清理中文文本：移除所有空格，只保留中文字符、字母、数字"""
            if not isinstance(s, str):
                return ""
            # 保留中文字符、字母、数字，移除所有空格和其他字符
            s = re.sub(r'[^\u4e00-\u9fff\w]', '', s)
            return s
        
        def clean_text_chinese_only(s):
            """清理文本：只保留纯中文字符，排除所有数字、字母、标点等"""
            if not isinstance(s, str):
                return ""
            # 只保留中文字符（\u4e00-\u9fff），排除所有其他字符（包括数字0-9、字母、标点等）
            s = re.sub(r'[^\u4e00-\u9fff]', '', s)
            return s
        
        def extract_name_candidates(line):
            """从OCR文本中提取可能的名称候选（过滤无关词，优化：优先从开头提取、优先长词）"""
            if not line:
                return []
            
            # 常见无关词（游戏UI中常见的词，但不是怪物/事件名称）
            common_noise_words = {
                '奖励', '人', '全', '合', '使', '倒', '含', '和', '由', '国', '蕊', 
                '本', '上', '站', '机', '作', '区'
            }
            
            # 关键优化：如果包含"奖励"，只保留"奖励"之前的内容
            if '奖励' in line:
                reward_index = line.find('奖励')
                if reward_index > 0:
                    line = line[:reward_index].strip()
                elif reward_index == 0:
                    return []
            
            # 只保留纯中文字符（排除所有数字、字母、标点等）
            clean_zh_only = clean_text_chinese_only(line)
            
            if not clean_zh_only or len(clean_zh_only) < 2:
                return []
            
            candidates = []
            
            # 策略1：从开头提取2-8个连续字符（最可能匹配）
            for length in range(min(8, len(clean_zh_only)), 1, -1):
                candidate = clean_zh_only[:length]
                if not all(c in common_noise_words for c in candidate):
                    candidates.append(candidate)
            
            # 策略2：提取包含关键词的长候选
            keywords = ['的', '咖啡', '店', '朱尔斯', '失落', '宝箱', '事件', '物品']
            for keyword in keywords:
                if keyword in clean_zh_only:
                    keyword_index = clean_zh_only.find(keyword)
                    for start in range(max(0, keyword_index - 6), keyword_index + 1):
                        for length in range(min(10, len(clean_zh_only) - start), len(keyword), -1):
                            if start + length <= len(clean_zh_only):
                                candidate = clean_zh_only[start:start+length]
                                if keyword in candidate and len(candidate) >= 3:
                                    if not all(c in common_noise_words for c in candidate):
                                        if candidate not in candidates:
                                            candidates.append(candidate)
            
            # 策略3：如果从开头提取的候选不足，再从其他位置提取
            if len(candidates) < 15:
                for start in range(1, len(clean_zh_only)):
                    for length in range(min(8, len(clean_zh_only) - start), 1, -1):
                        candidate = clean_zh_only[start:start+length]
                        if not all(c in common_noise_words for c in candidate):
                            if candidate not in candidates:
                                candidates.append(candidate)
                                if len(candidates) >= 15:
                                    break
                    if len(candidates) >= 15:
                        break
            
            # 去重并排序（优先长词）
            candidates = sorted(set(candidates), key=lambda x: (-len(x), x))
            return candidates[:15]
        
        # 处理文本行：同时支持英文和中文
        raw_lines = [line.strip() for line in str(text).split('\n') if line.strip()]
        lines_english = []
        lines_chinese = []
        
        for line in raw_lines:
            clean_en = clean_text(line)
            clean_zh = clean_text_chinese(line)
            
            # 排除包含"奖励"的完整行
            if '奖励' in clean_zh:
                reward_index = clean_zh.find('奖励')
                if reward_index > 0:
                    clean_zh = clean_zh[:reward_index].strip()
                elif reward_index == 0:
                    continue
            
            if len(clean_en) >= 3:
                lines_english.append(clean_en)
            if len(clean_zh) >= 2:
                lines_chinese.append(clean_zh)
                # 提取名称候选并添加到匹配列表
                name_candidates = extract_name_candidates(clean_zh)
                for candidate in name_candidates:
                    if candidate not in lines_chinese:
                        lines_chinese.append(candidate)
        
        if lines_english or lines_chinese:
            logging.debug(f"[匹配调试] OCR文本行(英文): {lines_english[:5]}")
            logging.debug(f"[匹配调试] OCR文本行(中文): {lines_chinese[:10]}")
        
        best_type = None
        best_name = None
        best_ratio = 0.0
        all_matches = []
        
        # 优化：先匹配事件，再匹配怪物（事件名称通常更长更具体，优先级更高）
        logging.debug(f"[匹配调试] 开始匹配事件，共有 {len(self.events)} 个事件，{len(lines_chinese)} 行中文文本")
        for event in self.events:
            event_name_zh = event.get('name', '')
            event_name_en = event.get('name_en', '')
            
            # 先尝试中文匹配（快速路径）
            if event_name_zh:
                event_clean_zh_only = clean_text_chinese_only(event_name_zh)
                
                for line in lines_chinese:
                    line_clean_only = clean_text_chinese_only(line)
                    
                    # 快速匹配1：完全匹配（纯中文字符）
                    if line_clean_only == event_clean_zh_only and len(line_clean_only) >= 2:
                        logging.info(f"找到完全匹配的事件(中文): {event_name_zh}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2：部分匹配：检查事件名称是否包含在OCR文本中
                    if event_clean_zh_only in line_clean_only and len(event_clean_zh_only) >= 2:
                        logging.info(f"找到部分匹配的事件(事件名在OCR文本中): {event_name_zh}, OCR行: {line}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    # 快速匹配2.5：反向部分匹配
                    if len(line_clean_only) >= 2 and line_clean_only in event_clean_zh_only:
                        ratio = len(line_clean_only) / len(event_clean_zh_only) if event_clean_zh_only else 0
                        if ratio > 0.5:
                            logging.info(f"找到部分匹配的事件(OCR文本在事件名中): {event_name_zh}, OCR行: {line}, 匹配度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    # 改进的匹配：检查关键字符匹配
                    if len(event_clean_zh_only) >= 2 and len(line_clean_only) >= 2:
                        matched_chars = sum(1 for c in event_clean_zh_only if c in line_clean_only)
                        match_ratio = matched_chars / len(event_clean_zh_only) if event_clean_zh_only else 0
                        
                        # 对于长事件名称（5+字符），降低字符匹配阈值
                        if len(event_clean_zh_only) >= 5:
                            if match_ratio >= 0.6:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.3:
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                        elif len(event_clean_zh_only) == 4:
                            if match_ratio >= 0.75:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.3:
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                            elif match_ratio >= 0.5:
                                ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                                if ratio > 0.4:
                                    logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}, 相似度: {ratio:.2f}")
                                    result = ('event', event_name_zh)
                                    if len(self.match_cache) >= self.match_cache_max_size:
                                        oldest_key = next(iter(self.match_cache))
                                        del self.match_cache[oldest_key]
                                    self.match_cache[text_key] = result
                                    return result
                        elif match_ratio > 0.5:
                            logging.info(f"找到关键字符匹配的事件: {event_name_zh}, OCR行: {line}, 字符匹配度: {match_ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                    
                    # 慢速匹配：相似度匹配
                    if len(line_clean_only) >= 2:
                        ratio = difflib.SequenceMatcher(None, line_clean_only, event_clean_zh_only).ratio()
                        if ratio > 0.5:
                            logging.info(f"找到相似匹配的事件: {event_name_zh}, OCR行: {line}, 相似度: {ratio:.2f}")
                            result = ('event', event_name_zh)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                        elif ratio > 0.3:
                            all_matches.append({
                                'type': 'event',
                                'name': event_name_zh,
                                'line': line,
                                'ratio': ratio,
                                'common_words': []
                            })
                            if ratio > best_ratio:
                                best_ratio = ratio
                                best_type = 'event'
                                best_name = event_name_zh
            
            # 再尝试英文匹配
            if event_name_en:
                event_clean_en = clean_text(event_name_en)
                for line in lines_english:
                    if line == event_clean_en:
                        logging.info(f"找到完全匹配的事件(英文): {event_name_en}")
                        result = ('event', event_name_zh)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    event_words = set(event_clean_en.split())
                    line_words = set(line.split())
                    common_words = event_words & line_words
                    
                    if len(common_words) > 0:
                        ratio = difflib.SequenceMatcher(None, line, event_clean_en).ratio()
                        all_matches.append({
                            'type': 'event',
                            'name': event_name_zh,
                            'line': line,
                            'ratio': ratio,
                            'common_words': list(common_words)
                        })
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_type = 'event'
                            best_name = event_name_zh
        
        # 匹配怪物（优先使用中文，因为新数据源使用中文名称作为key）
        for monster_name in self.monster_data:
            monster_info = self.monster_data[monster_name]
            monster_name_en = monster_info.get('name', '') if isinstance(monster_info, dict) else ''
            
            # 先尝试中文匹配
            monster_clean_zh_only = clean_text_chinese_only(monster_name)
            monster_chars = set(monster_clean_zh_only)
            
            for line in lines_chinese:
                line_clean_zh_only = clean_text_chinese_only(line)
                
                # 完全匹配（纯中文字符）
                if line_clean_zh_only == monster_clean_zh_only and len(line_clean_zh_only) >= 2:
                    logging.info(f"找到完全匹配的怪物(中文): {monster_name}")
                    result = ('monster', monster_name)
                    if len(self.match_cache) >= self.match_cache_max_size:
                        oldest_key = next(iter(self.match_cache))
                        del self.match_cache[oldest_key]
                    self.match_cache[text_key] = result
                    return result
                
                # 部分匹配：怪物名称在OCR文本中
                if monster_clean_zh_only in line_clean_zh_only and len(monster_clean_zh_only) >= 2:
                    ratio = len(monster_clean_zh_only) / len(line_clean_zh_only) if line_clean_zh_only else 0
                    if ratio > 0.5:
                        logging.info(f"找到部分匹配的怪物(中文): {monster_name}, 匹配度: {ratio:.2f}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                
                # 部分匹配：OCR文本在怪物名称中
                if line_clean_zh_only in monster_clean_zh_only and len(line_clean_zh_only) >= 2:
                    ratio = len(line_clean_zh_only) / len(monster_clean_zh_only) if monster_clean_zh_only else 0
                    if ratio > 0.5:
                        logging.info(f"找到部分匹配的怪物(中文): {monster_name}, 匹配度: {ratio:.2f}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                
                # 字符级别匹配
                if len(monster_chars) >= 2 and len(line_clean_zh_only) >= 2:
                    line_chars = set(line_clean_zh_only)
                    matched_chars = monster_chars & line_chars
                    char_match_ratio = len(matched_chars) / len(monster_chars) if monster_chars else 0
                    
                    monster_name_len = len(monster_clean_zh_only)
                    if monster_name_len == 2:
                        required_char_ratio = 0.5
                        min_matched_chars = 1
                    elif monster_name_len == 3:
                        required_char_ratio = 0.6
                        min_matched_chars = 2
                    elif monster_name_len == 4:
                        required_char_ratio = 0.5
                        min_matched_chars = 2
                    else:
                        required_char_ratio = 0.4
                        min_matched_chars = max(2, int(monster_name_len * 0.4))
                    
                    if char_match_ratio >= required_char_ratio and len(matched_chars) >= min_matched_chars:
                        ratio = difflib.SequenceMatcher(None, line_clean_zh_only, monster_clean_zh_only).ratio()
                        similarity_threshold = 0.30 if monster_name_len >= 5 else 0.35
                        
                        if ratio > similarity_threshold:
                            logging.info(f"找到字符匹配的怪物(中文): {monster_name}, 字符匹配度: {char_match_ratio:.2f}, 相似度: {ratio:.2f}, 名称长度: {monster_name_len}")
                            result = ('monster', monster_name)
                            if len(self.match_cache) >= self.match_cache_max_size:
                                oldest_key = next(iter(self.match_cache))
                                del self.match_cache[oldest_key]
                            self.match_cache[text_key] = result
                            return result
                
                # 模糊匹配（根据名称长度调整阈值）
                if len(line_clean_zh_only) >= 2:
                    ratio = difflib.SequenceMatcher(None, line_clean_zh_only, monster_clean_zh_only).ratio()
                    monster_name_len = len(monster_clean_zh_only)
                    
                    if monster_name_len <= 2:
                        immediate_threshold = 0.35
                        candidate_threshold = 0.20
                    elif monster_name_len == 3:
                        immediate_threshold = 0.5
                        candidate_threshold = 0.35
                    elif monster_name_len == 4:
                        immediate_threshold = 0.40
                        candidate_threshold = 0.30
                    else:
                        immediate_threshold = 0.40
                        candidate_threshold = 0.30
                    
                    if ratio > immediate_threshold:
                        logging.info(f"找到相似匹配的怪物(中文): {monster_name}, 相似度: {ratio:.2f}, 名称长度: {monster_name_len}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    elif ratio > candidate_threshold:
                        all_matches.append({
                            'type': 'monster',
                            'name': monster_name,
                            'line': line,
                            'ratio': ratio,
                            'common_words': []
                        })
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_type = 'monster'
                            best_name = monster_name
            
            # 再尝试英文匹配（兼容旧数据源）
            if monster_name_en:
                monster_clean_en = clean_text(monster_name_en)
                for line in lines_english:
                    if line == monster_clean_en:
                        logging.info(f"找到完全匹配的怪物(英文): {monster_name_en}")
                        result = ('monster', monster_name)
                        if len(self.match_cache) >= self.match_cache_max_size:
                            oldest_key = next(iter(self.match_cache))
                            del self.match_cache[oldest_key]
                        self.match_cache[text_key] = result
                        return result
                    
                    monster_words = set(monster_clean_en.split())
                    line_words = set(line.split())
                    common_words = monster_words & line_words
                    
                    if len(common_words) > 0:
                        ratio = difflib.SequenceMatcher(None, line, monster_clean_en).ratio()
                        all_matches.append({
                            'type': 'monster',
                            'name': monster_name,
                            'line': line,
                            'ratio': ratio,
                            'common_words': list(common_words)
                        })
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_type = 'monster'
                            best_name = monster_name
        
        # 输出所有匹配结果用于调试
        if all_matches:
            logging.debug(f"[匹配调试] 找到 {len(all_matches)} 个候选匹配:")
            for match in sorted(all_matches, key=lambda x: x['ratio'], reverse=True)[:5]:
                logging.debug(f"  - {match['type']}: {match['name']}, 相似度: {match['ratio']:.2f}, OCR行: {match['line'][:30]}")
        else:
            logging.debug(f"[匹配调试] 未找到任何候选匹配（all_matches为空）")
        
        # 匹配阈值：根据匹配到的名称长度动态调整
        result = None, None
        if best_name:
            name_len = len(clean_text_chinese_only(best_name))
            if name_len <= 3:
                threshold = 0.40
            elif name_len == 4:
                threshold = 0.35
            else:
                threshold = 0.30
            logging.debug(f"[最终阈值判断] 最佳匹配: {best_type} - {best_name} (名称长度: {name_len}字符, 相似度: {best_ratio:.2f}, 阈值: {threshold:.2f})")
        else:
            threshold = 0.35
            logging.debug(f"[最终阈值判断] 无最佳匹配 (best_name=None, best_ratio={best_ratio:.2f}, 默认阈值: {threshold:.2f})")
        
        if best_ratio >= threshold:
            logging.info(f"[最终阈值判断] ✅ 匹配成功: {best_type} - {best_name} (相似度: {best_ratio:.2f} >= 阈值: {threshold:.2f})")
            result = best_type, best_name
        else:
            logging.debug(f"[最终阈值判断] ❌ 匹配失败: 最佳相似度 {best_ratio:.2f} < 阈值 {threshold:.2f} (最佳名称: {best_name})")
        
        # 缓存匹配结果（限制缓存大小）
        if len(self.match_cache) >= self.match_cache_max_size:
            oldest_key = next(iter(self.match_cache))
            del self.match_cache[oldest_key]
        self.match_cache[text_key] = result
        
        return result
