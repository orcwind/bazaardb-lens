"""
数据加载模块
"""
import os
import sys
import json
import logging
import traceback

# 添加父目录到路径以便导入logger
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from logger import is_packaged_environment
from .matcher import TextMatcher


class DataLoader:
    """数据加载器类"""

    def __init__(self):
        self.monster_data = {}
        self.event_data = {}
        self.event_name_map = {}
        self.items_data = {}
        self.skills_data = {}
        self.uuid_to_item_data = {}
        self.events = []
        self.matcher = None

    def get_monster_data(self, name):
        return self.monster_data.get(name)

    def get_event_data(self, name):
        return self.event_data.get(name)

    def get_item_data(self, name):
        return self.items_data.get(name)

    def find_item_by_name(self, text):
        """
        根据OCR文本查找物品，返回物品数据或None
        支持中文名称匹配，返回包含附魔信息的物品数据
        """
        import re
        import difflib
        
        if not text:
            return None
        
        # 清理文本，提取中文名称
        def clean_text_chinese_only(s):
            if not isinstance(s, str):
                return ""
            s = re.sub(r'[^\u4e00-\u9fff]', '', s)
            return s
        
        text_clean = clean_text_chinese_only(text)
        if not text_clean or len(text_clean) < 2:
            return None
        
        logging.info(f"[物品匹配] OCR文本: {text}, 清理后: {text_clean}")
        
        best_match = None
        best_ratio = 0.0
        best_name = None
        
        # 遍历 uuid_to_item_data (items_db.json，包含附魔信息)
        for uuid, item_data in self.uuid_to_item_data.items():
            name_zh = item_data.get('name_zh', '')
            name_en = item_data.get('name', '')
            
            if not name_zh:
                continue
            
            name_zh_clean = clean_text_chinese_only(name_zh)
            if not name_zh_clean:
                continue
            
            # 完全匹配
            if text_clean == name_zh_clean:
                logging.info(f"[物品匹配] ✅ 完全匹配: {text_clean} -> {name_zh}")
                return item_data
            
            # 部分匹配（OCR文本在物品名称中）
            if text_clean in name_zh_clean:
                ratio = len(text_clean) / len(name_zh_clean)
                if ratio >= 0.5:
                    logging.info(f"[物品匹配] ✅ 部分匹配(OCR在名称中): {text_clean} -> {name_zh} (比例: {ratio:.2f})")
                    return item_data
            
            # 物品名称在OCR文本中
            if name_zh_clean in text_clean:
                ratio = len(name_zh_clean) / len(text_clean)
                if ratio >= 0.3:
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = item_data
                        best_name = name_zh
            
            # 模糊匹配
            ratio = difflib.SequenceMatcher(None, text_clean, name_zh_clean).ratio()
            if ratio > best_ratio and ratio >= 0.5:
                best_ratio = ratio
                best_match = item_data
                best_name = name_zh
        
        if best_match and best_ratio >= 0.4:
            logging.info(f"[物品匹配] ✅ 模糊匹配: {text_clean} -> {best_name} (相似度: {best_ratio:.2f})")
            return best_match
        
        logging.warning(f"[物品匹配] ❌ 未找到匹配: {text_clean}")
        return None

    def get_base_dir(self):
        if is_packaged_environment():
            return os.path.dirname(sys.executable)
        else:
            current_file = os.path.abspath(__file__)
            data_dir = os.path.dirname(current_file)
            main_script_dir = os.path.dirname(data_dir)
            project_root = os.path.dirname(main_script_dir)
            return project_root

    def load_monster_data(self):
        try:
            base_dir = self.get_base_dir()
            monster_file = os.path.join(base_dir, 'data', 'Json', 'monsters_detail.json')
            if not os.path.exists(monster_file):
                monster_file = os.path.join(base_dir, 'data', 'Json - 副本', 'monsters_detail.json')
                if not os.path.exists(monster_file):
                    monster_file = os.path.join(base_dir, '6.0', 'crawlers', 'monster_details_v3', 'monsters_v3.json')
            with open(monster_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.monster_data = {monster['name_zh']: monster for monster in data}
                else:
                    self.monster_data = {monster['name']: monster for monster in data}
                logging.info(f"成功加载怪物数据，共 {len(self.monster_data)} 个怪物")
                self.load_items_data()
                self.load_skills_data()
        except Exception as e:
            logging.error(f"加载怪物数据失败: {e}")
            self.monster_data = {}

    def load_items_data(self):
        try:
            base_dir = self.get_base_dir()
            items_file = os.path.join(base_dir, 'data', 'Json', 'items.json')
            if not os.path.exists(items_file):
                items_file = os.path.join(base_dir, 'data', 'Json - 副本', 'items.json')
            if os.path.exists(items_file):
                with open(items_file, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    self.items_data = {item['name']: item for item in items}
                    logging.info(f"成功加载物品数据，共 {len(self.items_data)} 个物品")
                items_db_file = os.path.join(base_dir, 'data', 'Json', 'items_db.json')
                if os.path.exists(items_db_file):
                    with open(items_db_file, 'r', encoding='utf-8') as f:
                        self.uuid_to_item_data = json.load(f)
                        logging.info(f"成功加载UUID映射数据，共 {len(self.uuid_to_item_data)} 个物品UUID")
                else:
                    self.uuid_to_item_data = {}
        except Exception as e:
            logging.error(f"加载物品数据失败: {e}")
            self.items_data = {}
            self.uuid_to_item_data = {}

    def load_skills_data(self):
        try:
            base_dir = self.get_base_dir()
            skills_file = os.path.join(base_dir, 'data', 'Json', 'skills.json')
            if not os.path.exists(skills_file):
                skills_file = os.path.join(base_dir, 'data', 'Json - 副本', 'skills.json')
            if os.path.exists(skills_file):
                with open(skills_file, 'r', encoding='utf-8') as f:
                    skills = json.load(f)
                    self.skills_data = {skill['name']: skill for skill in skills}
                    logging.info(f"成功加载技能数据，共 {len(self.skills_data)} 个技能")
        except Exception as e:
            logging.error(f"加载技能数据失败: {e}")
            self.skills_data = {}

    def load_event_data(self):
        try:
            base_dir = self.get_base_dir()
            event_file = os.path.join(base_dir, 'data', 'Json', 'events_from_html.json')
            if not os.path.exists(event_file):
                event_file = os.path.join(base_dir, '6.0', 'crawlers', 'event_details_final', 'events_final.json')
            with open(event_file, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                logging.info(f"已加载 {len(self.events)} 个事件")
                self.event_data = {}
                self.event_name_map = {}
                for event in self.events:
                    if 'name' in event and 'choices' in event:
                        chinese_name = event['name']
                        english_name = event.get('name_en', '')
                        self.event_data[chinese_name] = event['choices']
                        if english_name:
                            self.event_name_map[chinese_name] = english_name
                            self.event_data[english_name] = event['choices']
                    else:
                        logging.warning(f"事件 {event.get('name', '')} 缺少 choices 字段")
        except Exception as e:
            logging.error(f"加载事件数据时出错: {e}")
            logging.error(traceback.format_exc())
            self.events = []
            self.event_data = {}
            self.event_name_map = {}
        
        # 初始化文本匹配器
        logging.info(f"[DataLoader] ========== 开始初始化文本匹配器 ==========")
        logging.info(f"[DataLoader] monster_data数量: {len(self.monster_data)}")
        logging.info(f"[DataLoader] event_data数量: {len(self.event_data)}")
        logging.info(f"[DataLoader] events数量: {len(self.events)}")
        try:
            logging.info(f"[DataLoader] 开始创建TextMatcher实例...")
            self.matcher = TextMatcher(
                monster_data=self.monster_data,
                event_data=self.event_data,
                events=self.events)
            logging.info(f"[DataLoader] 文本匹配器初始化成功: {type(self.matcher).__name__}")
            logging.info(f"[DataLoader] ========== 文本匹配器初始化完成 ==========")
        except Exception as e:
            logging.error(f"[DataLoader] 初始化文本匹配器失败: {e}")
            logging.error(traceback.format_exc())
            self.matcher = None
