# Tesseract OCR Best版本安装指南

## 一、下载Tesseract Best版本

### Windows版本下载：

1. **官方GitHub仓库**：
   - 访问：https://github.com/UB-Mannheim/tesseract/wiki
   - 下载最新版本的Windows安装包（推荐5.x版本）

2. **直接下载链接**（示例，请检查最新版本）：
   ```
   https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.x.x.exe
   ```

### 语言包下载（Best版本）：

1. **Tessdata Best版本**（高精度语言包）：
   - 访问：https://github.com/tesseract-ocr/tessdata_best
   - 下载 `chi_sim.traineddata`（简体中文best版本）

2. **直接下载链接**：
   ```
   https://github.com/tesseract-ocr/tessdata_best/raw/main/chi_sim.traineddata
   ```

## 二、安装步骤

### 1. 安装Tesseract OCR

1. 运行下载的安装程序
2. 安装路径建议：`C:\Program Files\Tesseract-OCR` 或项目目录下的 `Tesseract-OCR`
3. **重要**：安装时选择安装简体中文语言包（虽然这是标准版本，但先安装）

### 2. 替换为Best版本语言包

1. 找到Tesseract的tessdata目录：
   - 通常在：`C:\Program Files\Tesseract-OCR\tessdata`
   - 或：`你的安装路径\Tesseract-OCR\tessdata`

2. 备份原有的 `chi_sim.traineddata`（可选）

3. 将下载的 `chi_sim.traineddata`（best版本）复制到tessdata目录

4. 如果使用项目便携版Tesseract：
   - 路径：`D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tessdata`
   - 同样替换 `chi_sim.traineddata`

### 3. 验证安装

运行以下Python代码验证：

```python
import pytesseract
import os

# 设置Tesseract路径
tesseract_path = r"D:\PythonProject\BazaarInfo\bazaardb-desktop\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# 检查语言包
tessdata_dir = os.path.join(os.path.dirname(tesseract_path), 'tessdata')
chi_sim_path = os.path.join(tessdata_dir, 'chi_sim.traineddata')

if os.path.exists(chi_sim_path):
    file_size = os.path.getsize(chi_sim_path)
    print(f"✓ 找到中文语言包: {chi_sim_path}")
    print(f"  文件大小: {file_size / (1024*1024):.2f} MB")
    # Best版本通常大于50MB，标准版本约10-20MB
    if file_size > 50 * 1024 * 1024:
        print("  ✓ 这可能是best版本（文件较大）")
    else:
        print("  ⚠ 这可能是标准版本（文件较小）")
else:
    print("✗ 未找到中文语言包")
```

## 三、Best版本 vs 标准版本

| 特性 | 标准版本 | Best版本 |
|------|---------|---------|
| 文件大小 | ~10-20 MB | ~50-100 MB |
| 识别准确率 | 较高 | 最高 |
| 识别速度 | 较快 | 稍慢 |
| 适用场景 | 一般用途 | 高精度需求 |

## 四、使用Best版本的代码配置

代码已经自动检测best版本，如果存在会自动使用。你也可以手动指定：

```python
# 在Bazaar_Lens.py中，ocr_for_game方法已经支持best版本
# 它会自动检测tessdata目录中的语言包
```

## 五、性能优化建议

1. **如果Best版本太慢**：
   - 可以保留标准版本用于快速识别
   - Best版本用于需要高精度的场景

2. **混合使用**：
   - 怪物名称（短文本）：使用标准版本 + fast模式
   - 事件描述（长文本）：使用best版本 + balanced模式

## 六、常见问题

### Q: Best版本识别速度慢怎么办？
A: 可以：
1. 使用fast模式（PSM 7）
2. 减少图像尺寸
3. 使用标准版本进行快速识别，best版本用于验证

### Q: 如何同时保留两个版本？
A: 可以：
1. 安装两个Tesseract实例
2. 或使用不同的tessdata目录
3. 在代码中根据场景选择

### Q: Best版本文件太大？
A: Best版本确实较大，但识别准确率显著提升，特别是对于：
- 带阴影的文字
- 复杂背景
- 小字体
- 艺术字体
