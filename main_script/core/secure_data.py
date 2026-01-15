"""
安全数据加载器

功能:
 - 在运行时查找打包后的加密包 (data_json.enc) 和未保护的 key (data_key.bin)
 - 使用 AES-GCM 解密包并在内存中以 zip 形式打开，提供 get_json(name) 接口
 - 若未找到加密包，则回退到直接从磁盘读取 JSON 文件（与现有代码兼容）

注意:
 - data_key.bin 在打包后应由安装器替换为受 DPAPI 保护的版本；目前实现会直接读取未保护的 key 文件以便调试/打包测试。
 - 本模块尽量保持对上层透明：上层只需调用 get_json(filename) 即可。
"""
from __future__ import annotations
import os
import sys
import io
import json
import zipfile
import logging
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    AESGCM = None
try:
    import win32crypt
except Exception:
    win32crypt = None


def _get_base_path():
    # 打包环境下使用 _MEIPASS，否则回退到项目根
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    # main_script/core/secure_data.py -> project_root/main_script/core -> up two
    current = os.path.abspath(__file__)
    core_dir = os.path.dirname(current)
    main_script_dir = os.path.dirname(core_dir)
    project_root = os.path.dirname(main_script_dir)
    return project_root


class SecureDataBundle:
    def __init__(self):
        self.base = _get_base_path()
        self.enc_path = os.path.join(self.base, 'data_json.enc')
        self.key_path = os.path.join(self.base, 'data_key.bin')
        self._zip_files = None  # dict: name -> bytes
        if AESGCM is None:
            logging.warning("cryptography 库不可用，SecureDataBundle 将无法解密。回退到磁盘读取。")
            return
        if os.path.exists(self.enc_path) and os.path.exists(self.key_path):
            try:
                self._load_and_decrypt()
                logging.info(f"[SecureData] 成功载入加密数据包，包含文件数: {len(self._zip_files) if self._zip_files else 0}")
            except Exception as e:
                logging.error(f"[SecureData] 解密或载入失败: {e}")
                self._zip_files = None
        else:
            logging.debug(f"[SecureData] 未找到加密包或 key: enc={os.path.exists(self.enc_path)}, key={os.path.exists(self.key_path)}")

    def _load_and_decrypt(self):
        # 优先尝试从受保护的 key 文件读取并使用 Windows DPAPI 解密
        prot_path = os.path.join(self.base, 'data_key_prot.bin')
        key = None
        if os.path.exists(prot_path) and win32crypt is not None:
            try:
                with open(prot_path, 'rb') as f:
                    prot_blob = f.read()
                # CryptUnprotectData 返回 (description, plaintext_bytes)
                _, decrypted = win32crypt.CryptUnprotectData(prot_blob, None, None, None, 0)
                key = decrypted
                logging.info("[SecureData] 使用 DPAPI 解密受保护 key")
            except Exception as e:
                logging.warning(f"[SecureData] DPAPI 解密受保护 key 失败: {e}")

        # 回退到未保护的 key 文件
        if key is None:
            with open(self.key_path, 'rb') as f:
                key = f.read()
        with open(self.enc_path, 'rb') as f:
            data = f.read()
        if len(data) < 13:
            raise ValueError("加密文件太短")
        nonce = data[:12]
        ct = data[12:]
        aes = AESGCM(key)
        plain = aes.decrypt(nonce, ct, None)
        # 解析为 zip
        mem = io.BytesIO(plain)
        zf = zipfile.ZipFile(mem, 'r')
        files = {}
        for info in zf.infolist():
            # 只保留文件名最后一部分（与原来开文件名一致）
            files[info.filename] = zf.read(info.filename)
        self._zip_files = files

    def get_json(self, filename: str) -> Optional[dict]:
        """
        读取指定的 JSON 文件（只传文件名，例如 'monsters_detail.json'）
        返回已解析的 Python 对象或 None（找不到或解析失败）
        """
        # 优先使用内存中的加密包
        try:
            if self._zip_files is not None:
                # 尝试直接按传入 filename 查找
                if filename in self._zip_files:
                    raw = self._zip_files[filename]
                else:
                    # 尝试 basename 查找
                    base = os.path.basename(filename)
                    raw = self._zip_files.get(base)
                if raw:
                    return json.loads(raw.decode('utf-8'))
        except Exception as e:
            logging.error(f"[SecureData] 从加密包读取 {filename} 失败: {e}")

        # 回退：从磁盘读取原始文件（保持向后兼容）
        try:
            disk_path = os.path.join(self.base, 'data', 'Json', filename)
            if os.path.exists(disk_path):
                with open(disk_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # 兼容旧目录名
            alt = os.path.join(self.base, 'data', 'Json - 副本', filename)
            if os.path.exists(alt):
                with open(alt, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"[SecureData] 从磁盘读取 {filename} 失败: {e}")

        return None


# 单例实例，模块导入时创建（上层直接使用 secure_bundle.get_json(...)）
secure_bundle = SecureDataBundle()

