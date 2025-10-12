"""
Selenium事件爬虫 - 完整版
功能：
1. 从页面的 <script> 标签中提取 pool 数据（获取选择名称、URL、图标）
2. 从DOM中提取选择的描述
3. 下载图标并保存到本地
4. 增量保存
"""

import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# 配置
OUTPUT_DIR = Path('event_details_final')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR = OUTPUT_DIR / 'icons'
ICONS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = OUTPUT_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = 'unique_events.json'

# 全局错误日志
ERROR_LOG = {
    'failed_events': [],
    'missing_detail_urls': [],
    'missing_choices': [],
    'failed_choice_downloads': [],
    'failed_descriptions': [],
    'exceptions': []
}


def setup_driver():
    """设置Chrome驱动"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def load_event_names(file_path):
    """从文件中加载事件名称列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            names = [line.strip().strip('"') for line in f if line.strip()]
        return names
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return []


def get_icon_aspect_ratio(filepath):
    """获取图标的长宽比
    
    Args:
        filepath: 图标文件路径
    
    Returns:
        长宽比 (width/height)，如果失败则返回 1.0
    """
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            width, height = img.size
            if height == 0:
                return 1.0
            aspect_ratio = width / height
            
            # 四舍五入到最接近的标准比例 (0.5, 1.0, 1.5)
            if aspect_ratio < 0.75:
                return 0.5
            elif aspect_ratio < 1.25:
                return 1.0
            else:
                return 1.5
    except Exception as e:
        print(f"        ⚠ 获取长宽比失败: {e}")
        return 1.0


