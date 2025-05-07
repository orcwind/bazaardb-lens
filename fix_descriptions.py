import json
import re
import os

def fix_description(text):
    """修复描述文本中单词之间缺少空格的问题"""
    if not text:
        return text
    
    # 确保关键词和数字之间有空格
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    
    # 确保数字和单词之间有空格
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    
    # 确保单词之间有空格
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # 特殊处理一些常见的游戏术语
    # 修复 "leftmost" + 关键词
    text = re.sub(r'leftmost([A-Z][a-z]+)', r'leftmost \1', text)
    
    # 修复 "Max" + 关键词
    text = re.sub(r'Max([A-Z][a-z]+)', r'Max \1', text)
    
    # 修复 "Damage" + "for the fight"
    text = re.sub(r'Damagefor', r'Damage for', text)
    
    # 修复 "Shield" + "for the fight"
    text = re.sub(r'Shieldfor', r'Shield for', text)
    
    # 修复 "Heal" + "equal"
    text = re.sub(r'Healequal', r'Heal equal', text)
    
    # 修复 "Deal" + "Damage"
    text = re.sub(r'DealDamage', r'Deal Damage', text)
    
    # 修复 "Health" + "each"
    text = re.sub(r'Healtheach', r'Health each', text)
    
    return text

def main():
    # 读取 monsters.json 文件
    try:
        with open('data/monsters.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("错误: 找不到 data/monsters.json 文件")
        return
    
    # 备份原文件
    backup_path = 'data/monsters.json.bak'
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已创建备份文件: {backup_path}")
    
    # 修复所有描述文本
    fixed_count = 0
    for monster in data.get('monsters', []):
        # 修复技能描述
        for skill in monster.get('skills', []):
            if 'description' in skill:
                original = skill['description']
                fixed = fix_description(original)
                if original != fixed:
                    skill['description'] = fixed
                    fixed_count += 1
        
        # 修复物品描述
        for item in monster.get('items', []):
            if 'description' in item:
                original = item['description']
                fixed = fix_description(original)
                if original != fixed:
                    item['description'] = fixed
                    fixed_count += 1
    
    # 保存修复后的文件
    with open('data/monsters.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"修复完成，共修复了 {fixed_count} 条描述文本")

if __name__ == '__main__':
    main() 