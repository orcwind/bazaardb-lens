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
# 可选的安全数据包（如果存在 data_json.enc / data_key.bin）
try:
    from core.secure_data import secure_bundle
except Exception:
    secure_bundle = None


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
            data = None
            # 优先从加密包读取
            if secure_bundle:
                try:
                    data = secure_bundle.get_json('monsters_detail.json')
                    if data is not None:
                        logging.info("[DataLoader] 从加密包加载 monsters_detail.json")
                except Exception as e:
                    logging.error(f"[DataLoader] 从加密包加载 monsters_detail.json 出错: {e}")

            # 打包环境：仅允许从加密包读取
            if is_packaged_environment():
                if data is None:
                    logging.error("[DataLoader] 打包环境：加密包不可用，无法加载 monsters_detail.json")
            else:
                # 开发环境：若加密包不可用则从磁盘回退读取
                if data is None:
                    monster_file = os.path.join(base_dir, 'data', 'Json', 'monsters_detail.json')
                    if not os.path.exists(monster_file):
                        monster_file = os.path.join(base_dir, 'data', 'Json - 副本', 'monsters_detail.json')
                    if os.path.exists(monster_file):
                        try:
                            with open(monster_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            logging.info(f"[DataLoader] 开发环境：从磁盘加载 monsters_detail.json: {monster_file}")
                        except Exception as e:
                            logging.error(f"[DataLoader] 从磁盘加载 monsters_detail.json 出错: {e}")
                    else:
                        logging.warning(f"[DataLoader] 开发环境：未找到 monsters_detail.json")

            # 处理加载到的 data（无论来自加密包还是磁盘）
            if data is not None:
                if isinstance(data, list):
                    self.monster_data = {monster.get('name_zh', monster.get('name')): monster for monster in data if monster}
                else:
                    try:
                        self.monster_data = {k: v for k, v in data.items()}
                    except Exception:
                        self.monster_data = {}

                logging.info(f"成功加载怪物数据，共 {len(self.monster_data)} 个怪物")
                # 继续加载物品与技能数据（依赖于 monster_data）
                self.load_items_data()
                self.load_skills_data()
            else:
                self.monster_data = {}
        except Exception as e:
            logging.error(f"加载怪物数据失败: {e}")
            logging.error(traceback.format_exc())
            self.monster_data = {}

    def load_items_data(self):
        try:
            base_dir = self.get_base_dir()
            items = None
            # 优先从加密包读取
            if secure_bundle:
                try:
                    items = secure_bundle.get_json('items.json')
                    if items is not None:
                        logging.info("[DataLoader] 从加密包加载 items.json")
                except Exception as e:
                    logging.error(f"[DataLoader] 从加密包加载 items.json 出错: {e}")

            if is_packaged_environment():
                if items is None:
                    logging.error("[DataLoader] 打包环境：加密包不可用，无法加载 items.json")
            else:
                if items is None:
                    items_file = os.path.join(base_dir, 'data', 'Json', 'items.json')
                    if not os.path.exists(items_file):
                        items_file = os.path.join(base_dir, 'data', 'Json - 副本', 'items.json')
                    if os.path.exists(items_file):
                        try:
                            with open(items_file, 'r', encoding='utf-8') as f:
                                items = json.load(f)
                            logging.info(f"[DataLoader] 开发环境：从磁盘加载 items.json: {items_file}")
                        except Exception as e:
                            logging.error(f"[DataLoader] 从磁盘加载 items.json 出错: {e}")

            if items:
                try:
                    self.items_data = {item['name']: item for item in items}
                    logging.info(f"成功加载物品数据，共 {len(self.items_data)} 个物品")
                except Exception:
                    self.items_data = {}

            # items_db.json (uuid 映射)
            uuid_items = None
            if secure_bundle:
                try:
                    uuid_items = secure_bundle.get_json('items_db.json')
                    if uuid_items is not None:
                        logging.info("[DataLoader] 从加密包加载 items_db.json")
                except Exception as e:
                    logging.error(f"[DataLoader] 从加密包加载 items_db.json 出错: {e}")

            if is_packaged_environment():
                if uuid_items is None:
                    logging.error("[DataLoader] 打包环境：加密包不可用，无法加载 items_db.json")
            else:
                if uuid_items is None:
                    items_db_file = os.path.join(base_dir, 'data', 'Json', 'items_db.json')
                    if os.path.exists(items_db_file):
                        try:
                            with open(items_db_file, 'r', encoding='utf-8') as f:
                                uuid_items = json.load(f)
                            logging.info(f"[DataLoader] 开发环境：从磁盘加载 items_db.json: {items_db_file}")
                        except Exception as e:
                            logging.error(f"[DataLoader] 从磁盘加载 items_db.json 出错: {e}")

            if uuid_items:
                self.uuid_to_item_data = uuid_items
                logging.info(f"成功加载UUID映射数据，共 {len(self.uuid_to_item_data)} 个物品UUID")
            else:
                self.uuid_to_item_data = {}
        except Exception as e:
            logging.error(f"加载物品数据失败: {e}")
            logging.error(traceback.format_exc())
            self.items_data = {}
            self.uuid_to_item_data = {}

    def load_skills_data(self):
        try:
            base_dir = self.get_base_dir()
            skills = None
            if secure_bundle:
                try:
                    skills = secure_bundle.get_json('skills.json')
                    if skills is not None:
                        logging.info("[DataLoader] 从加密包加载 skills.json")
                except Exception as e:
                    logging.error(f"[DataLoader] 从加密包加载 skills.json 出错: {e}")

            if is_packaged_environment():
                if skills is None:
                    logging.error("[DataLoader] 打包环境：加密包不可用，无法加载 skills.json")
            else:
                if skills is None:
                    skills_file = os.path.join(base_dir, 'data', 'Json', 'skills.json')
                    if not os.path.exists(skills_file):
                        skills_file = os.path.join(base_dir, 'data', 'Json - 副本', 'skills.json')
                    if os.path.exists(skills_file):
                        try:
                            with open(skills_file, 'r', encoding='utf-8') as f:
                                skills = json.load(f)
                            logging.info(f"[DataLoader] 开发环境：从磁盘加载 skills.json: {skills_file}")
                        except Exception as e:
                            logging.error(f"[DataLoader] 从磁盘加载 skills.json 出错: {e}")

            if skills:
                try:
                    self.skills_data = {skill['name']: skill for skill in skills}
                    logging.info(f"成功加载技能数据，共 {len(self.skills_data)} 个技能")
                except Exception:
                    self.skills_data = {}
        except Exception as e:
            logging.error(f"加载技能数据失败: {e}")
            logging.error(traceback.format_exc())
            self.skills_data = {}
    def load_event_data(self):
        try:
            base_dir = self.get_base_dir()
            events = None
            # 优先从加密包读取
            if secure_bundle:
                try:
                    events = secure_bundle.get_json('events_from_html.json')
                    if events is not None:
                        logging.info("[DataLoader] 从加密包加载 events_from_html.json")
                except Exception as e:
                    logging.error(f"[DataLoader] 从加密包加载 events_from_html.json 出错: {e}")

            if is_packaged_environment():
                if events is None:
                    logging.error("[DataLoader] 打包环境：加密包不可用，无法加载 events_from_html.json")
            else:
                if events is None:
                    event_file = os.path.join(base_dir, 'data', 'Json', 'events_from_html.json')
                    if os.path.exists(event_file):
                        try:
                            with open(event_file, 'r', encoding='utf-8') as f:
                                events = json.load(f)
                            logging.info(f"[DataLoader] 开发环境：从磁盘加载 events_from_html.json: {event_file}")
                        except Exception as e:
                            logging.error(f"[DataLoader] 从磁盘加载 events_from_html.json 出错: {e}")
                    else:
                        logging.warning(f"[DataLoader] 开发环境：未找到 events_from_html.json")

            if events is None:
                self.events = []
                logging.warning("[DataLoader] events 为 None，设置为空列表")
            else:
                self.events = events
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
