"""
Selenium事件爬虫 V1 - 完整版（处理所有事件）
功能：
1. 从meta描述提取事件选择名称
2. 从HTML中提取图标URL
3. 访问详情页获取描述
4. 下载图标并保存到本地（命名格式：事件名_选择名.webp）
5. 增量保存：每处理完一个事件立即保存到JSON文件
"""

import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置
OUTPUT_DIR = Path('event_details_v1')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR = OUTPUT_DIR / 'icons'
ICONS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = OUTPUT_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = 'unique_events.json'

# 全局错误日志
ERROR_LOG = {
    'failed_events': [],              # 完全失败的事件
    'missing_detail_urls': [],        # 未找到详情页的事件
    'missing_choices': [],            # 未找到选择的事件
    'failed_choice_downloads': [],    # 选择图标下载失败
    'failed_descriptions': [],        # 描述获取失败
    'exceptions': []                  # 其他异常
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


def download_icon(icon_url, event_name, choice_name):
    """下载图标并返回本地路径"""
    if not icon_url:
        ERROR_LOG['failed_choice_downloads'].append({
            'event': event_name,
            'choice': choice_name,
            'reason': 'No icon URL provided'
        })
        return ""
    
    try:
        # 清理文件名中的非法字符
        safe_event_name = re.sub(r'[<>:"/\\|?*]', '_', event_name)
        safe_choice_name = re.sub(r'[<>:"/\\|?*]', '_', choice_name)
        
        # 构建文件名: 事件名_选择名.webp
        filename = f"{safe_event_name}_{safe_choice_name}.webp"
        filepath = ICONS_DIR / filename
        
        # 如果文件已存在，跳过下载
        if filepath.exists():
            print(f"        图标已存在: {filename}")
            return f"icons/{filename}"
        
        # 下载图标
        response = requests.get(icon_url, timeout=10)
        response.raise_for_status()
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"        ✓ 下载图标: {filename}")
        return f"icons/{filename}"
    
    except Exception as e:
        print(f"        ✗ 下载图标失败: {e}")
        ERROR_LOG['failed_choice_downloads'].append({
            'event': event_name,
            'choice': choice_name,
            'url': icon_url,
            'reason': str(e)
        })
        return ""


def get_event_detail_url(driver, event_name):
    """通过搜索获取事件的详情页URL"""
    search_url = f"https://bazaardb.gg/search?q={event_name.replace(' ', '+')}&c=events"
    driver.get(search_url)
    
    try:
        time.sleep(3)
        
        # 查找第一个卡片链接
        card_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="/card/"]')
        detail_url = card_link.get_attribute('href')
        return detail_url
    except NoSuchElementException:
        print(f"    ✗ 未找到事件: {event_name}")
        return None
    except Exception as e:
        print(f"    ✗ 搜索出错: {e}")
        return None


def extract_choices_from_html(html_content):
    """从HTML中提取事件选择名称（从h3标题提取）"""
    choices = []
    
    # 查找所有h3标题中的选择名称
    # 格式: <h3...><span>Choice Name</span></h3>
    h3_matches = re.findall(r'<h3[^>]*>.*?<span>([^<]+)</span>', html_content, re.DOTALL)
    
    if h3_matches:
        # 过滤掉非选择的标题（如"Hide filters"等）
        for title in h3_matches:
            title = title.strip()
            # 排除一些明显不是选择的标题
            if title and title not in ['Hide filters', 'Close filters', 'Reset filters']:
                choices.append(title)
        
        print(f"    找到 {len(choices)} 个选择:")
        for i, choice in enumerate(choices, 1):
            print(f"      {i}. {choice}")
    
    return choices


