@echo off
title 停止 Clash-AI-Watchdog 守护进程
chcp 65001 >nul

echo 正在停止后台运行的 Watchdog 进程...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'main.py --tray|clash_watchdog' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host '已关闭进程 PID:' $_.ProcessId }"
echo.
echo [完成] 守护进程已安全关闭！
timeout /t 2 >nul
exit
