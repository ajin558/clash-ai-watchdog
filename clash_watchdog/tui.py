# -*- coding: utf-8 -*-
"""
控制台终端渲染与格式化输出模块 (TUI)
兼容原生 CMD / PowerShell / Linux 终端，自动处理字符集与 ANSI 彩色渲染
"""

import sys
import os
from datetime import datetime

# Windows 终端 UTF-8 兼容性强化
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 简单的 ANSI 颜色支持
USE_COLOR = os.name != "nt" or "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") is not None or "ANSICON" in os.environ

def _color(text, code):
    if USE_COLOR:
        return f"\033[{code}m{text}\033[0m"
    return text

def green(t): return _color(t, "32")
def yellow(t): return _color(t, "33")
def red(t): return _color(t, "31")
def cyan(t): return _color(t, "36")
def gray(t): return _color(t, "90")
def bold(t): return _color(t, "1")

BANNER = r"""
   _____ _           _              _____  __          __   _       _         _             
  / ____| |         | |       /\   |_   _| \ \        / /  | |     | |       | |            
 | |    | | __ _ ___| |__    /  \    | |    \ \  /\  / /_ _| |_ ___| |__   __| | ___   __ _ 
 | |    | |/ _` / __| '_ \  / /\ \   | |     \ \/  \/ / _` | __/ __| '_ \ / _` |/ _ \ / _` |
 | |____| | (_| \__ \ | | |/ ____ \ _| |_     \  /\  / (_| | || (__| | | | (_| | (_) | (_| |
  \_____|_|\__,_|___/_| |_/_/    \_\_____|     \/  \/ \__,_|\__\___|_| |_|\__,_|\___/ \__, |
                                                                                        __/ |
                                                                                       |___/ 
"""

def print_banner(service, check_interval, proxy, api, regions):
    print(cyan(BANNER))
    print(bold("=" * 76))
    print(f"  {bold('核心状态')}: 活跃守护中")
    print(f"  {bold('监控目标')}: {green(service.upper())} ({check_interval}s 心跳)")
    print(f"  {bold('代理通道')}: {gray(proxy)}  |  {bold('API 控制')}: {gray(api)}")
    print(f"  {bold('优先区域')}: {yellow(', '.join(regions))}")
    print(bold("=" * 76))
    print()

def log(msg, level="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    time_str = gray(f"[{now}]")
    if level == "SUCCESS":
        badge = green("[  OK  ]")
    elif level == "WARN":
        badge = yellow("[ WARN ]")
    elif level == "ERROR":
        badge = red("[ FAIL ]")
    else:
        badge = cyan("[ INFO ]")
    print(f"{time_str} {badge} {msg}", flush=True)
