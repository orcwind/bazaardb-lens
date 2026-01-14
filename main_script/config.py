"""
配置管理模块
"""
import os
import sys
import json
import logging


class ConfigManager:
    """配置管理类，用于保存和加载配置"""

    def __init__(self):
        self.config_file = "bazaar_lens_config.json"
        # 默认 Tesseract 路径：必须使用项目目录下的便携版
        if getattr(sys, 'frozen', False):
            # 打包环境：使用可执行文件所在目录
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # 开发环境：使用项目根目录（main_script的父目录）
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        portable_tesseract = os.path.join(
            app_dir, "Tesseract-OCR", "tesseract.exe")

        self.default_config = {
            "tesseract_path": portable_tesseract,
            "last_update_check": "",
            "auto_update": True,
            "show_console": False
        }
        self.config = self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 确保所有默认配置项都存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value

                # 强制使用便携版路径（如果存在），覆盖配置文件中的旧路径
                # 重新计算便携版路径（确保使用正确的项目根目录）
                if getattr(sys, 'frozen', False):
                    app_dir = os.path.dirname(os.path.abspath(sys.executable))
                else:
                    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                portable_tesseract = os.path.join(app_dir, "Tesseract-OCR", "tesseract.exe")
                if portable_tesseract and os.path.exists(portable_tesseract):
                    config["tesseract_path"] = portable_tesseract
                    logging.info(f"强制使用便携版Tesseract: {portable_tesseract}")

                return config
            else:
                return self.default_config.copy()
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return self.default_config.copy()

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False

    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项并保存"""
        self.config[key] = value
        return self.save_config()

    def get_tesseract_path(self):
        """获取Tesseract OCR路径"""
        return self.get(
            "tesseract_path",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    def set_tesseract_path(self, path):
        """设置Tesseract OCR路径"""
        if path and os.path.exists(path) and os.path.isfile(path):
            return self.set("tesseract_path", path)
        return False
