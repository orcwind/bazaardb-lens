"""从HTML文件中提取事件选择和描述"""
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).parent.parent.parent
HTML_DIR = PROJECT_ROOT / 'data' / 'html' / 'event'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'Json'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_choices_from_html(html_file):
    """从HTML文件中提取选择和描述
    
    Args:
        html_file: HTML文件路径
    
    Returns:
        dict: 包含事件名称、URL和选择列表的字典
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 获取事件名称
    h1 = soup.find('h1')
    if not h1:
        return None
    
    event_name = h1.text.strip()
    
    # 获取事件URL（从canonical link或og:url）
    event_url = None
    canonical = soup.find('link', {'rel': 'canonical'})
    if canonical:
        event_url = canonical.get('href', '')
    
    if not event_url:
        og_url = soup.find('meta', {'property': 'og:url'})
        if og_url:
            event_url = og_url.get('content', '')
    
    # 从pool数据中提取选择基本信息（名称、URL、图标）
    choices_basic = []
    pool_pattern = r'\\"pool\\":\['
    pool_match = re.search(pool_pattern, html_content)
    
    if pool_match:
        start_pos = pool_match.end()
        bracket_count = 1
        i = start_pos
        
        while i < len(html_content) and bracket_count > 0:
            if html_content[i] == '[':
                bracket_count += 1
            elif html_content[i] == ']':
                bracket_count -= 1
            i += 1
        
        if bracket_count == 0:
            pool_str = html_content[start_pos:i-1]
            pool_json_str = '[' + pool_str + ']'
            pool_json_str = pool_json_str.replace('\\"', '"')
            
            try:
                pool_data = json.loads(pool_json_str)
                for choice_data in pool_data:
                    choice_basic = {
                        'name': choice_data.get('title', ''),
                        'url': 'https://bazaardb.gg' + choice_data.get('url', ''),
                        'icon_url': choice_data.get('art', '')
                    }
                    choices_basic.append(choice_basic)
            except Exception as e:
                print(f"    警告: 解析pool数据失败: {e}")
    
    # 从DOM中提取中文选择名称（从h3元素中）
    h3s = soup.find_all('h3')
    chinese_choice_names = []
    exclude_names = ['Heroes', 'Size', 'Tier', 'Types & Tags']
    for h3 in h3s:
        h3_text = h3.get_text(strip=True)
        if h3_text and h3_text not in exclude_names:
            # 检查是否包含中文字符
            if any('\u4e00' <= c <= '\u9fff' for c in h3_text):
                chinese_choice_names.append(h3_text)
    
    # 从DOM中提取所有选择的描述
    # 所有 _bq div 中包含的描述
    # 前几个通常是事件描述，后面的是选择描述
    all_bq_divs = soup.find_all('div', class_=lambda x: x and '_bq' in str(x))
    
    # 过滤掉事件描述（通常包含 "You find", "You can only select", "encounter" 等）
    choice_descriptions = []
    event_desc_patterns = [
        'BronzeEventEncounter',  # 标签信息
        'SilverEventEncounter',
        'GoldEventEncounter',
        'DiamondEventEncounter',
        'You find',  # 事件描述开头
        'You can only select',  # 事件规则
        'You must pay',
        'You can leave',
        'You cannot reroll',
        'from this encounter',  # 包含 encounter 的较长文本
    ]
    
    for bq_div in all_bq_divs:
        desc_text = bq_div.get_text(strip=True)
        # 跳过明显的标签信息
        if 'Tags' in desc_text and len(desc_text) < 50:
            continue
        # 跳过事件描述（匹配事件描述模式）
        if any(pattern in desc_text for pattern in event_desc_patterns):
            continue
        # 收集选择描述
        if desc_text and len(desc_text) > 3:
            choice_descriptions.append(desc_text)
    
    # 按顺序匹配pool数据和描述
    # 如果描述数量 >= 选择数量，从最后开始匹配（避免前面的事件描述）
    choices = []
    num_choices = len(choices_basic)
    num_descriptions = len(choice_descriptions)
    
    # 从最后开始匹配：如果有x个选择，y个描述，取最后x个描述
    start_idx = max(0, num_descriptions - num_choices)
    matched_descriptions = choice_descriptions[start_idx:start_idx + num_choices] if num_descriptions >= num_choices else choice_descriptions
    
    for idx, choice_basic in enumerate(choices_basic):
        description = ''
        if idx < len(matched_descriptions):
            description = matched_descriptions[idx]
        
        # 获取中文名称（按顺序匹配）
        name_zh = ''
        if idx < len(chinese_choice_names):
            name_zh = chinese_choice_names[idx]
        
        choice = {
            'name': choice_basic['name'],
            'name_zh': name_zh,
            'url': choice_basic['url'],
            'icon_url': choice_basic['icon_url'],
            'description': description
        }
        choices.append(choice)
    
    return {
        'name': event_name,
        'url': event_url,
        'choices': choices
    }

def extract_all_from_html():
    """从所有HTML文件中提取事件数据"""
    html_files = list(HTML_DIR.glob('*.html'))
    print(f"找到 {len(html_files)} 个HTML文件\n")
    
    events_data = []
    
    for html_file in html_files:
        print(f"处理: {html_file.name}")
        try:
            event_data = extract_choices_from_html(html_file)
            if event_data:
                events_data.append(event_data)
                print(f"  ✓ 提取到 {len(event_data['choices'])} 个选择")
                # 显示前几个选择的描述
                for choice in event_data['choices'][:3]:
                    if choice['description']:
                        print(f"    - {choice['name']}: {choice['description'][:80]}...")
                    else:
                        print(f"    - {choice['name']}: 未找到描述")
            else:
                print(f"  ✗ 提取失败")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    # 保存到JSON
    output_file = OUTPUT_DIR / 'events_from_html.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 结果已保存到: {output_file}")
    print(f"总共提取到 {len(events_data)} 个事件")

if __name__ == "__main__":
    extract_all_from_html()
