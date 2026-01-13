import pyautogui
import time
import keyboard
import logging
import json
import os
from typing import Dict, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_positions(positions: Dict[str, Tuple[int, int]]):
    """保存坐标到文件"""
    # 构造保存路径
    config_dir = os.path.join("data", "json")
    os.makedirs(config_dir, exist_ok=True)  # 确保目录存在
    
    filename = os.path.join(config_dir, "position.json")
    
    # 组织数据结构
    data = {
        "timestamp": datetime.now().isoformat(),
        "monster": {
            "icon": {
                "top_left": {"x": positions.get('monster_icon_tl', (0, 0))[0], "y": positions.get('monster_icon_tl', (0, 0))[1]},
                "top_right": {"x": positions.get('monster_icon_tr', (0, 0))[0], "y": positions.get('monster_icon_tr', (0, 0))[1]},
                "bottom_left": {"x": positions.get('monster_icon_bl', (0, 0))[0], "y": positions.get('monster_icon_bl', (0, 0))[1]},
                "bottom_right": {"x": positions.get('monster_icon_br', (0, 0))[0], "y": positions.get('monster_icon_br', (0, 0))[1]}
            },
            "name": {
                "top_left": {"x": positions.get('monster_name_tl', (0, 0))[0], "y": positions.get('monster_name_tl', (0, 0))[1]},
                "top_right": {"x": positions.get('monster_name_tr', (0, 0))[0], "y": positions.get('monster_name_tr', (0, 0))[1]},
                "bottom_left": {"x": positions.get('monster_name_bl', (0, 0))[0], "y": positions.get('monster_name_bl', (0, 0))[1]},
                "bottom_right": {"x": positions.get('monster_name_br', (0, 0))[0], "y": positions.get('monster_name_br', (0, 0))[1]}
            }
        },
        "item": {
            "icon": {
                "top_left": {"x": positions.get('item_icon_tl', (0, 0))[0], "y": positions.get('item_icon_tl', (0, 0))[1]},
                "top_right": {"x": positions.get('item_icon_tr', (0, 0))[0], "y": positions.get('item_icon_tr', (0, 0))[1]},
                "bottom_left": {"x": positions.get('item_icon_bl', (0, 0))[0], "y": positions.get('item_icon_bl', (0, 0))[1]},
                "bottom_right": {"x": positions.get('item_icon_br', (0, 0))[0], "y": positions.get('item_icon_br', (0, 0))[1]}
            },
            "name": {
                "top_left": {"x": positions.get('item_name_tl', (0, 0))[0], "y": positions.get('item_name_tl', (0, 0))[1]},
                "top_right": {"x": positions.get('item_name_tr', (0, 0))[0], "y": positions.get('item_name_tr', (0, 0))[1]},
                "bottom_left": {"x": positions.get('item_name_bl', (0, 0))[0], "y": positions.get('item_name_bl', (0, 0))[1]},
                "bottom_right": {"x": positions.get('item_name_br', (0, 0))[0], "y": positions.get('item_name_br', (0, 0))[1]}
            }
        }
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n坐标已保存到文件: {filename}")

def get_mouse_position():
    """
    获取鼠标位置的工具
    用于记录怪物和道具的图标、名称范围坐标
    
    怪物图标范围（4个角）：
    1 - 怪物图标左上角
    2 - 怪物图标右上角
    3 - 怪物图标左下角
    4 - 怪物图标右下角
    
    怪物名称范围（4个角）：
    5 - 怪物名称左上角
    6 - 怪物名称右上角
    7 - 怪物名称左下角
    8 - 怪物名称右下角
    
    道具图标范围（4个角）：
    q - 道具图标左上角
    w - 道具图标右上角
    e - 道具图标左下角
    r - 道具图标右下角
    
    道具名称范围（4个角）：
    t - 道具名称左上角
    y - 道具名称右上角
    u - 道具名称左下角
    i - 道具名称右下角
    
    s - 保存并退出
    """

    positions: Dict[str, Tuple[int, int]] = {}
    position_names = {
        # 怪物图标范围
        '1': 'monster_icon_tl',  # top left
        '2': 'monster_icon_tr',  # top right
        '3': 'monster_icon_bl',  # bottom left
        '4': 'monster_icon_br',  # bottom right
        # 怪物名称范围
        '5': 'monster_name_tl',
        '6': 'monster_name_tr',
        '7': 'monster_name_bl',
        '8': 'monster_name_br',
        # 道具图标范围
        'q': 'item_icon_tl',
        'w': 'item_icon_tr',
        'e': 'item_icon_bl',
        'r': 'item_icon_br',
        # 道具名称范围
        't': 'item_name_tl',
        'y': 'item_name_tr',
        'u': 'item_name_bl',
        'i': 'item_name_br',
    }
    
    logger.info("=" * 60)
    logger.info("坐标获取工具已启动")
    logger.info("=" * 60)
    logger.info("\n【怪物图标范围】")
    logger.info("1 - 怪物图标左上角")
    logger.info("2 - 怪物图标右上角")
    logger.info("3 - 怪物图标左下角")
    logger.info("4 - 怪物图标右下角")
    logger.info("\n【怪物名称范围】")
    logger.info("5 - 怪物名称左上角")
    logger.info("6 - 怪物名称右上角")
    logger.info("7 - 怪物名称左下角")
    logger.info("8 - 怪物名称右下角")
    logger.info("\n【道具图标范围】")
    logger.info("q - 道具图标左上角")
    logger.info("w - 道具图标右上角")
    logger.info("e - 道具图标左下角")
    logger.info("r - 道具图标右下角")
    logger.info("\n【道具名称范围】")
    logger.info("t - 道具名称左上角")
    logger.info("y - 道具名称右上角")
    logger.info("u - 道具名称左下角")
    logger.info("i - 道具名称右下角")
    logger.info("\n按 's' 保存并退出程序")
    logger.info("=" * 60)
    
    try:
        while True:
            for key in position_names.keys():
                if keyboard.is_pressed(key):
                    x, y = pyautogui.position()
                    name = position_names[key]
                    positions[name] = (x, y)
                    logger.info(f"✓ 记录位置 {name}: x={x}, y={y}")
                    # 等待按键释放
                    time.sleep(0.5)
            
            if keyboard.is_pressed('s'):
                break
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        pass
    
    if positions:
        logger.info("\n" + "=" * 60)
        logger.info("记录的所有位置：")
        logger.info("=" * 60)
        for name, (x, y) in sorted(positions.items()):
            logger.info(f"{name}: x={x}, y={y}")
        
        # 保存坐标到文件
        save_positions(positions)
        logger.info("\n坐标已保存完成！")
    else:
        logger.info("\n未记录任何坐标，退出程序。")

if __name__ == "__main__":
    get_mouse_position() 