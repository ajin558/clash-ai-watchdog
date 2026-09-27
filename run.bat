@echo off
chcp 65001 >nul
title Clash-AI-Watchdog v2.0
cd /d "%~dp0"
python main.py %*
echo.
echo Process exited with code %errorlevel%.
pause
