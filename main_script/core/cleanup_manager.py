"""
清理管理模块
"""
import os
import subprocess
import time
import logging
import traceback
import win32gui
import win32con


class CleanupManager:
    """清理管理器"""

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_files = ['debug_binary.png', 'debug_capture.png']
            for filename in temp_files:
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                        logging.info(f"已删除临时文件: {filename}")
                    except Exception as e:
                        logging.warning(f"删除临时文件失败: {filename}, 错误: {e}")
        except Exception as e:
            logging.error(f"清理临时文件时出错: {e}")

    def cleanup_system_tray_icons(self):
        """清理系统托盘中的遗留图标"""
        try:
            logging.info("开始清理系统托盘中的遗留图标...")

            # 方法1: 使用系统命令清理通知区域
            self._cleanup_notification_area()

            # 方法2: 清理注册表中的图标缓存
            self._cleanup_icon_cache()

            # 方法3: 刷新系统托盘（不重启 Explorer）
            self._refresh_system_tray()

            logging.info("系统托盘图标清理完成")

        except Exception as e:
            logging.error(f"清理系统托盘图标时出错: {e}")
            logging.error(traceback.format_exc())

    def _cleanup_notification_area(self):
        """清理通知区域图标"""
        try:
            # 使用 PowerShell 命令清理通知区域
            ps_script = '''
            # 清理通知区域的图标缓存
            Remove-ItemProperty -Path "HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify" -Name "IconStreams" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path "HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify" -Name "PastIconsStream" -ErrorAction SilentlyContinue
            Write-Host "Notification area icons cache cleared"
            '''

            # 执行 PowerShell 脚本
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                logging.info("通知区域图标缓存已清理")
            else:
                logging.warning(f"清理通知区域失败: {result.stderr}")

        except Exception as e:
            logging.error(f"清理通知区域时出错: {e}")

    def _refresh_system_tray(self):
        """刷新系统托盘（不重启 Explorer）"""
        try:
            logging.info("正在刷新系统托盘...")

            # 获取系统托盘窗口句柄
            tray_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if tray_hwnd:
                # 发送刷新消息
                win32gui.PostMessage(tray_hwnd, win32con.WM_COMMAND, 419, 0)
                logging.info("已发送系统托盘刷新消息")

                # 尝试刷新通知区域
                notification_hwnd = win32gui.FindWindowEx(
                    tray_hwnd, None, "TrayNotifyWnd", None)
                if notification_hwnd:
                    win32gui.InvalidateRect(notification_hwnd, None, True)
                    win32gui.UpdateWindow(notification_hwnd)
                    logging.info("已刷新通知区域")

                # 等待刷新完成
                time.sleep(1)

        except Exception as e:
            logging.error(f"刷新系统托盘时出错: {e}")

    def _restart_explorer(self):
        """重启 Windows Explorer 进程（备用方法）"""
        try:
            logging.info("正在重启 Windows Explorer...")

            # 终止 Explorer 进程
            subprocess.run(
                ['taskkill', '/f', '/im', 'explorer.exe'],
                capture_output=True, timeout=10
            )

            # 等待一秒
            time.sleep(1)

            # 重新启动 Explorer
            subprocess.Popen(['explorer.exe'])

            logging.info("Windows Explorer 已重启")

        except Exception as e:
            logging.error(f"重启 Explorer 时出错: {e}")

    def _cleanup_icon_cache(self):
        """清理图标缓存"""
        try:
            # 清理图标缓存目录
            cache_dirs = [
                os.path.join(
                    os.environ.get('LOCALAPPDATA', ''),
                    'Microsoft', 'Windows', 'Explorer'),
                os.path.join(
                    os.environ.get('APPDATA', ''),
                    'Microsoft', 'Windows', 'Explorer'),
                os.path.join(os.environ.get('TEMP', ''), 'Low')
            ]

            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    # 查找并删除图标缓存文件
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            if file.lower() in [
                                'iconcache.db', 'thumbcache_*.db', '*.tmp']:
                                try:
                                    file_path = os.path.join(root, file)
                                    os.remove(file_path)
                                    logging.info(f"已删除图标缓存文件: {file_path}")
                                except Exception as e:
                                    logging.warning(
                                        f"删除图标缓存文件失败: {file_path}, 错误: {e}")

            logging.info("图标缓存清理完成")

        except Exception as e:
            logging.error(f"清理图标缓存时出错: {e}")

    def cleanup_icon_cache(self):
        """清理图标缓存（公共接口）"""
        self._cleanup_icon_cache()
