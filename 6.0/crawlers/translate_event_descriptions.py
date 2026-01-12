"""翻译JSON文件中的描述为中文"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'Json' / 'events_from_html.json'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'Json' / 'events_from_html.json'

# 翻译功能（可选）
_translator = None
def get_translator():
    """获取翻译器（懒加载）"""
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source='en', target='zh-CN')
            print("✓ 翻译库已加载")
        except ImportError:
            print("⚠️  deep-translator 未安装，将跳过描述翻译")
            print("   安装方法: pip install deep-translator")
            _translator = False  # 标记为不可用
    return _translator

def translate_description(text):
    """翻译描述为中文"""
    if not text:
        return ''
    
    translator = get_translator()
    if translator is False:
        return ''  # 翻译器不可用
    
    try:
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"    翻译失败: {e}")
        return ''

def translate_events_descriptions():
    """翻译事件选择描述为中文"""
    # 读取JSON文件
    print(f"读取文件: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        events_data = json.load(f)
    
    print(f"找到 {len(events_data)} 个事件\n")
    
    # 统计需要翻译的数量
    total_choices = 0
    choices_to_translate = 0
    for event in events_data:
        for choice in event.get('choices', []):
            total_choices += 1
            description = choice.get('description', '')
            description_zh = choice.get('description_zh', '')
            if description and not description_zh:
                choices_to_translate += 1
    
    print(f"总共 {total_choices} 个选择，需要翻译 {choices_to_translate} 个描述\n")
    
    # 翻译描述
    translated_count = 0
    for event_idx, event in enumerate(events_data, 1):
        event_name = event.get('name', '')
        print(f"[{event_idx}/{len(events_data)}] {event_name}")
        
        for choice_idx, choice in enumerate(event.get('choices', []), 1):
            description = choice.get('description', '')
            description_zh = choice.get('description_zh', '')
            
            # 如果已有中文描述，跳过
            if description_zh:
                continue
            
            # 如果有英文描述，进行翻译
            if description:
                print(f"  [{choice_idx}/{len(event['choices'])}] {choice.get('name', '')}: 翻译中...")
                translated = translate_description(description)
                if translated:
                    choice['description_zh'] = translated
                    translated_count += 1
                    print(f"    ✓ {translated[:60]}...")
                else:
                    print(f"    ✗ 翻译失败")
        print()
    
    # 保存更新后的JSON文件
    print(f"保存文件: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 完成！已翻译 {translated_count} 个描述")

if __name__ == "__main__":
    translate_events_descriptions()

