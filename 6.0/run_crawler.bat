@echo off
chcp 65001 >nul
echo ========================================
echo Bazaar数据库爬虫系统 v6.0
echo ========================================
echo.

cd /d "%~dp0"

echo 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo 检查依赖...
pip show selenium >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo 选择运行模式:
echo 1. 爬取所有数据（怪物 + 事件）
echo 2. 只爬取怪物
echo 3. 只爬取事件
echo 4. 无头模式爬取所有数据
echo.
set /p choice=请输入选择 (1-4): 

cd crawlers

if "%choice%"=="1" (
    echo.
    echo 开始爬取所有数据...
    python main.py
) else if "%choice%"=="2" (
    echo.
    echo 开始爬取怪物数据...
    python main.py --type monster
) else if "%choice%"=="3" (
    echo.
    echo 开始爬取事件数据...
    python main.py --type event
) else if "%choice%"=="4" (
    echo.
    echo 开始无头模式爬取...
    python main.py --headless
) else (
    echo [错误] 无效的选择
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo 爬取完成！
echo ========================================
echo.
echo 输出文件位置:
echo   data\monsters.json  - 怪物数据
echo   data\events.json    - 事件数据
echo   icons\skills\       - 技能图标
echo   icons\items\        - 物品图标
echo   logs\               - 日志文件
echo.
pause







