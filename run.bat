@echo off
title Clash-AI-Watchdog 代理智能守护系统
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================================
echo       Clash-AI-Watchdog: 专为 AI 开发者打造的自愈守护引擎
echo ==============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 环境，请先安装 Python 3.7+ 并添加到系统 PATH！
    pause
    exit /b 1
)

python main.py %*
pause
