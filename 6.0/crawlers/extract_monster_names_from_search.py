#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从bazaardb.gg搜索页面提取所有怪物名称
"""

import json
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_monster_names_from_search():
    """从搜索页面提取所有怪物名称"""
    driver = setup_driver()
    monster_names = set()
    
    try:
        print("🔍 正在访问怪物搜索页面...")
        driver.get("https://bazaardb.gg/search?c=monsters")
        
        # 等待页面加载
        time.sleep(3)
        
        print("📄 正在提取怪物名称...")
        
        # 方法1: 查找所有怪物标题元素
        try:
            # 尝试多种可能的选择器
            selectors = [
                "h3",  # 怪物名称通常用h3标签
                ".monster-name",
                "[data-testid='monster-name']",
                "a[href*='/monster/']",
                ".card-title",
                ".monster-title"
            ]
            
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ 使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                    
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 2 and len(text) < 50:  # 过滤掉太短或太长的文本
                            # 检查是否包含Level信息，如果有则提取怪物名称
                            if "Level" in text:
                                # 提取Level之前的部分作为怪物名称
                                monster_name = text.split("Level")[0].strip()
                                if monster_name:
                                    monster_names.add(monster_name)
                            else:
                                # 直接使用文本作为怪物名称
                                monster_names.add(text)
                    
                    if monster_names:
                        break
        except Exception as e:
            print(f"⚠️ 方法1失败: {e}")
        
        # 方法2: 从页面源码中提取
        if not monster_names:
            print("🔄 尝试从页面源码提取...")
            page_source = driver.page_source
            
            # 查找怪物名称的模式
            patterns = [
                r'<h3[^>]*>([^<]+)</h3>',
                r'<a[^>]*href="[^"]*monster[^"]*"[^>]*>([^<]+)</a>',
                r'"name":\s*"([^"]+)"',
                r'Level\s+\d+\s+•\s+Day\s+\d+.*?([A-Za-z][A-Za-z0-9\s\'-]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    if len(name) > 2 and len(name) < 50:
                        monster_names.add(name)
        
        # 方法3: 滚动页面加载更多内容
        if len(monster_names) < 50:  # 如果数量太少，尝试滚动
            print("📜 尝试滚动页面加载更多内容...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            for i in range(5):  # 最多滚动5次
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # 重新尝试提取
            elements = driver.find_elements(By.TAG_NAME, "h3")
            for element in elements:
                text = element.text.strip()
                if text and len(text) > 2 and len(text) < 50:
                    monster_names.add(text)
        
        print(f"📊 总共提取到 {len(monster_names)} 个怪物名称")
        
        # 保存结果
        monster_list = sorted(list(monster_names))
        
        # 保存到JSON文件
        with open('extracted_monsters.json', 'w', encoding='utf-8') as f:
            json.dump(monster_list, f, ensure_ascii=False, indent=2)
        
        # 保存到文本文件
        with open('extracted_monsters.txt', 'w', encoding='utf-8') as f:
            for name in monster_list:
                f.write(f'"{name}"\n')
        
        print(f"💾 结果已保存到 extracted_monsters.json 和 extracted_monsters.txt")
        print(f"📝 前10个怪物名称: {monster_list[:10]}")
        
        return monster_list
        
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return []
    
    finally:
        driver.quit()

if __name__ == "__main__":
    extract_monster_names_from_search()


