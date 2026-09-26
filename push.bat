@echo off
title 推送更新到 GitHub
chcp 65001 >nul
cd /d "%~dp0"

echo 正在推送最新提交到 GitHub...
git push origin main

if errorlevel 1 (
    echo.
    echo [提示] 推送未完成，请检查网络或 GitHub 登录凭据。
) else (
    echo.
    echo [成功] 已成功将最新代码与系统托盘更新推送到 GitHub！
)

echo.
pause
