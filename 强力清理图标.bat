@echo off
title 强力清理系统托盘遗留图标
color 0A

echo.
echo ================================================
echo           强力清理系统托盘遗留图标
echo ================================================
echo.
echo 注意：此脚本会重启 Windows Explorer
echo 桌面和任务栏会暂时消失，请稍等...
echo.

pause

echo.
echo [1/4] 清理注册表中的通知区域缓存...
reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v "IconStreams" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v "PastIconsStream" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TrayNotify" /v "IconStreams" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TrayNotify" /v "PastIconsStream" /f >nul 2>&1
echo ✓ 注册表清理完成

echo.
echo [2/4] 清理图标缓存文件...
if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache.db" (
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache.db" >nul 2>&1
)
if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" (
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
)
echo ✓ 图标缓存清理完成

echo.
echo [3/4] 终止所有 Bazaar_Lens 相关进程...
taskkill /f /im "Bazaar_Lens.exe" >nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Bazaar_Lens*" >nul 2>&1
echo ✓ 相关进程已终止

echo.
echo [4/4] 重启 Windows Explorer...
echo 正在重启 Explorer，桌面会暂时消失...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 2 /nobreak >nul
start explorer.exe
echo ✓ Windows Explorer 已重启

echo.
echo ================================================
echo               清理完成！
echo ================================================
echo.
echo 请检查系统托盘区域，遗留图标应该已经消失。
echo 如果仍有问题，请重启计算机。
echo.

pause
exit

