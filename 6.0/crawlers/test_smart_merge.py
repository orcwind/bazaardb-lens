"""
测试智能合并功能
验证智能覆盖机制是否正确工作
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from selenium_monster_v3 import smart_merge_skill_data, smart_merge_item_data


def test_smart_merge():
    """测试智能合并功能"""
    print("=" * 80)
    print("测试智能合并功能")
    print("=" * 80)
    
    # 测试用例1: 新数据有效，应该覆盖
    print("\n测试用例1: 新数据有效")
    existing = {
        "name": "Test Skill",
        "description": "旧描述（手动修正）",
        "url": "old_url",
        "icon": "old_icon.webp",
        "aspect_ratio": 1.0
    }
    new = {
        "name": "Test Skill",
        "description": "新描述（从网页抓取）",
        "url": "new_url",
        "icon": "new_icon.webp",
        "aspect_ratio": 1.5
    }
    
    result = smart_merge_skill_data(existing, new)
    print(f"  原有: {existing}")
    print(f"  新的: {new}")
    print(f"  结果: {result}")
    
    # 验证
    assert result['description'] == "新描述（从网页抓取）", "描述应该被新数据覆盖"
    assert result['url'] == "new_url", "URL应该被新数据覆盖"
    assert result['aspect_ratio'] == 1.5, "长宽比应该被新数据覆盖"
    print("  ✅ 测试通过：新数据有效，成功覆盖")
    
    # 测试用例2: 新数据为空，应该保留原有
    print("\n测试用例2: 新数据为空")
    existing = {
        "name": "Test Skill",
        "description": "手动修正的描述",
        "url": "old_url",
        "icon": "old_icon.webp",
        "aspect_ratio": 1.0
    }
    new = {
        "name": "Test Skill",
        "description": "",  # 空描述
        "url": "",  # 空URL
        "icon": "",  # 空图标
        "aspect_ratio": None  # 空长宽比
    }
    
    result = smart_merge_skill_data(existing, new)
    print(f"  原有: {existing}")
    print(f"  新的: {new}")
    print(f"  结果: {result}")
    
    # 验证
    assert result['description'] == "手动修正的描述", "空描述应该保留原有"
    assert result['url'] == "old_url", "空URL应该保留原有"
    assert result['icon'] == "old_icon.webp", "空图标应该保留原有"
    assert result['aspect_ratio'] == 1.0, "空长宽比应该保留原有"
    print("  ✅ 测试通过：新数据为空，保留原有")
    
    # 测试用例3: 部分数据有效
    print("\n测试用例3: 部分数据有效")
    existing = {
        "name": "Test Skill",
        "description": "手动修正的描述",
        "url": "old_url",
        "icon": "old_icon.webp",
        "aspect_ratio": 1.0
    }
    new = {
        "name": "Test Skill",
        "description": "新描述",  # 有效
        "url": "",  # 无效
        "icon": "icons/test.webp",  # 无效（默认路径）
        "aspect_ratio": 1.5  # 有效
    }
    
    result = smart_merge_skill_data(existing, new)
    print(f"  原有: {existing}")
    print(f"  新的: {new}")
    print(f"  结果: {result}")
    
    # 验证
    assert result['description'] == "新描述", "有效描述应该被覆盖"
    assert result['url'] == "old_url", "无效URL应该保留原有"
    assert result['icon'] == "old_icon.webp", "无效图标应该保留原有"
    assert result['aspect_ratio'] == 1.5, "有效长宽比应该被覆盖"
    print("  ✅ 测试通过：部分数据有效，智能合并")
    
    print("\n" + "=" * 80)
    print("所有测试通过！智能合并功能工作正常")
    print("=" * 80)


if __name__ == "__main__":
    test_smart_merge()



