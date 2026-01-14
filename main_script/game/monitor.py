"""
游戏日志监控模块
从游戏日志中提取物品信息，用于辅助OCR匹配
"""
import os
import re
import time
import threading
import logging


class LogMonitor:
    """游戏日志监控类"""

    def __init__(self):
        self.log_monitor_thread = None
        self.log_monitor_running = False
        self.log_data_lock = threading.Lock()
        self.instance_to_template = {}  # InstanceId -> TemplateId 映射
        self.template_to_name_zh = {}  # TemplateId -> 中文名称 映射
        self.uuid_to_item_data = {}  # UUID (TemplateId) -> 物品数据 映射
        self.hand_items = set()  # 手牌物品InstanceId集合
        self.stash_items = set()  # 仓库物品InstanceId集合
        self.equipped_items = set()  # 当前装备的物品InstanceId集合（手牌+仓库）

    def set_uuid_to_item_data(self, uuid_to_item_data):
        """设置UUID到物品数据的映射（由DataLoader提供）"""
        self.uuid_to_item_data = uuid_to_item_data
        logging.info(f"[LogMonitor] 已设置UUID映射数据: {len(uuid_to_item_data)} 个物品")

    def get_game_log_path(self):
        """获取游戏日志路径"""
        try:
            userprofile = os.environ.get('USERPROFILE')
            if not userprofile:
                return None
            
            log_path = os.path.join(
                userprofile,
                'AppData', 'LocalLow', 'Tempo Storm', 'The Bazaar', 'Player.log'
            )
            return log_path
        except Exception as e:
            logging.error(f"获取游戏日志路径失败: {e}")
            return None

    def start_log_monitor(self):
        """启动游戏日志监控线程"""
        log_path = self.get_game_log_path()
        if not log_path:
            logging.warning("无法获取游戏日志路径，日志监控功能将不可用")
            return
        
        if not os.path.exists(log_path):
            logging.info(f"游戏日志文件不存在: {log_path}，等待文件创建...")
        
        self.log_monitor_running = True
        self.log_monitor_thread = threading.Thread(
            target=self._monitor_log,
            args=(log_path,),
            daemon=True
        )
        self.log_monitor_thread.start()
        logging.info("游戏日志监控线程已启动")

    def stop_log_monitor(self):
        """停止游戏日志监控线程"""
        self.log_monitor_running = False
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            self.log_monitor_thread.join(timeout=2)
            logging.info("游戏日志监控线程已停止")

    def _monitor_log(self, log_path):
        """监控游戏日志文件，解析物品信息"""
        # 等待日志文件存在
        max_wait_time = 60  # 最多等待60秒
        wait_start = time.time()
        while not os.path.exists(log_path) and (time.time() - wait_start) < max_wait_time:
            if not self.log_monitor_running:
                return
            time.sleep(2)
        
        if not os.path.exists(log_path):
            logging.warning(f"游戏日志文件不存在: {log_path}，日志监控功能将不可用")
            return
        
        logging.info(f"开始监控游戏日志: {log_path}")
        
        # 编译正则表达式
        # 注意：TemplateId后面没有空格，直接跟UUID
        re_purchase = re.compile(
            r"Card Purchased: InstanceId:\s*([^\s]+)\s*-\s*TemplateId([^\s-]+(?:-[^\s-]+){4})\s*-\s*Target:([^\s]+)"
        )
        re_id = re.compile(r"ID:\s*\[([^\]]+)\]")
        re_owner = re.compile(r"- Owner:\s*\[([^\]]+)\]")
        re_section = re.compile(r"- Section:\s*\[([^\]]+)\]")
        
        # 读取位置
        last_file_size = 0
        file_position = 0
        
        try:
            # 首次读取：建立完整的映射关系
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 建立InstanceId到TemplateId的映射
                    for match in re_purchase.finditer(content):
                        instance_id = match.group(1)
                        template_id = match.group(2)
                        with self.log_data_lock:
                            self.instance_to_template[instance_id] = template_id
                            # 通过TemplateId查找物品中文名称
                            self._update_template_name_mapping(template_id)
                    
                    file_position = len(content)
                    last_file_size = os.path.getsize(log_path)
                    
                    # 统计信息
                    unique_templates = len(self.template_to_name_zh)
                    total_instances = len(self.instance_to_template)
                    template_names = list(self.template_to_name_zh.values())[:10]
                    logging.info(
                        f"初始扫描完成: {unique_templates} 种物品 "
                        f"({', '.join(template_names)}{'...' if unique_templates > 10 else ''}), "
                        f"{total_instances} 个实例"
                    )
        except Exception as e:
            logging.error(f"初始扫描日志失败: {e}")
        
        # 持续监控
        while self.log_monitor_running:
            try:
                if not os.path.exists(log_path):
                    time.sleep(1)
                    continue
                
                current_file_size = os.path.getsize(log_path)
                
                # 如果文件被重置（大小变小），重新开始
                if current_file_size < last_file_size:
                    logging.info("游戏日志文件被重置，重新开始监控")
                    file_position = 0
                    with self.log_data_lock:
                        self.instance_to_template.clear()
                        self.template_to_name_zh.clear()
                        self.hand_items.clear()
                        self.stash_items.clear()
                        self.equipped_items.clear()
                
                last_file_size = current_file_size
                
                # 读取新内容
                if current_file_size > file_position:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(file_position)
                        new_lines = f.readlines()
                        file_position = f.tell()
                        
                        # 解析新行
                        current_instance_id = None
                        current_owner = None
                        current_section = None
                        
                        for line in new_lines:
                            line = line.strip()
                            
                            # 解析购买记录
                            purchase_match = re_purchase.search(line)
                            if purchase_match:
                                instance_id = purchase_match.group(1)
                                template_id = purchase_match.group(2)
                                target = purchase_match.group(3)
                                
                                with self.log_data_lock:
                                    self.instance_to_template[instance_id] = template_id
                                    self._update_template_name_mapping(template_id)
                                    
                                    # 根据Target判断位置
                                    if "Storage" in target:
                                        self.equipped_items.add(instance_id)
                            
                            # 解析物品信息
                            id_match = re_id.search(line)
                            if id_match:
                                current_instance_id = id_match.group(1)
                                if current_instance_id.startswith('itm_'):
                                    current_owner = None
                                    current_section = None
                            
                            owner_match = re_owner.search(line)
                            if owner_match:
                                current_owner = owner_match.group(1)
                            
                            section_match = re_section.search(line)
                            if section_match:
                                current_section = section_match.group(1)
                                
                                # 如果是玩家的物品，区分手牌和仓库
                                if (current_owner == "Player" and 
                                    current_instance_id and 
                                    current_instance_id.startswith('itm_')):
                                    with self.log_data_lock:
                                        if current_section == "Hand":
                                            self.hand_items.add(current_instance_id)
                                            self.equipped_items.add(current_instance_id)
                                        elif current_section in ("Stash", "Storage"):
                                            self.stash_items.add(current_instance_id)
                                            self.equipped_items.add(current_instance_id)
                
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logging.error(f"监控日志文件时出错: {e}")
                time.sleep(5)

    def _update_template_name_mapping(self, template_id):
        """更新TemplateId到中文名称的映射"""
        if template_id in self.template_to_name_zh:
            return  # 已经存在，不需要更新
        
        # 优先从uuid_to_item_data（items_db.json）中查找
        if template_id in self.uuid_to_item_data:
            item_data = self.uuid_to_item_data[template_id]
            name_zh = item_data.get('name_zh', '')
            if name_zh:
                self.template_to_name_zh[template_id] = name_zh
                logging.debug(
                    f"[日志映射] ✅ TemplateId: {template_id} -> "
                    f"中文名称: {name_zh} (从items_db.json)"
                )
                return
        
        # 如果没有找到，记录警告
        logging.debug(f"[日志映射] ⚠ TemplateId: {template_id} 未找到对应的中文名称")

    def get_current_items(self):
        """获取当前玩家的所有物品（手牌+仓库）的中文名称列表"""
        item_names = []
        with self.log_data_lock:
            # 遍历所有装备的物品
            for instance_id in self.equipped_items:
                template_id = self.instance_to_template.get(instance_id)
                if template_id:
                    name_zh = self.template_to_name_zh.get(template_id)
                    if name_zh and name_zh not in item_names:
                        item_names.append(name_zh)
        return item_names

    def get_hand_item_names(self):
        """获取当前手牌物品的中文名称列表"""
        item_names = []
        with self.log_data_lock:
            for instance_id in self.hand_items:
                template_id = self.instance_to_template.get(instance_id)
                if template_id:
                    name_zh = self.template_to_name_zh.get(template_id)
                    if name_zh and name_zh not in item_names:
                        item_names.append(name_zh)
        return item_names

    def get_stash_item_names(self):
        """获取当前仓库物品的中文名称列表"""
        item_names = []
        with self.log_data_lock:
            for instance_id in self.stash_items:
                template_id = self.instance_to_template.get(instance_id)
                if template_id:
                    name_zh = self.template_to_name_zh.get(template_id)
                    if name_zh and name_zh not in item_names:
                        item_names.append(name_zh)
        return item_names

    def get_item_count(self):
        """获取当前物品统计"""
        with self.log_data_lock:
            return {
                'hand': len(self.hand_items),
                'stash': len(self.stash_items),
                'total': len(self.equipped_items),
                'mapped': len(self.template_to_name_zh)
            }
