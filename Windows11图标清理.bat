@echo off
title Windows 11 系统托盘图标清理
color 0B

echo.
echo ================================================
echo        Windows 11 系统托盘图标清理工具
echo ================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 错误：需要管理员权限运行此脚本！
    echo 请右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo 检测到管理员权限，开始清理...
echo.

echo [步骤 1] 清理 Windows 11 通知区域缓存...
:: Windows 11 的特殊注册表路径
reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TrayNotify" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FlyoutMenuSettings" /f >nul 2>&1
echo ✓ Windows 11 通知区域缓存已清理

echo.
echo [步骤 2] 清理 Windows 11 图标缓存...
:: Windows 11 的图标缓存位置
if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer" (
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\*.db" >nul 2>&1
    del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\*.tmp" >nul 2>&1
)
if exist "%LOCALAPPDATA%\IconCache.db" (
    del /f /q "%LOCALAPPDATA%\IconCache.db" >nul 2>&1
)
echo ✓ Windows 11 图标缓存已清理

echo.
echo [步骤 3] 清理 Windows 11 缩略图缓存...
if exist "%LOCALAPPDATA%\Microsoft\Windows\Explorer" (
    for /f "delims=" %%i in ('dir /b "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" 2^>nul') do (
        del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\%%i" >nul 2>&1
    )
)
echo ✓ 缩略图缓存已清理

echo.
echo [步骤 4] 终止所有相关进程...
taskkill /f /im "Bazaar_Lens.exe" >nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Bazaar_Lens*" >nul 2>&1
echo ✓ 相关进程已终止

echo.
echo [步骤 5] 重启 Windows 11 资源管理器...
echo 警告：桌面和任务栏会暂时消失，请稍等...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 3 /nobreak >nul
start explorer.exe
timeout /t 2 /nobreak >nul
echo ✓ Windows 11 资源管理器已重启

echo.
echo [步骤 6] 刷新 Windows 11 系统托盘...
:: 发送刷新消息给系统托盘
powershell -Command "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Win32 { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName); [DllImport(\"user32.dll\")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam); }'; $tray = [Win32]::FindWindow('Shell_TrayWnd', $null); if($tray -ne [IntPtr]::Zero) { [Win32]::PostMessage($tray, 0x111, [IntPtr]419, [IntPtr]::Zero) }" >nul 2>&1
echo ✓ 系统托盘已刷新

echo.
echo ================================================
echo              Windows 11 清理完成！
echo ================================================
echo.
echo 请检查系统托盘区域，遗留图标应该已经消失。
echo 如果仍有问题，建议重启计算机。
echo.

echo 按任意键退出...
pause >nul
exit /b 0
