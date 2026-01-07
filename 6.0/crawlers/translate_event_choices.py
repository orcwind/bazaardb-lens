"""
事件选项翻译脚本
用于将事件的选项名称和描述从英文翻译成中文

使用方法：
1. 运行此脚本，它会读取 events_final.json
2. 对于没有 name_zh 或 description_zh 的选项，会显示需要翻译的内容
3. 可以手动编辑 events_final.json，添加 name_zh 和 description_zh 字段
4. 或者使用翻译API自动翻译（需要实现翻译函数）

注意：事件名称通常是中文，选项名称和描述是英文，需要翻译
"""

import json
import re
from pathlib import Path

def is_chinese(text):
    """检查文本是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def translate_text(text, source_lang='en', target_lang='zh'):
    """
    翻译文本（需要手动实现或使用翻译API）
    
    这里提供一个简单的框架，实际翻译需要：
    1. 使用翻译API（如Google Translate API, DeepL API等）
    2. 或手动维护翻译字典
    3. 或使用离线翻译库
    """
    # TODO: 实现翻译逻辑
    # 示例：可以使用 googletrans 库
    # from googletrans import Translator
    # translator = Translator()
    # result = translator.translate(text, src=source_lang, dest=target_lang)
    # return result.text
    
    # 临时返回空字符串，需要手动翻译
    return ""

def load_events():
    """加载事件数据"""
    event_file = Path('event_details_final/events_final.json')
    if not event_file.exists():
        print(f"错误: 找不到文件 {event_file}")
        return None
    
    with open(event_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_events(events):
    """保存事件数据"""
    event_file = Path('event_details_final/events_final.json')
    # 备份原文件
    backup_file = event_file.with_suffix('.json.bak')
    if event_file.exists():
        import shutil
        shutil.copy2(event_file, backup_file)
        print(f"已备份原文件到: {backup_file}")
    
    with open(event_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"已保存到: {event_file}")

def check_translation_status(events):
    """检查翻译状态"""
    total_events = len(events)
    events_with_zh_name = 0
    total_choices = 0
    choices_with_zh_name = 0
    choices_with_zh_desc = 0
    choices_need_translation = []  # 记录需要翻译的选项
    
    for event in events:
        # 检查事件名称
        if event.get('name_zh'):
            events_with_zh_name += 1
        elif is_chinese(event.get('name', '')):
            # 如果事件名称本身就是中文，可以复制到 name_zh
            event['name_zh'] = event['name']
            events_with_zh_name += 1
        
        # 检查选项
        for choice in event.get('choices', []):
            total_choices += 1
            choice_name = choice.get('name', '')
            choice_desc = choice.get('description', '')
            
            if choice.get('name_zh'):
                choices_with_zh_name += 1
            elif is_chinese(choice_name):
                # 如果选项名称本身就是中文，可以复制到 name_zh
                choice['name_zh'] = choice_name
                choices_with_zh_name += 1
            else:
                # 需要翻译的选项名称
                if not choice.get('name_zh') and choice_name:
                    choices_need_translation.append({
                        'event': event.get('name_zh') or event.get('name', ''),
                        'choice': choice_name,
                        'type': 'name'
                    })
            
            if choice.get('description_zh'):
                choices_with_zh_desc += 1
            elif is_chinese(choice_desc):
                # 如果描述本身就是中文，可以复制到 description_zh
                choice['description_zh'] = choice_desc
                choices_with_zh_desc += 1
            else:
                # 需要翻译的描述
                if not choice.get('description_zh') and choice_desc:
                    choices_need_translation.append({
                        'event': event.get('name_zh') or event.get('name', ''),
                        'choice': choice_name,
                        'type': 'description',
                        'text': choice_desc
                    })
    
    print(f"\n翻译状态:")
    print(f"  事件总数: {total_events}")
    print(f"  有中文名称的事件: {events_with_zh_name} ({events_with_zh_name/total_events*100:.1f}%)")
    print(f"  选项总数: {total_choices}")
    print(f"  有中文名称的选项: {choices_with_zh_name} ({choices_with_zh_name/total_choices*100:.1f}%)")
    print(f"  有中文描述的选项: {choices_with_zh_desc} ({choices_with_zh_desc/total_choices*100:.1f}%)")
    
    if choices_need_translation:
        print(f"\n需要翻译的选项数量: {len(choices_need_translation)}")
        print("\n前10个需要翻译的选项:")
        for i, item in enumerate(choices_need_translation[:10], 1):
            print(f"  {i}. [{item['event']}] {item['choice']}")
            if item['type'] == 'description':
                print(f"     描述: {item['text'][:60]}...")
    
    return {
        'events_with_zh_name': events_with_zh_name,
        'total_events': total_events,
        'choices_with_zh_name': choices_with_zh_name,
        'choices_with_zh_desc': choices_with_zh_desc,
        'total_choices': total_choices,
        'choices_need_translation': choices_need_translation
    }

def main():
    """主函数"""
    print("=" * 80)
    print("事件选项翻译工具")
    print("=" * 80)
    
    # 加载事件数据
    events = load_events()
    if not events:
        return
    
    # 检查翻译状态
    status = check_translation_status(events)
    
    # 自动处理：如果名称本身就是中文，复制到 name_zh
    print("\n正在自动处理中文名称...")
    for event in events:
        if not event.get('name_zh') and is_chinese(event.get('name', '')):
            event['name_zh'] = event['name']
        
        for choice in event.get('choices', []):
            if not choice.get('name_zh') and is_chinese(choice.get('name', '')):
                choice['name_zh'] = choice['name']
    
    # 再次检查状态
    print("\n自动处理后的状态:")
    status = check_translation_status(events)
    
    # 保存更新后的数据
    save_events(events)
    
    print("\n" + "=" * 80)
    print("提示: 对于需要翻译的选项，可以:")
    print("1. 使用翻译API自动翻译")
    print("2. 手动编辑 events_final.json，添加 name_zh 和 description_zh 字段")
    print("3. 使用在线翻译工具，然后手动添加到JSON文件中")
    print("=" * 80)

if __name__ == "__main__":
    main()

