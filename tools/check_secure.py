#!/usr/bin/env python3
import sys, os, traceback

print("Python:", sys.version)
try:
    # 使用 importlib.util 按文件路径安全加载模块
    import importlib.util
    secure_path = os.path.join(os.path.dirname(__file__), '..', 'main_script', 'core', 'secure_data.py')
    secure_path = os.path.abspath(secure_path)
    spec = importlib.util.spec_from_file_location("secure_data_temp", secure_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法为路径创建 spec: {secure_path}")
    secure_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(secure_mod)
    secure_bundle = getattr(secure_mod, 'secure_bundle', None)
    if secure_bundle is None:
        print("secure_bundle 未在模块中找到")
        sys.exit(1)
except Exception as e:
    print("按路径加载 secure_bundle 失败:", e)
    traceback.print_exc()
    sys.exit(1)

print("enc_path:", getattr(secure_bundle, "enc_path", None))
print("key_path:", getattr(secure_bundle, "key_path", None))
print("prot_path:", os.path.join(getattr(secure_bundle, "base", "."), "data_key_prot.bin"))
zip_files = getattr(secure_bundle, "_zip_files", None)
print("_zip_files is None?", zip_files is None)
if zip_files:
    print("包含文件数:", len(zip_files))
    names = list(zip_files.keys())
    print("示例文件:", names[:10])
    target = 'monsters_detail.json'
    print(f"是否包含 {target} :", target in zip_files)
    if target in zip_files:
        data = zip_files[target]
        try:
            text = data.decode('utf-8')
            print(f"{target} 前200字符:\n", text[:200])
        except Exception as e:
            print("解码文件失败:", e)
else:
    # 回退：尝试从磁盘直接读取
    base = getattr(secure_bundle, "base", ".")
    path = os.path.join(base, "data", "Json", "monsters_detail.json")
    print("回退读取磁盘文件:", path, "exists=", os.path.exists(path))
    if os.path.exists(path):
        try:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                arr = json.load(f)
            print("磁盘 monsters_detail.json 条目数:", len(arr) if isinstance(arr, list) else "not list")
        except Exception as e:
            print("读取磁盘文件失败:", e)
            traceback.print_exc()

print("done")

