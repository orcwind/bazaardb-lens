import PyInstaller.__main__
import sys
from version import VERSION

# 将版本号转换为元组格式
version_parts = VERSION.split('.')
version_tuple = tuple(int(part) for part in version_parts) + (0,) * (4 - len(version_parts))

# 更新version_info.txt中的版本号
with open('version_info.txt', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('filevers=(0, 1, 0, 0)', f'filevers={version_tuple}')
content = content.replace('prodvers=(0, 1, 0, 0)', f'prodvers={version_tuple}')
content = content.replace("u'FileVersion', u'0.1.0'", f"u'FileVersion', u'{VERSION}'")
content = content.replace("u'ProductVersion', u'0.1.0'", f"u'ProductVersion', u'{VERSION}'")

with open('version_info.txt', 'w', encoding='utf-8') as f:
    f.write(content)

# PyInstaller参数
args = [
    'Bazaar_Lens.py',
    '--onefile',
    '--windowed',
    '--icon=Bazaar_Lens.ico',
    '--version-file=version_info.txt',
    '--add-data=icons;icons',
    '--add-data=data;data',
]

PyInstaller.__main__.run(args) 