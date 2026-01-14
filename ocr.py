"""
OCR功能模块
"""
import io
import logging
import traceback
from PIL import Image
import pytesseract


def ocr_task(img_bytes):
    """OCR任务函数（用于进程池）"""
    try:
        # 使用全局设置的tesseract_cmd路径
        img = Image.open(io.BytesIO(img_bytes))
        # 使用标准版本（tessdata_fast中没有chi_sim_fast）
        # 使用PSM 6（统一文本块）和OEM 3（LSTM引擎）以获得最佳速度和准确率平衡
        return pytesseract.image_to_string(
            img,
            config='--psm 6 --oem 3 -l chi_sim'
        ).strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"


def direct_ocr(img_bytes, psm=6, paddle_ocr=None):
    """直接在当前线程执行OCR，使用Tesseract"""
    try:
        img = Image.open(io.BytesIO(img_bytes))

        # 使用Tesseract OCR
        # 使用PSM 6（统一文本块）和OEM 3（LSTM引擎）以获得最佳速度和准确率平衡
        ocr_text = pytesseract.image_to_string(
            img,
            config=f'--psm {psm} --oem 3 -l chi_sim'
        ).strip()

        if ocr_text:
            logging.debug(f"[Tesseract] 识别成功: {repr(ocr_text[:100])}")
            return ocr_text if ocr_text else None
    except Exception as e:
        logging.error(f"direct_ocr错误: {e}")
        logging.error(traceback.format_exc())
        return None
