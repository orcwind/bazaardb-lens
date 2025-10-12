"""
应用2025年10月10日补丁更新
自动更新monsters_v3.json和events_final.json中受影响的数据
"""

import json
from pathlib import Path

# 补丁数据：需要更新的技能和物品描述
SKILL_UPDATES = {
    "Full Arsenal": {
        "old": "Your item's Cooldowns are reduced by 5% » 10% if you have a Vehicle, reduced by 5% » 10% if you have a Weapon, and reduced by 5% » 10% if you have a Tool.",
        "new": "Your item's Cooldowns are reduced by 2% » 4% if you have a Vehicle, reduced by 2% » 4% if you have a Weapon, and reduced by 2% » 4% if you have a Tool."
    },
    "Snowstorm": {
        "old": "When you Freeze, a Weapon gains +30 » +60 » +90 » +120 Damage for the fight.",
        "new": "When you Freeze, a Weapon gains +20 » +40 » +60 » +80 Damage for the fight."
    },
    "Guardian's Fury": {
        "old": "While you are Shielded, your Weapons' Cooldowns are are reduced by 10% » 20% » 30%.",
        "new": "While you are Shielded, your Weapons' Cooldowns are reduced by 5% » 10% » 15%."
    },
    "Parting Shot": {
        "pattern": "When you use an item with Ammo, it gains +5% » +10% Crit Chance",
        "new": "When you use an item with Ammo, it gains +10% » +15% Crit Chance for the fight."
    }
}

ITEM_UPDATES = {
    "Eagle Talisman": {
        "old": "When you sell this, your leftmost item gains 5% » 10% » 15% » 20% Crit Chance.",
        "new": "When you sell this, your leftmost item gains 5% » 10% » 20% Crit Chance."
    },
    "Ectoplasm": {
        "old": "Poison 1 » 2 » 3. Heal equal to an enemy's Poison",
        "new": "Poison 10 » 20 » 30. Heal equal to an enemy's Poison"
    },
    "Cinders": {
        "old": "When you sell this, your leftmost Burn item gains +1 » +2 » +3 » +4 Burn.",
        "new": "When you sell this, your leftmost Burn item gains +1 » +2 » +4 » +8 Burn."
    },
    "Extract": {
        "old": "When you sell this, your leftmost Poison item gains +1 » +2 » +3 » +4 Poison.",
        "new": "When you sell this, your leftmost Poison item gains +1 » +2 » +4 » +8 Poison."
    },
    "Feather": {
        "old": "When you sell this, reduce your items' Cooldowns by 2% » 4% » 6%.",
        "new": "When you sell this, reduce your items' Cooldowns by 3% » 6%."
    },
    "Gland": {
        "old": "When you sell this, gain 1 » 2 » 3 » 4 Regen.",
        "new": "When you sell this, gain 2 » 4 » 8 » 16 Regen."
    },
    "Gunpowder": {
        "old": "When you sell this, your leftmost Ammo item gains 1 » 2 » 3 Max Ammo.",
        "new": "When you sell this, your leftmost Ammo item gains 1 » 2 » 4 Max Ammo."
    },
    "Insect Wing": {
        "old": "When you sell this, reduce your leftmost item's Cooldown by 3% » 6% » 9%.",
        "new": "When you sell this, reduce your leftmost item's Cooldown by 2% » 4% » 8%."
    },
    "Scrap": {
        "old": "When you sell this, your leftmost Shield item gains +3 » +6 » +12 » +24 Shield.",
        "new": "When you sell this, your leftmost Shield item gains +4 » +8 » +16 » +32 Shield."
    },
    "Sharpening Stone": {
        "old": "When you sell this, your leftmost Weapon gains 5 » 10 » 15 » 20 Damage.",
        "new": "When you sell this, your leftmost Weapon gains 4 » 8 » 16 » 32 Damage."
    },
    "Necronomicon": {
        "pattern": "Gain 10 Regen for the fight. When any non-Weapon is used, Charge this 1 second(s).",
        "new": "Gain 10 Regen for the fight. When any non-Weapon is used, Charge this 1 second(s). If you are a Cult Member, reduce this item's cooldown by 1 second."
    },
    "Admiral's Badge": {
        "pattern": "When you use a Vehicle or Flying item, Slow an item on each Player's board for 1 second(s).. Your items are affected by Freeze and Slow for half as long.",
        "new": "When you use a Vehicle or Flying item, Slow an item on each Player's board for 1 second(s). Your Flying items are affected by Freeze and Slow for half as long."
    }
}


