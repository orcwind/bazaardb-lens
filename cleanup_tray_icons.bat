@echo off
echo 正在清理系统托盘中的遗留图标...
echo.

echo 1. 清理通知区域图标缓存...
powershell -Command "Remove-ItemProperty -Path 'HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify' -Name 'IconStreams' -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify' -Name 'PastIconsStream' -ErrorAction SilentlyContinue; Write-Host 'Notification area icons cache cleared'"

echo.
echo 2. 重启 Windows Explorer...
taskkill /f /im explorer.exe
timeout /t 2 /nobreak >nul
start explorer.exe

echo.
echo 3. 清理图标缓存文件...
if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache.db" (
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache.db"
    echo 已删除 iconcache.db
)

if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" (
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db"
    echo 已删除 thumbcache 文件
)

echo.
echo 4. 清理临时图标文件...
if exist "%TEMP%\*.tmp" (
    del /f /q "%TEMP%\*.tmp"
    echo 已删除临时文件
)

echo.
echo 系统托盘图标清理完成！
echo 请检查系统托盘区域，遗留图标应该已经消失。
echo.
pause
