import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

class MonsterCrawler:
    def __init__(self, base_url: str = "https://bazaar.lol"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # 设置日志
        logging.basicConfig(
            filename='monster_crawler.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def fetch_all_monsters(self) -> List[Dict]:
        """获取所有怪物的基本信息列表"""
        try:
            url = f"{self.base_url}/api/monsters"
            response = self.session.get(url)
            response.raise_for_status()
            monsters = response.json()
            self.logger.info(f"成功获取{len(monsters)}个怪物的基本信息")
            return monsters
        except Exception as e:
            self.logger.error(f"获取怪物列表失败: {str(e)}")
            raise

    def fetch_monster_details(self, monster_id: int) -> Dict:
        """获取单个怪物的详细信息"""
        try:
            url = f"{self.base_url}/api/monsters/{monster_id}"
            response = self.session.get(url)
            response.raise_for_status()
            details = response.json()
            self.logger.info(f"成功获取怪物ID {monster_id} 的详细信息")
            return details
        except Exception as e:
            self.logger.error(f"获取怪物ID {monster_id} 的详细信息失败: {str(e)}")
            raise

    def get_card_description(self, html_content: str) -> str:
        """从HTML内容中提取卡牌描述"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            description = soup.find('div', class_='card-description')
            return description.text.strip() if description else ""
        except Exception as e:
            self.logger.error(f"解析卡牌描述失败: {str(e)}")
            return ""

    def crawl_all_monsters(self, output_dir: str = "data/monsters") -> None:
        """爬取所有怪物的完整信息并保存"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 获取所有怪物列表
            monsters = self.fetch_all_monsters()
            
            # 获取每个怪物的详细信息
            detailed_monsters = []
            for monster in monsters:
                monster_id = monster['id']
                details = self.fetch_monster_details(monster_id)
                
                # 合并基本信息和详细信息
                monster_data = {**monster, **details}
                detailed_monsters.append(monster_data)

            # 保存完整数据
            output_file = os.path.join(output_dir, "monsters_full.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_monsters, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"成功保存所有怪物数据到 {output_file}")
            
        except Exception as e:
            self.logger.error(f"爬取所有怪物信息失败: {str(e)}")
            raise

if __name__ == "__main__":
    crawler = MonsterCrawler()
    crawler.crawl_all_monsters() 