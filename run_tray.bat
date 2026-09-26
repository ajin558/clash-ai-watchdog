@echo off
title Clash-AI-Watchdog 系统托盘后台启动器
cd /d "%~dp0"

echo 正在启动 Clash-AI-Watchdog 系统托盘静默模式...
echo 程序将常驻在任务栏右下角，右键图标可管理或退出。
echo.

start "" pythonw main.py --tray
timeout /t 2 >nul
exit
