"""
更新检查模块
"""
import os
import json
import logging
import requests
import threading
import time
import re
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

# 版本信息（如果version模块不存在，使用默认值）
try:
    from version import VERSION
except ImportError:
    VERSION = "1.0.0"


class UpdateChecker:
    """更新检查器类"""

    def __init__(self, config_manager, update_callback=None):
        self.config = config_manager
        self.current_version = VERSION
        self.update_callback = update_callback  # 检测到更新时的回调函数
        
        # 读取更新配置文件
        self.update_config = self._load_update_config()
        
        # 从配置文件或默认值获取更新URL
        self.update_url = self.update_config.get(
            "update_api", 
            "https://api.github.com/repos/orcwind/bazaardb-lens/releases/latest"
        )
        
        # 检查间隔（小时）
        self.check_interval_hours = self.update_config.get("check_interval_hours", 24)
        
        # 下载配置
        self.download_sources = self.update_config.get("download_sources", {})
        self.auto_download = self.update_config.get("auto_download", False)
        self.auto_install = self.update_config.get("auto_install", False)
        
        # 从配置中获取最后检查时间
        last_check_str = self.config.get("last_update_check", "")
        if last_check_str:
            try:
                self.last_check_time = datetime.fromisoformat(last_check_str)
            except Exception:
                self.last_check_time = None
        else:
            self.last_check_time = None
        
        # 临时目录（用于存放下载的安装包）
        self.temp_dir = self.update_config.get("temp_dir", "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)
    
    def _load_update_config(self):
        """加载更新配置文件"""
        update_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "update_config.json"
        )
        try:
            if os.path.exists(update_config_path):
                with open(update_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"加载更新配置文件失败: {e}")
        return {}

    def check_update(self):
        """检查更新（在后台线程中执行）"""
        if not self.should_check_update():
            return

        def check_in_background():
            try:
                logging.info(f"开始检查更新... (当前版本: {self.current_version})")
                response = requests.get(self.update_url, timeout=10)
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = latest_release.get('tag_name', '').lstrip('v')
                    release_url = latest_release.get('html_url', '')
                    release_body = latest_release.get('body', '')
                    
                    # 获取下载链接
                    download_links = self._extract_download_links(latest_release)
                    
                    # 保存检查时间
                    now = datetime.now()
                    self.last_check_time = now
                    self.config.set("last_update_check", now.isoformat())
                    
                    if self._compare_versions(latest_version, self.current_version) > 0:
                        logging.info(f"✨ 发现新版本: {latest_version} (当前版本: {self.current_version})")
                        logging.info(f"📦 更新地址: {release_url}")
                        
                        # 调用回调函数通知有更新
                        if self.update_callback:
                            try:
                                self.update_callback(latest_version, release_url, download_links, release_body)
                            except Exception as e:
                                logging.error(f"调用更新回调函数失败: {e}")
                        
                        # 如果启用了自动下载，开始下载
                        if self.auto_download:
                            self.download_update(latest_version, download_links)
                        
                        return True, latest_version, release_url, download_links
                    else:
                        logging.info(f"✅ 当前已是最新版本: {self.current_version}")
                        return False, None, None, None
                else:
                    logging.warning(f"检查更新失败: HTTP {response.status_code}")
                    return False, None, None, None
            except requests.RequestException as e:
                logging.warning(f"检查更新失败: {e}")
                return False, None, None, None
            except Exception as e:
                logging.error(f"检查更新时发生错误: {e}")
                import traceback
                logging.error(traceback.format_exc())
                return False, None, None, None

        # 在后台线程中执行
        update_thread = threading.Thread(target=check_in_background, daemon=True)
        update_thread.start()
    
    def _extract_download_links(self, release_data):
        """从release数据中提取下载链接（优先从release body提取，如果失败则使用配置文件中的备用链接）"""
        download_links = {
            "github": None,
            "baidu_netdisk": None,
            "quark_netdisk": None
        }
        
        try:
            # 1. 提取GitHub assets（.exe安装包）- 这是动态的，不需要提前知道
            assets = release_data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '')
                if re.match(r'.*Bazaar_Lens_Installer.*\.exe', name, re.IGNORECASE):
                    download_links["github"] = {
                        "url": asset.get('browser_download_url'),
                        "name": name,
                        "size": asset.get('size', 0)
                    }
                    break
            
            # 2. 从release body中提取百度网盘和夸克网盘链接（优先使用这种方式）
            body = release_data.get('body', '')
            
            # 百度网盘链接（格式：链接：https://pan.baidu.com/... 提取码：xxxx）
            baidu_match = re.search(r'[百百度度]网?盘[：:]\s*(https?://pan\.baidu\.com/[^\s]+)', body, re.IGNORECASE)
            if baidu_match:
                baidu_code_match = re.search(r'[提提取取]码[：:]\s*([a-zA-Z0-9]{4})', body, re.IGNORECASE)
                download_links["baidu_netdisk"] = {
                    "url": baidu_match.group(1),
                    "extract_code": baidu_code_match.group(1) if baidu_code_match else ""
                }
            
            # 夸克网盘链接
            quark_match = re.search(r'[夸夸克克]网?盘[：:]\s*(https?://pan\.quark\.cn/[^\s]+)', body, re.IGNORECASE)
            if quark_match:
                quark_code_match = re.search(r'[提提取取]码[：:]\s*([a-zA-Z0-9]+)', body, re.IGNORECASE)
                download_links["quark_netdisk"] = {
                    "url": quark_match.group(1),
                    "extract_code": quark_code_match.group(1) if quark_code_match else ""
                }
            
            # 3. 如果从release body中提取失败，使用配置文件中的备用链接（作为回退方案）
            download_sources = self.download_sources
            
            # 百度网盘备用链接
            if not download_links["baidu_netdisk"] and download_sources.get("baidu_netdisk", {}).get("link"):
                baidu_config = download_sources["baidu_netdisk"]
                download_links["baidu_netdisk"] = {
                    "url": baidu_config.get("link", ""),
                    "extract_code": baidu_config.get("extract_code", "")
                }
                logging.debug("使用配置文件中的百度网盘备用链接")
            
            # 夸克网盘备用链接
            if not download_links["quark_netdisk"] and download_sources.get("quark_netdisk", {}).get("link"):
                quark_config = download_sources["quark_netdisk"]
                download_links["quark_netdisk"] = {
                    "url": quark_config.get("link", ""),
                    "extract_code": quark_config.get("extract_code", "")
                }
                logging.debug("使用配置文件中的夸克网盘备用链接")
                
        except Exception as e:
            logging.error(f"提取下载链接失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        return download_links

    def should_check_update(self):
        """判断是否应该检查更新"""
        # 检查配置
        if not self.config.get("auto_update", True):
            return False

        # 检查时间间隔
        if self.last_check_time:
            time_since_last_check = datetime.now() - self.last_check_time
            hours_since_last_check = time_since_last_check.total_seconds() / 3600
            if hours_since_last_check < self.check_interval_hours:
                logging.debug(f"距离上次检查仅过了{hours_since_last_check:.1f}小时，跳过检查（间隔：{self.check_interval_hours}小时）")
                return False
        
        return True

    def download_update(self, version, download_links):
        """下载更新（在后台线程中执行）"""
        def download_in_background():
            try:
                download_sources = self.download_sources
                
                # 优先使用GitHub下载（直接下载）
                if download_sources.get("github", {}).get("enabled", True) and download_links.get("github"):
                    github_link = download_links["github"]
                    download_path = self._download_from_github(github_link["url"], version)
                    if download_path and os.path.exists(download_path):
                        logging.info(f"✅ 下载成功: {download_path}")
                        if self.auto_install:
                            # 延迟一下，确保下载完全完成
                            time.sleep(1)
                            self.install_update(download_path)
                        return download_path
                    else:
                        logging.warning("GitHub下载失败")
                
                # 如果GitHub下载失败，提示用户使用其他下载源
                logging.warning("GitHub下载失败或未启用，请手动下载")
                
                # 提供百度网盘和夸克网盘链接（打开浏览器）
                if download_sources.get("baidu_netdisk", {}).get("enabled", False) and download_links.get("baidu_netdisk"):
                    baidu_link = download_links["baidu_netdisk"]
                    logging.info(f"📦 百度网盘链接: {baidu_link['url']}")
                    if baidu_link.get("extract_code"):
                        logging.info(f"🔑 提取码: {baidu_link['extract_code']}")
                    # 可以选择打开浏览器
                    # webbrowser.open(baidu_link["url"])
                
                if download_sources.get("quark_netdisk", {}).get("enabled", False) and download_links.get("quark_netdisk"):
                    quark_link = download_links["quark_netdisk"]
                    logging.info(f"📦 夸克网盘链接: {quark_link['url']}")
                    if quark_link.get("extract_code"):
                        logging.info(f"🔑 提取码: {quark_link['extract_code']}")
                    # 可以选择打开浏览器
                    # webbrowser.open(quark_link["url"])
                
                return None
            except Exception as e:
                logging.error(f"下载更新失败: {e}")
                import traceback
                logging.error(traceback.format_exc())
                return None
        
        download_thread = threading.Thread(target=download_in_background, daemon=True)
        download_thread.start()
    
    def _download_from_github(self, url, version):
        """从GitHub下载安装包"""
        try:
            logging.info(f"开始从GitHub下载: {url}")
            
            # 获取文件名
            filename = os.path.basename(url.split('?')[0])
            download_path = os.path.join(self.temp_dir, filename)
            
            # 下载文件（支持断点续传）
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            logging.debug(f"下载进度: {progress:.1f}%")
            
            logging.info(f"下载完成: {download_path} ({downloaded_size} bytes)")
            return download_path
        except Exception as e:
            logging.error(f"GitHub下载失败: {e}")
            return None
    
    def install_update(self, installer_path):
        """安装更新：关闭程序并运行安装程序"""
        try:
            if not os.path.exists(installer_path):
                logging.error(f"安装包不存在: {installer_path}")
                return False
            
            logging.info(f"准备安装更新: {installer_path}")
            
            # 创建安装脚本（在程序退出后运行）
            if sys.platform == 'win32':
                # Windows: 创建一个批处理脚本来执行安装
                script_path = os.path.join(self.temp_dir, "install_update.bat")
                with open(script_path, 'w', encoding='gbk') as f:
                    # 等待程序退出，然后运行安装程序
                    f.write(f'@echo off\n')
                    f.write(f'timeout /t 2 /nobreak >nul\n')
                    f.write(f'start /wait "" "{installer_path}"\n')
                    f.write(f'del "%~f0"\n')  # 删除批处理脚本自身
                
                # 启动批处理脚本（不等待）
                subprocess.Popen([script_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                # 延迟一下，让批处理脚本启动
                time.sleep(0.5)
                
                # 退出当前程序
                logging.info("程序即将退出以进行更新安装...")
                if self.update_callback:
                    try:
                        # 通知主程序准备退出
                        self.update_callback.on_install_start()
                    except:
                        pass
                
                # 使用os._exit强制退出（更快，更彻底）
                os._exit(0)
            else:
                logging.warning("非Windows系统，无法自动安装")
                return False
            
            return True
        except Exception as e:
            logging.error(f"安装更新失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False

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
