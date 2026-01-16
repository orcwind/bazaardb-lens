#!/usr/bin/env python3
"""
工具：将 data/Json 目录打包并用 AES-GCM 加密为 data_json.enc，同时输出明文 key 文件（用于打包阶段，安装器应替换为受保护的密钥）

用法:
    python tools/encrypt_data.py

注意: 生成的 key 文件应仅用于打包流程，安装时应由安装程序使用 DPAPI 保护并替换。
"""
import os
import io
import sys
import zipfile
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def collect_json_bytes(src_dir):
    mem = io.BytesIO()
    collected_files = []
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if not fn.lower().endswith('.json'):
                    continue
                full = os.path.join(root, fn)
                # 使用文件名作为 zip 内的路径（不包含目录结构），便于查找
                arcname = fn
                zf.write(full, arcname)
                collected_files.append(fn)
    mem.seek(0)
    logging.info(f"已收集以下 JSON 文件: {', '.join(sorted(collected_files))}")
    return mem.read()

def main():
    logging.basicConfig(level=logging.INFO)
    src = os.path.join(PROJECT_ROOT, 'data', 'Json')
    if not os.path.exists(src):
        logging.error(f"未找到源目录: {src}")
        sys.exit(1)

    logging.info(f"收集 JSON 文件: {src}")
    plain = collect_json_bytes(src)
    logging.info(f"收集完成，字节数: {len(plain)}")
    
    # 验证关键文件是否被包含
    import zipfile
    import io
    mem = io.BytesIO(plain)
    with zipfile.ZipFile(mem, 'r') as zf:
        required_files = ['events_from_html.json', 'monsters_detail.json', 'items.json', 'skills.json']
        for req_file in required_files:
            found = False
            for info in zf.infolist():
                if os.path.basename(info.filename) == req_file:
                    found = True
                    break
            if found:
                logging.info(f"✓ 验证通过: {req_file} 已包含在加密包中")
            else:
                logging.warning(f"⚠ 警告: {req_file} 未包含在加密包中！")

    # 生成 AES-GCM key
    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plain, None)

    out_enc = os.path.join(PROJECT_ROOT, 'data_json.enc')
    out_key = os.path.join(PROJECT_ROOT, 'data_key.bin')

    with open(out_enc, 'wb') as f:
        # 格式: nonce (12 bytes) + ciphertext
        f.write(nonce + ct)
    with open(out_key, 'wb') as f:
        f.write(key)

    logging.info(f"生成完成: {out_enc} (加密) 以及 {out_key} (未保护的 key，请仅用于打包阶段)")
    logging.info("提示: 在安装过程中，请使用 Windows DPAPI 将 key 保护并替换 data_key.bin，或将 key 存入注册表/文件并使用 DPAPI 保护。")

if __name__ == '__main__':
    main()

