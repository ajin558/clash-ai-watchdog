#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog CLI 入口
"""

import sys
import argparse
from clash_watchdog import __version__
from clash_watchdog.core import WatchdogEngine
from clash_watchdog.config import save_example_config

def main():
    parser = argparse.ArgumentParser(
        description=f"Clash-AI-Watchdog v{__version__}: 专为 AI Agent / LLM 开发者打造的智能代理守护与自愈引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--version", action="version", version=f"Clash-AI-Watchdog v{__version__}")
    parser.add_argument("-c", "--config", default="config.json", help="指定配置文件路径 (默认: config.json)")
    parser.add_argument("-t", "--test", action="store_true", help="单次诊断测试模式 (测试当前网络并评估优选节点后退出)")
    parser.add_argument("--tray", action="store_true", help="以系统托盘模式运行 (静默常驻任务栏右下角，无控制台窗口)")
    parser.add_argument("-s", "--service", choices=["gemini", "claude", "openai", "google_204"], help="覆盖监控目标服务")
    parser.add_argument("-r", "--region", help="覆盖首选区域代码，例如: US, SG, JP (逗号分隔)")
    parser.add_argument("-i", "--interval", type=int, help="覆盖探测周期（秒）")
    parser.add_argument("--gen-config", action="store_true", help="在当前目录下生成默认 config.json 配置文件")

    args = parser.parse_args()

    if args.gen_config:
        save_example_config("config.json")
        print("已在当前目录生成默认配置文件: config.json")
        return

    # 托盘模式启动
    if args.tray:
        try:
            from clash_watchdog.tray import TrayApp
            app = TrayApp(config_path=args.config)
            app.run()
            return
        except ImportError:
            print("[错误] 托盘模式需要 pystray 和 Pillow 支持！")
            print("请在终端运行安装: pip install pystray pillow")
            print("正在降级转为控制台模式运行...\n")
        except Exception as e:
            print(f"[错误] 托盘模式启动失败: {e}，转为控制台模式运行...\n")

    overrides = {}
    if args.service:
        overrides["target_service"] = args.service
    if args.region:
        overrides["preferred_regions"] = [r.strip().upper() for r in args.region.split(",") if r.strip()]
    if args.interval:
        overrides["check_interval"] = args.interval

    engine = WatchdogEngine(config_path=args.config, overrides=overrides)

    if args.test:
        engine.run_diagnostics()
    else:
        engine.start()

if __name__ == "__main__":
    main()
