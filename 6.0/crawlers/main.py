"""
主程序入口
协调怪物和事件爬虫的执行
"""

import sys
import argparse
from pathlib import Path
from monster_crawler import MonsterCrawler
from event_crawler import EventCrawler
from utils import Logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Bazaar数据库爬虫')
    parser.add_argument(
        '--type',
        choices=['monster', 'event', 'all'],
        default='all',
        help='爬取类型: monster(怪物), event(事件), all(全部)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='使用无头浏览器模式'
    )
    
    args = parser.parse_args()
    
    logger = Logger("main")
    logger.info("=" * 80)
    logger.info("Bazaar数据库爬虫启动")
    logger.info("=" * 80)
    logger.info(f"爬取类型: {args.type}")
    logger.info(f"无头模式: {args.headless}")
    logger.info("")
    
    success = True
    
    try:
        if args.type in ['monster', 'all']:
            logger.info("\n" + "=" * 80)
            logger.info("开始爬取怪物信息")
            logger.info("=" * 80)
            
            monster_crawler = MonsterCrawler(headless=args.headless)
            try:
                monsters = monster_crawler.crawl()
                logger.info(f"✓ 怪物信息爬取成功！共 {len(monsters)} 个怪物")
            except Exception as e:
                logger.error(f"✗ 怪物信息爬取失败: {str(e)}")
                success = False
        
        if args.type in ['event', 'all']:
            logger.info("\n" + "=" * 80)
            logger.info("开始爬取事件信息")
            logger.info("=" * 80)
            
            event_crawler = EventCrawler(headless=args.headless)
            try:
                events = event_crawler.crawl()
                logger.info(f"✓ 事件信息爬取成功！共 {len(events)} 个事件")
            except Exception as e:
                logger.error(f"✗ 事件信息爬取失败: {str(e)}")
                success = False
        
        logger.info("\n" + "=" * 80)
        if success:
            logger.info("所有爬取任务完成！")
            logger.info("")
            logger.info("输出文件:")
            logger.info("  - 6.0/data/monsters.json  (怪物数据)")
            logger.info("  - 6.0/data/events.json    (事件数据)")
            logger.info("  - 6.0/icons/skills/       (技能图标)")
            logger.info("  - 6.0/icons/items/        (物品图标)")
            logger.info("  - 6.0/logs/               (日志文件)")
        else:
            logger.error("部分任务失败，请查看日志获取详情")
        logger.info("=" * 80)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"\n发生未预期的错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())




