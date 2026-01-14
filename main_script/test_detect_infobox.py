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
    - 在信息框顶部，包含物品类型标签（如"大型"、"武器"）和物品名称
    - 名称是白色/金色大字
    - 下方有一条金色水平分隔线
    - 分隔线下方是物品描述区域
    
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
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # ========== 方法1：检测金色分隔线 ==========
    # 金色分隔线是最可靠的分界标志
    # 金色 HSV: H=15-35, S=100-255, V=150-255
    lower_gold = np.array([15, 100, 150])
    upper_gold = np.array([35, 255, 255])
    gold_mask = cv2.inRange(img_hsv, lower_gold, upper_gold)
    
    # 逐行统计金色像素，找到金色分隔线
    separator_y = None
    search_start = int(height * 0.10)  # 从10%位置开始搜索
    search_end = int(height * 0.50)    # 到50%位置结束
    
    gold_line_threshold = width * 0.3  # 金色像素至少占宽度的30%
    
    for y in range(search_start, search_end):
        gold_count = np.sum(gold_mask[y, :] > 0)
        if gold_count > gold_line_threshold:
            # 找到金色分隔线
            separator_y = y
            if debug:
                print(f"  找到金色分隔线: y={separator_y} (金色像素数: {gold_count})")
            break
    
    # ========== 方法2：检测水平边缘线（备用） ==========
    if separator_y is None:
        # 使用Sobel边缘检测水平方向的边缘
        sobel_y = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_abs = np.abs(sobel_y).astype(np.uint8)
        _, edge_binary = cv2.threshold(sobel_abs, 30, 255, cv2.THRESH_BINARY)
        
        min_line_width = width * 0.4
        
        for y in range(search_start, search_end):
            white_count = np.sum(edge_binary[y, :] > 0)
            if white_count > min_line_width:
                separator_y = y
                if debug:
                    print(f"  找到边缘分隔线: y={separator_y} (边缘像素数: {white_count})")
                break
    
    # ========== 方法3：检测亮度变化（备用） ==========
    if separator_y is None:
        if debug:
            print("  未找到明显分隔线，使用亮度变化方法")
        
        # 计算每行的平均亮度
        row_brightness = [np.mean(img_gray[y, :]) for y in range(height)]
        
        # 找到亮度变化最大的位置
        max_change = 0
        for y in range(search_start, search_end - 5):
            change = abs(row_brightness[y + 5] - row_brightness[y])
            if change > max_change:
                max_change = change
                separator_y = y
        
        if debug and separator_y:
            print(f"  通过亮度变化找到分隔位置: y={separator_y}")
    
    # ========== 方法4：使用固定比例（最后备用） ==========
    if separator_y is None:
        separator_y = int(height * 0.20)
        if debug:
            print(f"  使用默认比例: y={separator_y} (20%)")
    
    # ========== 确定名称区域的起始位置 ==========
    # 检查顶部是否有标签区域（蓝色/绿色的类型标签）
    name_y = 0
    
    # 检测顶部的深褐色背景开始位置
    lower_brown = np.array([8, 80, 30])
    upper_brown = np.array([25, 200, 100])
    
    for y in range(min(60, height // 4)):
        row_hsv = img_hsv[y:y+1, :]
        brown_mask = cv2.inRange(row_hsv, lower_brown, upper_brown)
        brown_ratio = np.sum(brown_mask > 0) / brown_mask.size if brown_mask.size > 0 else 0
        
        if brown_ratio > 0.3:
            # 找到深褐色背景开始的位置
            name_y = max(0, y - 5)  # 稍微往上扩展一点
            if debug and name_y > 0:
                print(f"  名称区域起始位置: y={name_y}")
            break
    
    # ========== 计算名称区域高度 ==========
    if separator_y <= name_y:
        # 分隔线在起始位置之前，使用默认高度
        if debug:
            print(f"  分隔线位置异常 (separator_y={separator_y}, name_y={name_y})，使用默认高度")
        name_h = min(100, height - name_y)
    else:
        # 名称区域从起始位置到分隔线，稍微扩展
        name_h = separator_y - name_y + 10
    
    # 确保高度合理
    name_h = max(60, min(name_h, height - name_y, 200))
    
    name_x = 0
    name_w = width
    
    if debug:
        print(f"  名称区域: ({name_x}, {name_y}, {name_w}, {name_h})")
    
    return (name_x, name_y, name_w, name_h)


def detect_infobox(img_array, debug=True):
    """
    检测图像中的物品信息框区域
    
    目标：检测包含物品名称（如"冰冻钝器"、"废品场长枪"）的深棕色信息框
    
    信息框特征：
    - 非常深的棕色背景（几乎是黑色带棕色调）
    - 有金色装饰边框
    - 顶部有蓝色/绿色的类型标签（如"大型"、"武器"）
    - 物品名称是白色大字
    
    返回：(x, y, w, h) 信息框的位置和大小，如果未检测到返回 None
    """
    # 转换为BGR格式
    if len(img_array.shape) == 2:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    elif img_array.shape[2] == 4:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    height, width = img_bgr.shape[:2]
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # ========== 检测信息框的深棕色背景 ==========
    # 信息框背景是非常深的棕色，HSV特征：
    # H: 10-25 (棕色/橙色调)
    # S: 50-180 (中等饱和度)
    # V: 20-60 (非常低的亮度，这是关键！)
    
    lower_brown = np.array([8, 40, 15])
    upper_brown = np.array([30, 200, 70])
    brown_mask = cv2.inRange(img_hsv, lower_brown, upper_brown)
    
    # 形态学操作：闭运算填充文字空隙
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    brown_mask = cv2.morphologyEx(brown_mask, cv2.MORPH_CLOSE, kernel)
    
    # 开运算去除小噪点
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
    brown_mask = cv2.morphologyEx(brown_mask, cv2.MORPH_OPEN, kernel_small)
    
    # 查找轮廓
    contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_boxes = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # 信息框面积通常在 30000-300000 之间
        if area < 20000:
            continue
        
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 限制最大尺寸：信息框不会占满整个屏幕
        # 宽度不超过图片的80%，高度不超过图片的60%
        if w > width * 0.8 or h > height * 0.6:
            continue
        
        # 宽高比：信息框是横向矩形，宽高比约 1.3-3.5
        aspect_ratio = w / h if h > 0 else 0
        if not (1.2 < aspect_ratio < 4.0):
            continue
        
        # 矩形度
        rect_area = w * h
        rectangularity = area / rect_area if rect_area > 0 else 0
        if rectangularity < 0.4:
            continue
        
        # 检查区域内是否有白色文字
        roi_gray = img_gray[y:y+h, x:x+w]
        white_mask = roi_gray > 200
        white_ratio = np.sum(white_mask) / white_mask.size
        
        # 必须有白色文字（物品名称）
        if white_ratio < 0.01:
            continue
        
        valid_boxes.append({
            'box': (x, y, w, h),
            'area': area,
            'aspect_ratio': aspect_ratio,
            'rectangularity': rectangularity,
            'white_ratio': white_ratio
        })
    
    if not valid_boxes:
        if debug:
            print("  未找到符合条件的信息框")
        return None, brown_mask
    
    # 评分：优先选择大小适中、矩形度高、白字多的
    for box in valid_boxes:
        # 大小评分：信息框通常在 400-800 像素宽，200-500 像素高
        bx, by, bw, bh = box['box']
        size_score = 1.0
        if bw > 1000 or bh > 600:  # 太大
            size_score = 0.3
        elif bw < 300 or bh < 150:  # 太小
            size_score = 0.5
        
        box['score'] = (
            box['rectangularity'] * 0.35 +
            min(box['white_ratio'] * 10, 0.3) +
            size_score * 0.35
        )
    
    valid_boxes.sort(key=lambda x: x['score'], reverse=True)
    
    if debug:
        print(f"  找到 {len(valid_boxes)} 个候选框:")
        for i, box in enumerate(valid_boxes[:5]):
            bx, by, bw, bh = box['box']
            print(f"    {i+1}. ({bx},{by}) {bw}x{bh} 矩形度:{box['rectangularity']:.2f} "
                  f"白字:{box['white_ratio']:.3f} 评分:{box['score']:.2f}")
    
    return valid_boxes[0]['box'], brown_mask


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
