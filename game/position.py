"""
位置配置模块
"""
import os
import sys
import json
import logging
from logger import is_packaged_environment


class PositionConfig:
    """位置配置管理类"""

    def __init__(self):
        self.position_config = None
        self.monster_icon_name_offset = None
        self.item_icon_name_offset = None

    def load_position_config(self):
        """加载位置配置文件"""
        try:
            # 获取数据文件路径（支持开发环境和安装环境）
            if is_packaged_environment():
                # 安装环境：数据文件在安装目录下
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境：数据文件在项目根目录下（main_script 的父目录）
                current_file = os.path.abspath(__file__)  # game/position.py
                game_dir = os.path.dirname(current_file)  # game 目录
                project_root = os.path.dirname(game_dir)  # 项目根目录
                base_dir = project_root

            position_file = os.path.join(
                base_dir, 'data', 'Json', 'position.json')
            if os.path.exists(position_file):
                with open(position_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logging.info("成功加载位置配置文件")
                    self.position_config = config
                    # 计算相对位置关系（怪物和物品）
                    self.monster_icon_name_offset = self.calculate_relative_offset(
                        'monster')
                    self.item_icon_name_offset = self.calculate_relative_offset(
                        'item')
                    return config
            else:
                logging.warning(f"位置配置文件不存在: {position_file}")
                self.position_config = None
                return None
        except Exception as e:
            logging.error(f"加载位置配置文件失败: {e}")
            self.position_config = None
            return None

    def calculate_relative_offset(self, entity_type='monster'):
        """
        计算图标和名称的相对位置关系（与 position.json 的结构匹配）

        Args:
            entity_type: 'monster' 或 'item'

        Returns:
            dict: 包含相对偏移量的字典，格式：
                  {
                      'x_offset_tl', 'y_offset_tl',
                      'x_offset_tr', 'y_offset_tr',
                      'x_offset_bl', 'y_offset_bl',
                      'x_offset_br', 'y_offset_br',
                  }
        """
        if not self.position_config:
            return None

        try:
            config = self.position_config
            if not isinstance(config, dict):
                logging.warning("position_config 不是字典格式")
                return None

            icon_data = config.get(entity_type, {}).get('icon', {})
            name_data = config.get(entity_type, {}).get('name', {})

            if not icon_data or not name_data:
                logging.warning(f"位置配置中缺少 {entity_type} 的数据")
                return None

            # 计算相对偏移量（使用四个角的坐标）
            offset = {
                'x_offset_tl': name_data['top_left']['x'] - icon_data['top_left']['x'],
                'y_offset_tl': name_data['top_left']['y'] - icon_data['top_left']['y'],
                'x_offset_tr': name_data['top_right']['x'] - icon_data['top_right']['x'],
                'y_offset_tr': name_data['top_right']['y'] - icon_data['top_right']['y'],
                'x_offset_bl': name_data['bottom_left']['x'] - icon_data['bottom_left']['x'],
                'y_offset_bl': name_data['bottom_left']['y'] - icon_data['bottom_left']['y'],
                'x_offset_br': name_data['bottom_right']['x'] - icon_data['bottom_right']['x'],
                'y_offset_br': name_data['bottom_right']['y'] - icon_data['bottom_right']['y'],
            }

            logging.debug(f"{entity_type} 相对偏移量: {offset}")
            return offset
        except Exception as e:
            logging.error(f"计算 {entity_type} 相对偏移量失败: {e}")
            return None
