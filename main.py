#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 入口命令行启动器
"""

import sys
import argparse
from watchdog.core import WatchdogEngine
from watchdog.config import save_example_config

def main():
    parser = argparse.ArgumentParser(
        description="Clash-AI-Watchdog: 专为 AI Agent / LLM 开发者打造的智能代理守护与自愈引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-c", "--config", default="config.json", help="指定配置文件路径 (默认: config.json)")
    parser.add_argument("-t", "--test", action="store_true", help="单次诊断测试模式 (测试当前网络并评估优选节点后退出)")
    parser.add_argument("-s", "--service", choices=["gemini", "claude", "openai", "google_204"], help="覆盖监控目标服务")
    parser.add_argument("-r", "--region", help="覆盖首选区域代码，例如: US, SG, JP (逗号分隔)")
    parser.add_argument("-i", "--interval", type=int, help="覆盖探测周期（秒）")
    parser.add_argument("--gen-config", action="store_true", help="在当前目录下生成默认 config.json 配置文件")

    args = parser.parse_args()

    if args.gen_config:
        save_example_config("config.json")
        print("已在当前目录生成默认配置文件: config.json")
        return

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
