import os
import json
import requests
from urllib.parse import urlparse

# 配置
json_path = 'data/events/all_events_options.json'
output_json_path = 'data/events/all_events_options_local.json'
icon_dir = 'icons'

def download_icon(url, icon_dir):
    if not url or not url.startswith('http'):
        return url  # 已经是本地或data:image
    filename = os.path.basename(urlparse(url).path)
    local_path = os.path.join(icon_dir, filename)
    if not os.path.exists(local_path):
        try:
            os.makedirs(icon_dir, exist_ok=True)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(resp.content)
                print(f'已下载: {filename}')
            else:
                print(f'下载失败: {filename} 状态码: {resp.status_code}')
        except Exception as e:
            print(f'下载异常: {filename} 错误: {e}')
    return os.path.join('icons', filename).replace('\\', '/')

def process_json(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'icon' and isinstance(v, str) and v.startswith('http'):
                obj[k] = download_icon(v, icon_dir)
            else:
                process_json(v)
    elif isinstance(obj, list):
        for item in obj:
            process_json(item)

def main():
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    process_json(data)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'处理完成，已保存到 {output_json_path}')

if __name__ == '__main__':
    main()
