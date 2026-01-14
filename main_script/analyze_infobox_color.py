"""
分析信息框区域的颜色值，用于确定正确的HSV范围
"""
import os
import cv2
import numpy as np
from PIL import Image

def analyze_region_color(image_path, regions):
    """
    分析指定区域的HSV颜色值
    regions: [(x, y, w, h, name), ...] 要分析的区域列表
    """
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # 转换为BGR
    if len(img_array.shape) == 2:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    elif img_array.shape[2] == 4:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 转换到HSV
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    print(f"\n分析图片: {os.path.basename(image_path)}")
    print(f"图片尺寸: {img_array.shape[:2]}")
    print("="*60)
    
    for x, y, w, h, name in regions:
        region_hsv = img_hsv[y:y+h, x:x+w]
        region_bgr = img_bgr[y:y+h, x:x+w]
        
        # 计算HSV统计值
        h_vals = region_hsv[:, :, 0].flatten()
        s_vals = region_hsv[:, :, 1].flatten()
        v_vals = region_hsv[:, :, 2].flatten()
        
        # 计算BGR统计值
        b_vals = region_bgr[:, :, 0].flatten()
        g_vals = region_bgr[:, :, 1].flatten()
        r_vals = region_bgr[:, :, 2].flatten()
        
        print(f"\n区域 '{name}' - 位置({x},{y}) 大小({w}x{h}):")
        print(f"  HSV 范围:")
        print(f"    H: min={h_vals.min()}, max={h_vals.max()}, mean={h_vals.mean():.1f}, median={np.median(h_vals):.1f}")
        print(f"    S: min={s_vals.min()}, max={s_vals.max()}, mean={s_vals.mean():.1f}, median={np.median(s_vals):.1f}")
        print(f"    V: min={v_vals.min()}, max={v_vals.max()}, mean={v_vals.mean():.1f}, median={np.median(v_vals):.1f}")
        print(f"  BGR 范围:")
        print(f"    B: min={b_vals.min()}, max={b_vals.max()}, mean={b_vals.mean():.1f}")
        print(f"    G: min={g_vals.min()}, max={g_vals.max()}, mean={g_vals.mean():.1f}")
        print(f"    R: min={r_vals.min()}, max={r_vals.max()}, mean={r_vals.mean():.1f}")


def main():
    # 设置路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    temp_dir = os.path.join(project_root, 'data', 'temp')
    
    # 分析第一张图片 - 信息框在上方中间
    # 根据原图，"冰冻钝器" 信息框大约在 (660, 20) 到 (1100, 320) 的位置
    image1 = os.path.join(temp_dir, 'ocr_region_20260114_202345_929.png')
    if os.path.exists(image1):
        # 手动指定信息框背景区域（根据原图观察）
        regions1 = [
            (700, 40, 400, 50, "信息框标题背景"),      # 标题区域
            (700, 100, 400, 150, "信息框内容背景"),    # 内容区域
            (200, 400, 200, 200, "游戏场景背景1"),     # 游戏背景对比
            (1500, 300, 200, 200, "游戏场景背景2"),    # 游戏背景对比
        ]
        analyze_region_color(image1, regions1)
    
    # 分析第二张图片 - 信息框在左侧
    image2 = os.path.join(temp_dir, 'ocr_region_20260114_202725_806.png')
    if os.path.exists(image2):
        # "废品场长枪" 信息框大约在 (300, 430) 到 (750, 720) 的位置
        regions2 = [
            (350, 470, 350, 50, "信息框标题背景"),     # 标题区域
            (350, 530, 350, 150, "信息框内容背景"),    # 内容区域
            (900, 300, 200, 200, "游戏场景背景"),      # 游戏背景对比
        ]
        analyze_region_color(image2, regions2)
    
    # 分析第三张图片
    image3 = os.path.join(temp_dir, 'ocr_region_20260114_202902_633.png')
    if os.path.exists(image3):
        # 根据之前看到的图片，信息框在右侧
        regions3 = [
            (910, 510, 300, 50, "信息框标题背景"),
            (910, 570, 300, 150, "信息框内容背景"),
        ]
        analyze_region_color(image3, regions3)


if __name__ == '__main__':
    main()
