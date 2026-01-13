"""使用JavaScript提取选择和描述"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json

def setup_driver():
    """设置Chrome驱动"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def extract_with_js():
    """使用JavaScript提取选择和描述"""
    driver = setup_driver()
    try:
        url = "https://bazaardb.gg/card/boa7agty4t9e2tbcgyc210tqh/%E5%A5%87%E5%BC%82%E8%98%91%E8%8F%87"
        print(f"访问: {url}")
        driver.get(url)
        time.sleep(5)
        
        # 使用JavaScript提取所有h3文本和对应的描述
        script = """
        const h3s = Array.from(document.querySelectorAll('h3'));
        const descs = Array.from(document.querySelectorAll('div._bk, div._bq'));
        const result = [];
        
        for (let i = 0; i < h3s.length; i++) {
            const h3 = h3s[i];
            const text = h3.textContent.trim();
            if (!text) continue;
            
            // 查找h3后面的第一个描述
            let desc = '';
            for (let j = 0; j < descs.length; j++) {
                const d = descs[j];
                if (d.compareDocumentPosition(h3) & Node.DOCUMENT_POSITION_FOLLOWING) {
                    desc = d.textContent.trim();
                    break;
                }
            }
            
            result.push({name: text, description: desc});
        }
        
        return result;
        """
        
        result = driver.execute_script(script)
        print(f"\n找到 {len(result)} 个选择\n")
        for i, item in enumerate(result[:10], 1):
            print(f"{i}. {item['name']}")
            if item['description']:
                print(f"   描述: {item['description'][:80]}")
            else:
                print(f"   ✗ 未找到描述")
            print()
        
        # 保存到JSON
        with open('debug_choices_descriptions.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("结果已保存到 debug_choices_descriptions.json")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    extract_with_js()


