#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""下载Tesseract Best版本语言包"""

import os
import urllib.request
import shutil

def download_tesseract_best():
    """下载Tesseract Best版本的中文语言包"""
    
    # 语言包下载URL
    url = "https://github.com/tesseract-ocr/tessdata_best/raw/main/chi_sim.traineddata"
    
    # 确定保存路径
    # 优先使用项目目录下的Tesseract
    project_tesseract = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR"
    tessdata_dir = os.path.join(project_tesseract, "tessdata")
    
    # 如果项目目录不存在，尝试系统安装目录
    if not os.path.exists(project_tesseract):
        # 常见的系统安装路径
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR",
            r"C:\Program Files (x86)\Tesseract-OCR",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                tessdata_dir = os.path.join(path, "tessdata")
                break
    
    if not os.path.exists(tessdata_dir):
        print(f"错误：找不到tessdata目录")
        print(f"请手动创建目录：{tessdata_dir}")
        return False
    
    # 备份原有文件（如果存在）
    old_file = os.path.join(tessdata_dir, "chi_sim.traineddata")
    backup_file = os.path.join(tessdata_dir, "chi_sim.traineddata.backup")
    
    if os.path.exists(old_file):
        print(f"备份原有语言包...")
        try:
            shutil.copy2(old_file, backup_file)
            print(f"✓ 已备份到: {backup_file}")
        except Exception as e:
            print(f"⚠ 备份失败: {e}")
    
    # 下载文件
    output_file = os.path.join(tessdata_dir, "chi_sim.traineddata")
    
    print(f"\n开始下载Tesseract Best版本中文语言包...")
    print(f"URL: {url}")
    print(f"保存到: {output_file}")
    print(f"文件较大（约50-100MB），请耐心等待...\n")
    
    try:
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded * 100 / total_size, 100)
            print(f"\r下载进度: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end='')
        
        urllib.request.urlretrieve(url, output_file, show_progress)
        print(f"\n\n✓ 下载完成！")
        
        # 检查文件大小
        file_size = os.path.getsize(output_file)
        print(f"文件大小: {file_size / (1024*1024):.2f} MB")
        
        if file_size > 50 * 1024 * 1024:
            print("✓ 这应该是best版本（文件较大）")
        else:
            print("⚠ 文件较小，可能不是best版本")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 下载失败: {e}")
        print("\n请手动下载：")
        print(f"1. 访问: {url}")
        print(f"2. 下载文件到: {tessdata_dir}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Tesseract Best版本语言包下载工具")
    print("=" * 60)
    
    success = download_tesseract_best()
    
    if success:
        print("\n" + "=" * 60)
        print("安装完成！")
        print("=" * 60)
        print("\n现在可以运行 Bazaar_Lens.py 测试OCR识别效果")
    else:
        print("\n" + "=" * 60)
        print("下载失败，请查看上面的错误信息")
        print("=" * 60)
