#!/usr/bin/env bash
# Clash-AI-Watchdog 启动脚本 (macOS / Linux)

set -e
cd "$(dirname "$0")"

echo "=============================================================="
echo "      Clash-AI-Watchdog: 专为 AI 开发者打造的自愈守护引擎"
echo "=============================================================="

if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 python3，请先安装 Python 3.7+！"
    exit 1
fi

python3 main.py "$@"
