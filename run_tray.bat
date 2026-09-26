@echo off
title Clash-AI-Watchdog 系统托盘后台启动器
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================================
echo       正在启动 Clash-AI-Watchdog 系统托盘静默模式...
echo ==============================================================
echo.
echo 提示：程序已常驻在任务栏右下角系统托盘（绿色小圆点）。
echo 若未直接看到，请点击任务栏右下角向上箭头 [^] 展开查看。
echo.

start "" pythonw main.py --tray
timeout /t 3 >nul
exit