def extract_icons_from_html(html_content):
    """从HTML中提取图标URL映射（从img标签提取）"""
    icons = {}
    
    # 事件选择图标格式：item/[hash]@256.webp（事件选择通常用item图标）
    icon_matches = re.findall(r'https://s\.bazaardb\.gg/v0/[^/]+/item/([a-f0-9]+)@256\.webp[^"]*', html_content)
    if icon_matches:
        # 去重
        unique_hashes = list(dict.fromkeys(icon_matches))
        for icon_hash in unique_hashes:
            icon_url = f"https://s.bazaardb.gg/v0/z5.0.0/item/{icon_hash}@256.webp?v=0"
            icons[icon_hash] = icon_url
            print(f"      找到选择图标: {icon_url[:70]}...")
    
    print(f"    ✓ 找到 {len(icons)} 个选择图标")
    
    return icons


def get_choice_description(driver, choice_url):
    """访问选择详情页获取描述"""
    try:
        driver.get(choice_url)
        time.sleep(3)
        
        html = driver.page_source
        
        # 从页面中查找所有 <div class="_bM"> 中的描述文本
        desc_matches = re.findall(r'<div class="_bM">(.*?)</div>', html, re.DOTALL)
        
        if desc_matches:
            valid_descriptions = []
            
            for description_html in desc_matches:
                # 清理HTML标签和注释
                description = re.sub(r'<[^>]+>', '', description_html)
                description = re.sub(r'<!--\s*-->', '', description)
                # 清理HTML实体
                description = description.replace('&nbsp;', ' ')
                description = description.replace('&amp;', '&')
                description = description.replace('&lt;', '<')
                description = description.replace('&gt;', '>')
                description = description.replace('&#x27;', "'")
                description = description.strip()
                
                # 过滤掉无效描述
                if (len(description) > 10 and 
                    'Offered by' not in description and 
                    'Dropped by' not in description and
                    'Found in' not in description):
                    valid_descriptions.append(description)
            
            # 合并所有有效描述
            if valid_descriptions:
                return '. '.join(valid_descriptions)
        
        return ""
    except Exception as e:
        print(f"      ✗ 获取描述失败: {e}")
        return ""


def extract_event_details(driver, event_name, detail_url):
    """从详情页提取事件信息"""
    print(f"\n  [2/4] 访问事件详情页...")
    driver.get(detail_url)
    time.sleep(5)
    
    html_content = driver.page_source
    
    # 步骤1: 从HTML的h3标题提取选择名称
    print(f"\n  [3/4] 从HTML提取选择...")
    choice_names = extract_choices_from_html(html_content)
    
    # 记录没有选择的事件
    if not choice_names:
        ERROR_LOG['missing_choices'].append({
            'event': event_name,
            'url': detail_url
        })
        print(f"    ⚠️  未找到选择")
    
    # 步骤2: 从HTML提取图标URL
    print(f"\n  [4/4] 从HTML提取图标...")
    icons = extract_icons_from_html(html_content)
    
    event_data = {
        "name": event_name,
        "url": detail_url,
        "choices": []
    }
    
    # 处理选择
    print(f"\n  处理选择详情...")
    icon_urls = list(icons.values())  # 按顺序获取图标URL
    
    for idx, choice_name in enumerate(choice_names):
        print(f"    [{choice_name}]")
        
        # 构建选择URL
        choice_url_match = re.search(rf'href="(/card/[^"]+/{re.escape(choice_name.replace(" ", "-"))})"', html_content)
        if choice_url_match:
            choice_url = f"https://bazaardb.gg{choice_url_match.group(1)}"
            
            # 按顺序匹配图标URL
            choice_icon_url = icon_urls[idx] if idx < len(icon_urls) else ''
            
            # 下载图标
            choice_icon_path = download_icon(choice_icon_url, event_name, choice_name)
            
            # 获取描述
            description = get_choice_description(driver, choice_url)
            
            event_data["choices"].append({
                "name": choice_name,
                "url": choice_url,
                "icon": choice_icon_path,
                "icon_url": choice_icon_url,
                "description": description
            })
            print(f"      ✓ 描述: {description[:50]}...")
        else:
            print(f"      ✗ 未找到URL")
    
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


