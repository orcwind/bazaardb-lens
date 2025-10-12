#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的系统托盘图标清理工具
用于清理 Bazaar_Lens 遗留的系统托盘图标
"""

import os
import sys
import time
import subprocess
import win32gui
import win32con
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def cleanup_notification_area():
    """清理通知区域图标缓存"""
    try:
        logging.info("正在清理通知区域图标缓存...")
        
        # 方法1: 直接使用 reg 命令
        try:
            # 删除 IconStreams
            subprocess.run(['reg', 'delete', 
                'HKCU\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify',
                '/v', 'IconStreams', '/f'], 
                capture_output=True, timeout=10)
            
            # 删除 PastIconsStream
            subprocess.run(['reg', 'delete', 
                'HKCU\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify',
                '/v', 'PastIconsStream', '/f'], 
                capture_output=True, timeout=10)
            
            logging.info("通知区域注册表项已清理")
        except Exception as e:
            logging.warning(f"使用 reg 命令清理失败: {e}")
        
        # 方法2: 使用 PowerShell 备用方案
        ps_script = '''
        $paths = @(
            "HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\TrayNotify",
            "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\TrayNotify"
        )
        
        foreach ($path in $paths) {
            try {
                if (Test-Path $path) {
                    Remove-ItemProperty -Path $path -Name "IconStreams" -ErrorAction SilentlyContinue
                    Remove-ItemProperty -Path $path -Name "PastIconsStream" -ErrorAction SilentlyContinue
                    Write-Host "清理路径: $path"
                }
            } catch {
                Write-Host "清理路径 $path 失败: $_"
            }
        }
        Write-Host "通知区域图标缓存清理完成"
        '''
        
        result = subprocess.run([
            'powershell', '-Command', ps_script
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logging.info("PowerShell 清理完成")
        else:
            logging.warning(f"PowerShell 清理失败: {result.stderr}")
            
    except Exception as e:
        logging.error(f"清理通知区域时出错: {e}")

def refresh_system_tray():
    """刷新系统托盘"""
    try:
        logging.info("正在刷新系统托盘...")
        
        # 获取系统托盘窗口句柄
        tray_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
        if tray_hwnd:
            # 发送刷新消息
            win32gui.PostMessage(tray_hwnd, win32con.WM_COMMAND, 419, 0)
            logging.info("已发送系统托盘刷新消息")
            
            # 刷新通知区域
            notification_hwnd = win32gui.FindWindowEx(tray_hwnd, None, "TrayNotifyWnd", None)
            if notification_hwnd:
                win32gui.InvalidateRect(notification_hwnd, None, True)
                win32gui.UpdateWindow(notification_hwnd)
                logging.info("已刷新通知区域")
        
        time.sleep(1)
        
    except Exception as e:
        logging.error(f"刷新系统托盘时出错: {e}")

def cleanup_icon_cache():
    """清理图标缓存文件"""
    try:
        logging.info("正在清理图标缓存文件...")
        
        cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
            os.path.join(os.environ.get('TEMP', ''), 'Low')
        ]
        
        cleaned_count = 0
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        if file.lower() in ['iconcache.db'] or file.lower().startswith('thumbcache_'):
                            try:
                                file_path = os.path.join(root, file)
                                os.remove(file_path)
                                logging.info(f"已删除图标缓存文件: {file_path}")
                                cleaned_count += 1
                            except Exception as e:
                                logging.warning(f"删除图标缓存文件失败: {file_path}, 错误: {e}")
        
        logging.info(f"图标缓存清理完成，共删除 {cleaned_count} 个文件")
        
    except Exception as e:
        logging.error(f"清理图标缓存时出错: {e}")

def force_restart_explorer():
    """强制重启 Windows Explorer"""
    try:
        print("\n⚠️  正在强制重启 Windows Explorer...")
        print("   这会导致桌面和任务栏暂时消失，请稍等...")
        
        # 终止 Explorer
        subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'], 
                      capture_output=True, timeout=10)
        
        # 等待
        time.sleep(2)
        
        # 重启 Explorer
        subprocess.Popen(['explorer.exe'])
        
        print("✓ Windows Explorer 已重启")
        time.sleep(2)
        
    except Exception as e:
        logging.error(f"重启 Explorer 失败: {e}")
        print(f"重启 Explorer 失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("系统托盘图标清理工具 (强力版)")
    print("用于清理 Bazaar_Lens 遗留的系统托盘图标")
    print("=" * 50)
    print()
    
    try:
        # 步骤1: 清理通知区域图标缓存
        cleanup_notification_area()
        print("✓ 通知区域图标缓存已清理")
        
        # 步骤2: 清理图标缓存文件
        cleanup_icon_cache()
        print("✓ 图标缓存文件已清理")
        
        # 步骤3: 刷新系统托盘
        refresh_system_tray()
        print("✓ 系统托盘已刷新")
        
        print()
        print("=" * 50)
        print("基础清理完成！")
        
        # 询问是否强制重启 Explorer
        print("\n如果遗留图标仍然存在，可以尝试强制重启 Windows Explorer")
        choice = input("是否强制重启 Explorer? (y/n): ").lower().strip()
        
        if choice in ['y', 'yes', '是']:
            force_restart_explorer()
            print("\n" + "=" * 50)
            print("强制清理完成！")
            print("请检查系统托盘区域，遗留图标应该已经消失。")
            print("如果仍有问题，请重启计算机。")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("清理完成！")
            print("请检查系统托盘区域，遗留图标应该已经消失。")
            print("如果仍有遗留图标，请重启计算机。")
            print("=" * 50)
        
    except Exception as e:
        logging.error(f"清理过程中出错: {e}")
        print(f"清理失败: {e}")
        return 1
    
    input("\n按回车键退出...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