def download_icon(icon_url, event_name, choice_name):
    """下载图标并返回路径和长宽比
    
    Returns:
        (本地图标路径, 长宽比) 或 ("", 1.0) 如果下载失败
    """
    try:
        # 清理文件名
        safe_event_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_choice_name = "".join([c for c in choice_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        # 创建事件目录
        event_dir = ICONS_DIR / safe_event_name
        event_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取图标扩展名
        ext = icon_url.split('.')[-1].split('?')[0]
        if not ext or len(ext) > 4:
            ext = 'webp'
        
        # 保存路径
        icon_path = event_dir / f"{safe_choice_name}.{ext}"
        
        # 如果已存在，获取长宽比并返回
        if icon_path.exists():
            aspect_ratio = get_icon_aspect_ratio(icon_path)
            return str(icon_path.relative_to(OUTPUT_DIR)), aspect_ratio
        
        # 下载图标
        response = requests.get(icon_url, timeout=10)
        if response.status_code == 200:
            with open(icon_path, 'wb') as f:
                f.write(response.content)
            
            # 获取长宽比
            aspect_ratio = get_icon_aspect_ratio(icon_path)
            return str(icon_path.relative_to(OUTPUT_DIR)), aspect_ratio
        else:
            ERROR_LOG['failed_choice_downloads'].append({
                'event': event_name,
                'choice': choice_name,
                'url': icon_url,
                'status': response.status_code
            })
            return "", 1.0
    except Exception as e:
        ERROR_LOG['failed_choice_downloads'].append({
            'event': event_name,
            'choice': choice_name,
            'url': icon_url,
            'error': str(e)
        })
        return "", 1.0


def smart_merge_choice_data(existing_choice, new_choice):
    """智能合并事件选择数据
    
    规则：
    1. 如果新数据为空或无效，保留原有数据
    2. 如果新数据有效，使用新数据覆盖
    3. 图标路径：如果新图标下载成功，使用新路径；否则保留原有
    
    Args:
        existing_choice: 已有的选择数据
        new_choice: 新抓取的选择数据
    
    Returns:
        合并后的选择数据
    """
    merged = existing_choice.copy()
    
    # 描述：只有新描述不为空时才覆盖
    if new_choice.get('description', '').strip():
        merged['description'] = new_choice['description']
    
    # URL：只有新URL不为空时才覆盖
    if new_choice.get('url', '').strip():
        merged['url'] = new_choice['url']
    
    # 图标URL：只有新图标URL不为空时才覆盖
    if new_choice.get('icon_url', '').strip():
        merged['icon_url'] = new_choice['icon_url']
    
    # 图标路径：只有新图标下载成功时才覆盖
    if (new_choice.get('icon', '').strip() and 
        new_choice['icon'] != "icons/placeholder.webp" and
        not new_choice['icon'].startswith('icons/placeholder')):
        merged['icon'] = new_choice['icon']
    
    # 长宽比：只有新长宽比有效时才覆盖
    if new_choice.get('aspect_ratio') is not None:
        merged['aspect_ratio'] = new_choice['aspect_ratio']
    
    return merged


def extract_pool_from_html(html_content):
    """从HTML中提取pool数据（选择的基本信息）"""
    choices_data = []
    try:
        # 找到 "pool":[ 的位置
        pattern = r'\\"pool\\":\['
        match = re.search(pattern, html_content)
        
        if not match:
            return []
        
        start_pos = match.end()  # 从 [ 之后开始
        
        # 使用括号计数来找到完整的数组
        bracket_count = 1  # 已经有一个 [
        i = start_pos
        
        while i < len(html_content) and bracket_count > 0:
            if html_content[i] == '[':
                bracket_count += 1
            elif html_content[i] == ']':
                bracket_count -= 1
            i += 1
        
        if bracket_count == 0:
            # 找到了完整的数组
            pool_str = html_content[start_pos:i-1]  # i-1 因为不包括最后的 ]
            
            # 反转义并解析
            pool_json_str = '[' + pool_str + ']'
            pool_json_str = pool_json_str.replace('\\"', '"')
            
            try:
                pool_data = json.loads(pool_json_str)
                
                for choice_data in pool_data:
                    choice = {
                        'name': choice_data.get('title', ''),
                        'url': 'https://bazaardb.gg' + choice_data.get('url', ''),
                        'icon_url': choice_data.get('art', '')
                    }
                    choices_data.append(choice)
                    
            except json.JSONDecodeError as e:
                print(f"    ✗ JSON解析失败: {e}")
    
    except Exception as e:
        print(f"    ✗ 提取pool数据失败: {e}")
    
    return choices_data


def extract_descriptions_from_page(driver, choice_names):
    """
    从事件页面提取选择的描述
    
    参数:
        driver: Selenium WebDriver (当前页面应该是事件详情页)
        choice_names: 选择名称列表
    
    返回:
        dict: {choice_name: description}
    """
    # 获取页面所有文本
    page_text = driver.execute_script("return document.body.innerText;")
    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
    
    descriptions = {}
    
    # 对于每个选择名称，找到它在文本中的位置，描述在下一行或下下行
    for choice_name in choice_names:
        for i, line in enumerate(lines):
            if line == choice_name:
                # 检查下一行和下下行
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                next_next_line = lines[i + 2] if i + 2 < len(lines) else ""
                
                description = ""
                
                # 判断下一行是否是描述
                # 情况1: 下一行是短的全大写文本（英雄标签如 MAK, DOO）-> 使用下下行
                # 情况2: 下一行是纯数字（代价）-> 使用下下行
                # 情况3: 其他 -> 使用下一行
                if next_line and len(next_line) <= 5 and (next_line.isupper() or next_line.isdigit()):
                    description = next_next_line
                else:
                    description = next_line
                
                # 过滤掉不是描述的文本（比如另一个选择名称）
                if description and description not in choice_names and len(description) > 3:
                    descriptions[choice_name] = description
                    break
    
    return descriptions


def extract_event_details(driver, event_name, detail_url, existing_event=None):
    """从详情页提取事件信息
    
    Args:
        driver: Selenium WebDriver
        event_name: 事件名称
        detail_url: 详情页URL
        existing_event: 已有的事件数据（用于智能覆盖）
    
    Returns:
        事件数据字典
    """
    print(f"\n  [2/3] 访问事件详情页...")
    driver.get(detail_url)
    time.sleep(5)  # 等待页面加载
    
    html_content = driver.page_source
    
    # 步骤1：从script标签中提取pool数据（基本信息）
    print(f"\n  [3/3] 提取选择信息...")
    choices = extract_pool_from_html(html_content)
    
    if not choices:
        ERROR_LOG['missing_choices'].append({
            'event': event_name,
            'url': detail_url
        })
        print(f"    ⚠️  未找到选择")
        # 如果已有数据，返回已有数据
        if existing_event:
            print(f"    ℹ️  保留已有数据")
            return existing_event
        return None
    
    print(f"    ✓ 找到 {len(choices)} 个选择")
    
    # 步骤2：从DOM中提取描述
    choice_names = [choice['name'] for choice in choices]
    descriptions = extract_descriptions_from_page(driver, choice_names)
    
    event_data = {
        "name": event_name,
        "url": detail_url,
        "choices": []
    }
    
    # 获取已有选择数据（用于智能覆盖）
    existing_choices = {}
    if existing_event:
        existing_choices = {choice['name']: choice for choice in existing_event.get('choices', [])}
    
    # 处理每个选择
    print(f"\n  下载选择图标和提取描述...")
    for idx, choice in enumerate(choices, 1):
        choice_name = choice['name']
        print(f"    [{idx}/{len(choices)}] {choice_name}")
        
        # 下载图标并获取长宽比
        icon_path, aspect_ratio = download_icon(choice['icon_url'], event_name, choice_name)
        
        # 获取描述
        description = descriptions.get(choice_name, "")
        if description:
            print(f"        描述: {description[:80]}...")
        else:
            print(f"        ⚠️  未找到描述")
            ERROR_LOG['failed_descriptions'].append({
                'event': event_name,
                'choice': choice_name
            })
        
        # 智能覆盖逻辑
        choice_data = {
            "name": choice_name,
            "url": choice['url'],
            "icon": icon_path,
            "icon_url": choice['icon_url'],
            "description": description,
            "aspect_ratio": aspect_ratio
        }
        
        # 如果已有数据，进行智能合并
        if choice_name in existing_choices:
            existing_choice = existing_choices[choice_name]
            choice_data = smart_merge_choice_data(existing_choice, choice_data)
            print(f"      🔄 智能合并已有数据")
        
        event_data["choices"].append(choice_data)
    
    return event_data


def save_events_to_json(events_list, output_file):
    """保存事件数据到JSON文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events_list, f, ensure_ascii=False, indent=2)


def save_error_log():
    """保存错误日志到文件"""
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f'error_log_{timestamp}.json'
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(ERROR_LOG, f, ensure_ascii=False, indent=2)
    
    return log_file


def load_existing_events(output_file):
    """加载已处理的事件数据（如果存在）"""
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def get_event_detail_url(driver, event_name):
    """从搜索页面获取事件详情URL"""
    try:
        search_url = f"https://bazaardb.gg/search?c=events&q={event_name.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(3)
        
        # 使用JavaScript查找链接
        script = """
        const links = Array.from(document.querySelectorAll('a[href*="/card/"]'));
        if (links.length > 0) {
            return links[0].href;
        }
        return null;
        """
        
        url = driver.execute_script(script)
        if url:
            return url
        
        ERROR_LOG['missing_detail_urls'].append(event_name)
        return None
    except Exception as e:
        ERROR_LOG['exceptions'].append({
            'event': event_name,
            'stage': 'get_detail_url',
            'error': str(e)
        })
        return None


def main():
    """主函数"""
    print("=" * 80)
    print("事件爬虫 - 完整版")
    print("=" * 80)
    
    # 加载事件名称
    event_names = load_event_names(EVENTS_FILE)
    if not event_names:
        print("错误: 没有找到事件名称")
        return
    
    print(f"\n总共 {len(event_names)} 个事件需要处理")
    
    # 加载已处理的事件
    output_file = OUTPUT_DIR / 'events_final.json'
    existing_events = load_existing_events(output_file)
    processed_names = {event['name'] for event in existing_events}
    
    print(f"已处理 {len(processed_names)} 个事件")
    
    # 设置驱动
    driver = setup_driver()
    
    try:
        events_data = existing_events.copy()
        
        for idx, event_name in enumerate(event_names, 1):
            # 检查是否已有此事件的数据
            existing_event = None
            for existing in existing_events:
                if existing['name'] == event_name:
                    existing_event = existing
                    break
            
            if existing_event:
                print(f"\n[{idx}/{len(event_names)}] {event_name} - 更新已有数据")
            else:
                print(f"\n[{idx}/{len(event_names)}] {event_name} - 新事件")
            
            print(f"\n{'=' * 80}")
            print(f"[{idx}/{len(event_names)}] 处理事件: {event_name}")
            print('=' * 80)
            
            try:
                # 获取详情URL
                print(f"  [1/3] 搜索事件详情页...")
                detail_url = get_event_detail_url(driver, event_name)
                
                if not detail_url:
                    print(f"  ⚠️  未找到详情页URL")
                    continue
                
                print(f"  ✓ 详情页: {detail_url}")
                
                # 提取事件详情
                event_data = extract_event_details(driver, event_name, detail_url, existing_event)
                
                if event_data:
                    if existing_event:
                        # 更新已有事件数据
                        events_data = [e for e in events_data if e['name'] != event_name]
                    events_data.append(event_data)
                    processed_names.add(event_name)
                    
                    # 增量保存
                    save_events_to_json(events_data, output_file)
                    print(f"\n  ✓ 事件数据已保存")
                
            except KeyboardInterrupt:
                print("\n\n用户中断，保存当前进度...")
                save_events_to_json(events_data, output_file)
                raise
            
            except Exception as e:
                print(f"\n  ✗ 处理失败: {e}")
                ERROR_LOG['failed_events'].append({
                    'event': event_name,
                    'error': str(e)
                })
                continue
        
        # 保存最终结果
        save_events_to_json(events_data, output_file)
        
        # 保存错误日志
        log_file = save_error_log()
        
        print(f"\n{'=' * 80}")
        print("爬取完成!")
        print('=' * 80)
        print(f"✓ 成功处理 {len(events_data)} 个事件")
        print(f"✓ 数据已保存到: {output_file}")
        print(f"✓ 错误日志: {log_file}")
        
        # 打印详细的错误报告
        print(f"\n{'=' * 80}")
        print("错误统计:")
        print('=' * 80)
        print(f"  - 失败的事件: {len(ERROR_LOG['failed_events'])}")
        print(f"  - 缺少详情URL: {len(ERROR_LOG['missing_detail_urls'])}")
        print(f"  - 缺少选择: {len(ERROR_LOG['missing_choices'])}")
        print(f"  - 图标下载失败: {len(ERROR_LOG['failed_choice_downloads'])}")
        print(f"  - 描述提取失败: {len(ERROR_LOG['failed_descriptions'])}")
        print(f"  - 异常: {len(ERROR_LOG['exceptions'])}")
        
        # 打印详细列表
        if ERROR_LOG['missing_detail_urls']:
            print(f"\n缺少详情URL的事件:")
            for event in ERROR_LOG['missing_detail_urls']:
                print(f"  - {event}")
        
        if ERROR_LOG['missing_choices']:
            print(f"\n缺少选择的事件:")
            for item in ERROR_LOG['missing_choices']:
                print(f"  - {item['event']}: {item['url']}")
        
        if ERROR_LOG['failed_descriptions']:
            print(f"\n缺少描述的选择:")
            for item in ERROR_LOG['failed_descriptions']:
                print(f"  - {item['event']} -> {item['choice']}")
        
        if ERROR_LOG['failed_choice_downloads']:
            print(f"\n图标下载失败的选择:")
            for item in ERROR_LOG['failed_choice_downloads'][:10]:  # 只显示前10个
                print(f"  - {item.get('event', 'N/A')} -> {item.get('choice', 'N/A')}")
            if len(ERROR_LOG['failed_choice_downloads']) > 10:
                print(f"  ... 和其他 {len(ERROR_LOG['failed_choice_downloads']) - 10} 个")
        
        if ERROR_LOG['failed_events']:
            print(f"\n完全失败的事件:")
            for item in ERROR_LOG['failed_events']:
                print(f"  - {item['event']}: {item.get('error', 'Unknown error')}")
        
    except KeyboardInterrupt:
        print("\n\n爬取被用户中断")
        log_file = save_error_log()
        print(f"✓ 当前进度已保存到: {output_file}")
        print(f"✓ 错误日志: {log_file}")
        
        # 打印错误报告
        print(f"\n{'=' * 80}")
        print("当前错误统计:")
        print('=' * 80)
        print(f"  - 已处理: {len(events_data)} 个事件")
        print(f"  - 缺少详情URL: {len(ERROR_LOG['missing_detail_urls'])} 个")
        print(f"  - 缺少选择: {len(ERROR_LOG['missing_choices'])} 个")
        print(f"  - 描述提取失败: {len(ERROR_LOG['failed_descriptions'])} 个")
        print(f"  - 图标下载失败: {len(ERROR_LOG['failed_choice_downloads'])} 个")
        
        if ERROR_LOG['missing_detail_urls']:
            print(f"\n缺少详情URL的事件:")
            for event in ERROR_LOG['missing_detail_urls']:
                print(f"  - {event}")
    
    finally:
        driver.quit()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    main()

