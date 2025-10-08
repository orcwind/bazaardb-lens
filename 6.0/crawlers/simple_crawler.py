"""
简单爬虫 - 只抓取HTML文件
"""

import requests


def main():
    """只抓取HTML文件"""
    print("=" * 80)
    print("开始抓取数据...")
    print("=" * 80)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 抓取怪物HTML
    print("\n[1/2] 抓取怪物数据")
    monsters_url = "https://bazaardb.gg/search?c=monsters"
    print(f"  访问: {monsters_url}")
    
    try:
        response = session.get(monsters_url, timeout=30)
        response.raise_for_status()
        
        output_file = 'debug_monsters.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        file_size = len(response.text)
        print(f"  ✓ 文件大小: {file_size:,} 字符")
        print(f"  ✓ 已保存到: {output_file}")
        
    except Exception as e:
        print(f"  ✗ 抓取失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 抓取事件HTML
    print("\n[2/2] 抓取事件数据")
    events_url = "https://bazaardb.gg/search?c=events"
    print(f"  访问: {events_url}")
    
    try:
        response = session.get(events_url, timeout=30)
        response.raise_for_status()
        
        output_file = 'debug_events.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        file_size = len(response.text)
        print(f"  ✓ 文件大小: {file_size:,} 字符")
        print(f"  ✓ 已保存到: {output_file}")
        
    except Exception as e:
        print(f"  ✗ 抓取失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("抓取完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()