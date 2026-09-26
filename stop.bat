@echo off
title Stop Clash-AI-Watchdog
chcp 65001 >nul

echo Stopping background Clash-AI-Watchdog process...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'main.py --tray|clash_watchdog' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Terminated process PID:' $_.ProcessId }"
echo.
echo [Done] Clash-AI-Watchdog daemon stopped safely.
timeout /t 2 >nul
exit
