"""
更新检查模块
"""
import logging
import requests
import threading

# 版本信息（如果version模块不存在，使用默认值）
try:
    from version import VERSION
except ImportError:
    VERSION = "1.0.0"


class UpdateChecker:
    """更新检查器类"""

    def __init__(self, config_manager):
        self.config = config_manager
        self.current_version = VERSION
        self.update_url = "https://api.github.com/repos/your-repo/bazaar-lens/releases/latest"
        self.last_check_time = None

    def check_update(self):
        """检查更新（在后台线程中执行）"""
        if not self.should_check_update():
            return

        def check_in_background():
            try:
                logging.info("开始检查更新...")
                response = requests.get(self.update_url, timeout=5)
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = latest_release.get('tag_name', '').lstrip('v')
                    
                    if self._compare_versions(latest_version, self.current_version) > 0:
                        logging.info(f"发现新版本: {latest_version} (当前版本: {self.current_version})")
                        # 可以在这里显示更新通知
                        return True
                    else:
                        logging.info("当前已是最新版本")
                        return False
                else:
                    logging.warning(f"检查更新失败: HTTP {response.status_code}")
                    return False
            except requests.RequestException as e:
                logging.warning(f"检查更新失败: {e}")
                return False
            except Exception as e:
                logging.error(f"检查更新时发生错误: {e}")
                return False

        # 在后台线程中执行
        update_thread = threading.Thread(target=check_in_background, daemon=True)
        update_thread.start()

    def should_check_update(self):
        """判断是否应该检查更新"""
        # 检查配置
        if not self.config.get("auto_update", True):
            return False

        # 可以添加时间间隔检查，避免频繁检查
        # 这里简化处理，每次都检查
        return True

    def _compare_versions(self, version1, version2):
        """比较版本号，返回1表示version1>version2，-1表示version1<version2，0表示相等"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except Exception as e:
            logging.error(f"版本比较失败: {e}")
            return 0
