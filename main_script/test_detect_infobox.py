"""
检测游戏中物品信息框区域的测试脚本
信息框特征：深褐色背景，有边框，内部有白色/彩色文字
"""
import os
import sys
import glob
import cv2
import numpy as np
from PIL import Image

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)


def detect_name_region(infobox_img, debug=True):
    """
    在信息框图像中检测物品名称区域
    名称区域特征：
    - 在信息框顶部
    - 下方有一条水平分隔线
    - 背景略深
    
    返回：(x, y, w, h) 名称区域的位置，如果未检测到返回 None
    """
    if len(infobox_img.shape) == 2:
        img_gray = infobox_img
        img_bgr = cv2.cvtColor(infobox_img, cv2.COLOR_GRAY2BGR)
    elif infobox_img.shape[2] == 4:
        img_bgr = cv2.cvtColor(infobox_img, cv2.COLOR_RGBA2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    elif infobox_img.shape[2] == 3:
        img_bgr = cv2.cvtColor(infobox_img, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    else:
        img_bgr = infobox_img
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    height, width = img_gray.shape[:2]
    
    # 方法1：检测水平分隔线
    # 分隔线通常是一条明亮的横线
    
    # 使用Sobel边缘检测，只检测水平方向的边缘
    sobel_x = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel_abs = np.abs(sobel_x).astype(np.uint8)
    
    # 二值化
    _, edge_binary = cv2.threshold(sobel_abs, 30, 255, cv2.THRESH_BINARY)
    
    # 检测水平线：逐行统计白色像素数量
    # 分隔线应该是一条横跨大部分宽度的线
    min_line_width = width * 0.5  # 至少占宽度的50%
    
    potential_lines = []
    for y in range(height):
        white_count = np.sum(edge_binary[y, :] > 0)
        if white_count > min_line_width:
            potential_lines.append((y, white_count))
    
    if debug and potential_lines:
        print(f"  找到 {len(potential_lines)} 条潜在水平线")
    
    # 找到第一条明显的分隔线（从上往下）
    # 名称区域通常在信息框的上部 1/4 到 1/3 位置
    separator_y = None
    search_start = int(height * 0.08)  # 从8%位置开始搜索（跳过顶部边框）
    search_end = int(height * 0.4)    # 到40%位置结束
    
    for y, count in potential_lines:
        if search_start < y < search_end:
            separator_y = y
            if debug:
                print(f"  找到分隔线位置: y={separator_y} (白色像素数: {count})")
            break
    
    if separator_y is None:
        # 方法2：如果没找到明显的分隔线，使用颜色变化检测
        # 名称区域背景较深，内容区域背景较浅
        if debug:
            print("  未找到明显分隔线，使用颜色变化方法")
        
        # 计算每行的平均亮度
        row_brightness = []
        for y in range(height):
            avg = np.mean(img_gray[y, :])
            row_brightness.append(avg)
        
        # 找到亮度变化最大的位置（从上往下）
        max_change = 0
        for y in range(search_start, search_end):
            if y + 5 < height:
                change = abs(row_brightness[y+5] - row_brightness[y])
                if change > max_change:
                    max_change = change
                    separator_y = y
        
        if debug and separator_y:
            print(f"  通过亮度变化找到分隔位置: y={separator_y}")
    
    if separator_y is None:
        # 方法3：使用固定比例
        separator_y = int(height * 0.18)
        if debug:
            print(f"  使用默认比例: y={separator_y} (18%)")
    
    # 名称区域：从顶部到分隔线位置
    # 稍微扩展一点以确保包含完整名称
    name_y = 0
    name_h = separator_y + 5  # 向下多取5像素
    name_x = 0
    name_w = width
    
    # 排除顶部可能的标签区域（如"小型 武器 服饰"）
    # 方法：检测顶部是否有与信息框不同的背景色
    
    # 检查顶部区域的颜色
    top_region = img_bgr[:min(30, height//4), :]
    
    # 转换到HSV检测是否是信息框背景色
    top_hsv = cv2.cvtColor(top_region, cv2.COLOR_BGR2HSV)
    
    # 信息框背景的HSV范围
    lower_bg = np.array([5, 20, 15])
    upper_bg = np.array([35, 180, 100])
    
    # 检测顶部区域中属于信息框背景的像素比例
    mask = cv2.inRange(top_hsv, lower_bg, upper_bg)
    bg_ratio = np.sum(mask > 0) / mask.size
    
    if bg_ratio < 0.3:
        # 顶部不是信息框背景，可能是标签区域
        # 找到信息框真正开始的位置
        if debug:
            print(f"  顶部区域背景比例低 ({bg_ratio:.1%})，检测真正的信息框起始位置")
        
        for y in range(min(80, height//3)):
            row_hsv = cv2.cvtColor(img_bgr[y:y+1, :], cv2.COLOR_BGR2HSV)
            row_mask = cv2.inRange(row_hsv, lower_bg, upper_bg)
            row_bg_ratio = np.sum(row_mask > 0) / row_mask.size
            
            if row_bg_ratio > 0.5:
                name_y = y
                if debug:
                    print(f"  信息框起始位置: y={name_y}")
                break
    
    # 调整名称区域高度
    name_h = separator_y - name_y + 5
    
    if debug:
        print(f"  名称区域: ({name_x}, {name_y}, {name_w}, {name_h})")
    
    return (name_x, name_y, name_w, name_h)


def detect_infobox(img_array, debug=True):
    """
    检测图像中的物品信息框区域
    返回：(x, y, w, h) 信息框的位置和大小，如果未检测到返回 None
    """
    # 转换为BGR格式（OpenCV格式）
    if len(img_array.shape) == 2:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    elif img_array.shape[2] == 4:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    height, width = img_bgr.shape[:2]
    
    # 转换到HSV色彩空间
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # 信息框的深褐色背景特征：
    # - 色调(H): 大约 10-30 (棕色范围)
    # - 饱和度(S): 较低到中等 30-150
    # - 亮度(V): 较低 20-80 (深色)
    
    # 定义深褐色的HSV范围
    lower_brown = np.array([5, 20, 15])
    upper_brown = np.array([35, 180, 100])
    
    # 创建掩码
    mask = cv2.inRange(img_hsv, lower_brown, upper_brown)
    
    # 形态学操作：闭运算填充小孔洞
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # 形态学操作：开运算去除小噪点
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small)
    
    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("  未找到任何轮廓")
        return None, mask
    
    # 过滤轮廓：
    # 1. 面积要足够大（至少占图像的5%）
    # 2. 宽高比要合理（信息框是横向矩形，宽度 > 高度）
    min_area = width * height * 0.03  # 最小面积阈值
    
    valid_boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        
        # 获取边界矩形
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 宽高比检查：信息框通常是宽 > 高
        aspect_ratio = w / h if h > 0 else 0
        
        # 信息框的宽高比大约在 1.2 - 3.0 之间
        if 0.8 < aspect_ratio < 4.0:
            # 计算矩形度（轮廓面积 / 边界矩形面积）
            rect_area = w * h
            rectangularity = area / rect_area if rect_area > 0 else 0
            
            # 信息框应该比较规则，矩形度 > 0.5
            if rectangularity > 0.4:
                valid_boxes.append({
                    'box': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'rectangularity': rectangularity
                })
    
    if not valid_boxes:
        print("  未找到符合条件的信息框")
        return None, mask
    
    # 按面积排序，选择最大的
    valid_boxes.sort(key=lambda x: x['area'], reverse=True)
    
    if debug:
        print(f"  找到 {len(valid_boxes)} 个候选框:")
        for i, box_info in enumerate(valid_boxes[:3]):
            x, y, w, h = box_info['box']
            print(f"    {i+1}. 位置:({x},{y}) 大小:{w}x{h} 面积:{box_info['area']:.0f} 宽高比:{box_info['aspect_ratio']:.2f} 矩形度:{box_info['rectangularity']:.2f}")
    
    best_box = valid_boxes[0]['box']
    return best_box, mask


def test_single_image(image_path, output_dir):
    """测试单张图片的信息框检测"""
    filename = os.path.basename(image_path)
    print(f"\n{'='*60}")
    print(f"测试图片: {filename}")
    print('='*60)
    
    try:
        # 加载图片
        img = Image.open(image_path)
        img_array = np.array(img)
        
        print(f"图片尺寸: {img.size}")
        
        # 检测信息框
        box, mask = detect_infobox(img_array, debug=True)
        
        if box:
            x, y, w, h = box
            print(f"\n✅ 检测到信息框: 位置({x},{y}) 大小({w}x{h})")
            
            # 裁剪信息框区域
            cropped = img_array[y:y+h, x:x+w]
            
            # 在信息框内检测名称区域
            print("\n--- 检测名称区域 ---")
            name_box = detect_name_region(cropped, debug=True)
            
            if name_box:
                nx, ny, nw, nh = name_box
                print(f"✅ 检测到名称区域: 位置({nx},{ny}) 大小({nw}x{nh})")
                
                # 裁剪名称区域
                name_region = cropped[ny:ny+nh, nx:nx+nw]
                name_path = os.path.join(output_dir, f"name_{filename}")
                Image.fromarray(name_region).save(name_path)
                print(f"  名称区域已保存: {name_path}")
            
            # 在原图上绘制检测结果
            img_result = img_array.copy()
            if len(img_result.shape) == 2:
                img_result = cv2.cvtColor(img_result, cv2.COLOR_GRAY2BGR)
            elif img_result.shape[2] == 4:
                img_result = cv2.cvtColor(img_result, cv2.COLOR_RGBA2BGR)
            else:
                img_result = cv2.cvtColor(img_result, cv2.COLOR_RGB2BGR)
            
            # 绘制绿色矩形框（信息框）
            cv2.rectangle(img_result, (x, y), (x+w, y+h), (0, 255, 0), 3)
            
            # 绘制红色矩形框（名称区域）
            if name_box:
                nx, ny, nw, nh = name_box
                cv2.rectangle(img_result, (x+nx, y+ny), (x+nx+nw, y+ny+nh), (0, 0, 255), 2)
            
            # 保存结果图片
            output_path = os.path.join(output_dir, f"detected_{filename}")
            cv2.imwrite(output_path, img_result)
            print(f"  结果已保存: {output_path}")
            
            # 保存信息框裁剪
            cropped_path = os.path.join(output_dir, f"cropped_{filename}")
            Image.fromarray(cropped).save(cropped_path)
            print(f"  信息框已保存: {cropped_path}")
            
            return True
        else:
            print(f"\n❌ 未检测到信息框")
            
            # 保存掩码以便调试
            mask_path = os.path.join(output_dir, f"mask_{filename}")
            cv2.imwrite(mask_path, mask)
            print(f"  掩码已保存: {mask_path}")
            
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("物品信息框检测测试")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = os.path.join(project_root, 'data', 'temp', 'detect_results')
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")
    
    # 获取测试图片
    temp_dir = os.path.join(project_root, 'data', 'temp')
    image_files = glob.glob(os.path.join(temp_dir, 'ocr_region_*.png'))
    
    if not image_files:
        print(f"错误: 没有找到测试图片: {temp_dir}/ocr_region_*.png")
        return
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    # 测试每张图片
    success_count = 0
    total_count = min(len(image_files), 10)
    
    for image_path in image_files[:total_count]:
        if test_single_image(image_path, output_dir):
            success_count += 1
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)
    print(f"测试图片数: {total_count}")
    print(f"检测成功数: {success_count}")
    print(f"检测成功率: {success_count/total_count*100:.1f}%")
    print(f"\n结果保存在: {output_dir}")
    print("  - detected_*.png: 检测结果（绿色框=信息框，红色框=名称区域）")
    print("  - cropped_*.png: 裁剪出的信息框区域")
    print("  - name_*.png: 裁剪出的名称区域（只包含物品名称）")


if __name__ == '__main__':
    main()
