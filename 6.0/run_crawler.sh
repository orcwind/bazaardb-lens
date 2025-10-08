#!/bin/bash

echo "========================================"
echo "Bazaar数据库爬虫系统 v6.0"
echo "========================================"
echo

cd "$(dirname "$0")"

echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python，请先安装Python 3.8+"
    exit 1
fi

echo "检查依赖..."
if ! python3 -c "import selenium" &> /dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo
echo "选择运行模式:"
echo "1. 爬取所有数据（怪物 + 事件）"
echo "2. 只爬取怪物"
echo "3. 只爬取事件"
echo "4. 无头模式爬取所有数据"
echo
read -p "请输入选择 (1-4): " choice

cd crawlers

case $choice in
    1)
        echo
        echo "开始爬取所有数据..."
        python3 main.py
        ;;
    2)
        echo
        echo "开始爬取怪物数据..."
        python3 main.py --type monster
        ;;
    3)
        echo
        echo "开始爬取事件数据..."
        python3 main.py --type event
        ;;
    4)
        echo
        echo "开始无头模式爬取..."
        python3 main.py --headless
        ;;
    *)
        echo "[错误] 无效的选择"
        exit 1
        ;;
esac

cd ..

echo
echo "========================================"
echo "爬取完成！"
echo "========================================"
echo
echo "输出文件位置:"
echo "  data/monsters.json  - 怪物数据"
echo "  data/events.json    - 事件数据"
echo "  icons/skills/       - 技能图标"
echo "  icons/items/        - 物品图标"
echo "  logs/               - 日志文件"
echo