def update_monsters(monsters_file):
    """更新怪物数据"""
    print("="*80)
    print("更新怪物数据")
    print("="*80)
    
    with open(monsters_file, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    skill_update_count = 0
    item_update_count = 0
    
    for monster in monsters:
        # 更新技能
        for skill in monster.get('skills', []):
            skill_name = skill.get('name')
            if skill_name in SKILL_UPDATES:
                update_info = SKILL_UPDATES[skill_name]
                old_desc = skill.get('description', '')
                
                if 'old' in update_info and old_desc == update_info['old']:
                    skill['description'] = update_info['new']
                    skill_update_count += 1
                    print(f"✓ 更新技能: {monster['name']} - {skill_name}")
                elif 'pattern' in update_info and update_info['pattern'] in old_desc:
                    skill['description'] = update_info['new']
                    skill_update_count += 1
                    print(f"✓ 更新技能: {monster['name']} - {skill_name}")
        
        # 更新物品
        for item in monster.get('items', []):
            item_name = item.get('name')
            if item_name in ITEM_UPDATES:
                update_info = ITEM_UPDATES[item_name]
                old_desc = item.get('description', '')
                
                if 'old' in update_info and old_desc == update_info['old']:
                    item['description'] = update_info['new']
                    item_update_count += 1
                    print(f"✓ 更新物品: {monster['name']} - {item_name}")
                elif 'pattern' in update_info and update_info['pattern'] in old_desc:
                    item['description'] = update_info['new']
                    item_update_count += 1
                    print(f"✓ 更新物品: {monster['name']} - {item_name}")
    
    # 保存更新后的数据
    with open(monsters_file, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, ensure_ascii=False, indent=2)
    
    print(f"\n总计:")
    print(f"  更新技能数: {skill_update_count}")
    print(f"  更新物品数: {item_update_count}")
    print(f"✓ 已保存到: {monsters_file}")
    
    return skill_update_count, item_update_count


def check_gibbus(monsters_file):
    """检查Gibbus数据是否完整"""
    print("\n" + "="*80)
    print("检查新怪物: Gibbus")
    print("="*80)
    
    with open(monsters_file, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
    
    gibbus = None
    for monster in monsters:
        if monster['name'] == 'Gibbus':
            gibbus = monster
            break
    
    if gibbus:
        print(f"✓ 找到Gibbus")
        print(f"  URL: {gibbus['url']}")
        print(f"  技能数: {len(gibbus['skills'])}")
        print(f"  物品数: {len(gibbus['items'])}")
        
        # 检查技能
        for skill in gibbus['skills']:
            print(f"\n  技能: {skill['name']}")
            print(f"    描述: {skill.get('description', 'N/A')[:80]}...")
            print(f"    长宽比: {skill.get('aspect_ratio', 'N/A')}")
        
        # 检查物品
        print(f"\n  物品列表:")
        for item in gibbus['items']:
            print(f"    - {item['name']} (比例: {item.get('aspect_ratio', 'N/A')})")
        
        # 验证新物品Moon Orb
        moon_orb = next((i for i in gibbus['items'] if i['name'] == 'Moon Orb'), None)
        if moon_orb:
            print(f"\n  ✓ Moon Orb存在")
            print(f"    描述: {moon_orb.get('description', 'N/A')[:80]}...")
        else:
            print(f"\n  ✗ 缺少Moon Orb")
        
        return True
    else:
        print(f"✗ 未找到Gibbus")
        return False


def main():
    """主函数"""
    print("="*80)
    print("应用2025年10月10日补丁更新")
    print("="*80)
    
    monsters_file = Path('monster_details_v3/monsters_v3.json')
    
    # 1. 检查Gibbus
    gibbus_ok = check_gibbus(monsters_file)
    
    # 2. 更新技能和物品描述
    print("\n" + "="*80)
    print("更新受影响的技能和物品")
    print("="*80)
    
    skill_count, item_count = update_monsters(monsters_file)
    
    # 总结
    print("\n" + "="*80)
    print("补丁应用完成")
    print("="*80)
    print(f"\n✓ Gibbus数据: {'完整' if gibbus_ok else '缺失'}")
    print(f"✓ 更新技能: {skill_count} 个")
    print(f"✓ 更新物品: {item_count} 个")
    print("\n提示: 部分物品（如Eagle Talisman）可能需要手动检查，因为描述格式可能不完全匹配")


if __name__ == "__main__":
    main()