def main():
    """主函数"""
    print("=" * 80)
    print("Selenium事件爬虫 V1 - 处理所有事件（增量保存）")
    print("=" * 80)

    event_names = load_event_names(EVENTS_FILE)
    if not event_names:
        print("没有事件名称可供处理。")
        return

    output_file = OUTPUT_DIR / 'events_v1.json'
    
    # 加载已处理的事件
    all_events = load_existing_events(output_file)
    processed_names = {e['name'] for e in all_events}
    
    # 过滤出未处理的事件
    remaining_events = [name for name in event_names if name not in processed_names]
    
    print(f"\n总事件数: {len(event_names)}")
    print(f"已处理: {len(processed_names)}")
    print(f"待处理: {len(remaining_events)}")
    
    if not remaining_events:
        print("\n✓ 所有事件已处理完成！")
        return
    
    print(f"\n将继续处理剩余的 {len(remaining_events)} 个事件...")
    
    driver = setup_driver()
    total_choices = 0

    try:
        for i, event_name in enumerate(remaining_events, 1):
            print(f"\n{'=' * 80}")
            print(f"[{i}/{len(remaining_events)}] 处理: {event_name}")
            print(f"总进度: [{len(all_events) + i}/{len(event_names)}]")
            print('=' * 80)

            try:
                # 步骤1: 获取详情页URL
                print(f"\n  [1/4] 搜索事件...")
                detail_url = get_event_detail_url(driver, event_name)
                
                if detail_url:
                    print(f"    ✓ 找到: {detail_url}")
                    
                    # 步骤2-4: 提取详细信息
                    event_details = extract_event_details(driver, event_name, detail_url)
                    all_events.append(event_details)
                    
                    # 立即保存到JSON文件
                    save_events_to_json(all_events, output_file)
                    
                    total_choices += len(event_details['choices'])
                    
                    print(f"\n  摘要:")
                    print(f"    选择数: {len(event_details['choices'])}")
                    print(f"    ✓ 已保存到: {output_file}")
                else:
                    print(f"    ✗ 未找到详情页")
                    ERROR_LOG['missing_detail_urls'].append({
                        'event': event_name,
                        'search_url': f"https://bazaardb.gg/search?q={event_name.replace(' ', '+')}&c=events"
                    })
                    
            except Exception as e:
                print(f"\n  ✗ 处理出错: {e}")
                print(f"  继续处理下一个事件...")
                ERROR_LOG['failed_events'].append({
                    'event': event_name,
                    'error': str(e)
                })
                ERROR_LOG['exceptions'].append({
                    'event': event_name,
                    'error': str(e),
                    'type': type(e).__name__
                })
                continue

    finally:
        # 最终保存
        save_events_to_json(all_events, output_file)
        
        # 保存错误日志
        log_file = save_error_log()
        
        print(f"\n{'=' * 80}")
        print("处理完成！")
        print('=' * 80)
        print(f"\n✓ 成功处理 {len(all_events)} 个事件")
        print(f"✓ 结果已保存到: {output_file}")
        print(f"✓ 错误日志已保存到: {log_file}")
        
        print(f"\n本次运行统计:")
        print(f"  新增选择数: {total_choices}")
        
        # 计算总统计
        all_choices = sum(len(e['choices']) for e in all_events)
        print(f"\n总统计:")
        print(f"  总事件数: {len(all_events)}")
        print(f"  总选择数: {all_choices}")
        
        # 显示错误统计
        print(f"\n错误统计:")
        print(f"  未找到详情页: {len(ERROR_LOG['missing_detail_urls'])}")
        print(f"  无选择的事件: {len(ERROR_LOG['missing_choices'])}")
        print(f"  选择图标下载失败: {len(ERROR_LOG['failed_choice_downloads'])}")
        print(f"  描述获取失败: {len(ERROR_LOG['failed_descriptions'])}")
        print(f"  完全失败的事件: {len(ERROR_LOG['failed_events'])}")
        print(f"  其他异常: {len(ERROR_LOG['exceptions'])}")

        driver.quit()
        print("\n关闭浏览器...")


if __name__ == "__main__":
    main()
