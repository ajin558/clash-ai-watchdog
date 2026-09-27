# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 终端沉浸式交互看板 (Interactive TUI)
采用 ANSI / VT100 原生光标复位覆盖渲染，彻底消除 cls 清屏导致的白闪
支持 Unicode Sparkline 微波形走势与 msvcrt 单键非阻塞热键
"""

import sys
import os
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def safe_print(text):
    """防崩打印：在任何控制台编码下保证 Unicode 不抛出 UnicodeEncodeError"""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or 'utf-8'
        sys.stdout.buffer.write(text.encode(enc, errors='replace') + b'\n')
        sys.stdout.buffer.flush()

def safe_write(text):
    """防崩输出：在任何控制台编码下保证 Unicode 不抛出 UnicodeEncodeError"""
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or 'utf-8'
        sys.stdout.buffer.write(text.encode(enc, errors='replace'))
        sys.stdout.buffer.flush()

# ANSI 颜色代码
ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
RED = f"{ESC}31m"
GREEN = f"{ESC}32m"
YELLOW = f"{ESC}33m"
BLUE = f"{ESC}34m"
MAGENTA = f"{ESC}35m"
CYAN = f"{ESC}36m"
WHITE = f"{ESC}37m"
BG_BLUE = f"{ESC}44m"
BG_DARK = f"{ESC}40m"

SPARKLINE_BARS = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

def green(s): return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s): return f"{RED}{s}{RESET}"
def cyan(s): return f"{CYAN}{s}{RESET}"
def bold(s): return f"{BOLD}{s}{RESET}"
def dim(s): return f"{DIM}{s}{RESET}"

def generate_sparkline(values, max_len=15):
    """
    根据最近的延迟数值序列生成 Unicode 迷你折线图
    示例: [120, 150, 180, 300] ->  ▂▃█
    """
    if not values:
        return dim("----------------")
    
    recent = list(values)[-max_len:]
    min_val = min(recent)
    max_val = max(recent)
    
    if max_val == min_val:
        return green("▃" * len(recent))
    
    result = []
    val_range = max_val - min_val
    for v in recent:
        if v <= 0:
            result.append(red("×"))
        else:
            # 归一化到 0 - 7
            idx = int(((v - min_val) / val_range) * 7)
            idx = max(0, min(7, idx))
            bar = SPARKLINE_BARS[idx]
            if v < 250:
                result.append(green(bar))
            elif v < 600:
                result.append(yellow(bar))
            else:
                result.append(red(bar))
                
    return "".join(result)

def check_keypress():
    """
    非阻塞检查键盘按键输入 (Windows 优先)
    返回大写的按键字符，如 'R', 'T', 'P', 'Q'，若无按键则返回 None
    """
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit():
            try:
                ch = msvcrt.getch()
                # 处理功能键/方向键前缀
                if ch in (b'\x00', b'\xe0'):
                    msvcrt.getch()
                    return None
                return ch.decode('utf-8', errors='ignore').upper()
            except Exception:
                return None
    return None

class DashboardRenderer:
    """
    零闪烁交互式看板渲染器
    使用 VT100 光标复位覆盖渲染
    """
    def __init__(self):
        self._first_render = True
        # 尝试隐藏光标
        sys.stdout.write(f"{ESC}?25l")
        sys.stdout.flush()

    def restore_cursor(self):
        """恢复光标可见性"""
        sys.stdout.write(f"{ESC}?25h\n")
        sys.stdout.flush()

    def render_zen(self, state):
        """
        绘制 Zen 极简润物无声状态栏
        双行紧凑常驻更新，清爽护航，绝不干扰用户日常工作
        """
        if self._first_render:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._first_render = False
        else:
            sys.stdout.write(f"{ESC}H")

        current_node = state.get("current_node", "正在检测...")
        current_latency = state.get("current_latency", "--")
        latency_rating = state.get("latency_rating", "")
        status_str = state.get("status_badge", green("🟢 守护中"))
        today_heals = state.get("today_heals", 0)
        service = state.get("service", "GEMINI").upper()
        
        node_disp = current_node[:28]
        heal_str = f" │ 今日自愈: {yellow(str(today_heals) + '次')}" if today_heals > 0 else ""
        
        line1 = f"{CYAN}[🐕 AI-Watchdog]{RESET} {status_str} │ 节点: {bold(node_disp)} ({current_latency} {latency_rating}) │ AI通道: {green('畅通')} ({service}){heal_str}"
        line2 = f"{dim('  [热键] (V) 展开全量看板  │  (R) 立即换线  │  (T) 链路自检  │  (P) 暂停  │  (Q) 退出')}"
        
        output = f"{line1}\033[K\n{line2}\033[K\n\033[J"
        safe_write(output)

    def render(self, state):
        """
        绘制完整仪表盘面板
        state 字典包含当前所有运行态指标
        """
        # 初次绘制先清屏，后续仅光标置顶覆盖，实现 0 白闪
        if self._first_render:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._first_render = False
        else:
            # 光标复位到第 1 行第 1 列
            sys.stdout.write(f"{ESC}H")

        status_str = state.get("status_badge", green("[🟢 正常监控]"))
        health_rate = state.get("health_rate", "100.0%")
        check_interval = state.get("check_interval", 30)
        mixed_proxy = state.get("mixed_proxy", "7897")
        service = state.get("service", "GEMINI").upper()
        current_node = state.get("current_node", "正在检测...")
        current_latency = state.get("current_latency", "--")
        latency_rating = state.get("latency_rating", "")
        sparkline = state.get("sparkline", "")
        avg_latency = state.get("avg_latency", "--")
        multi_probe = state.get("multi_probe", {})
        today_heals = state.get("today_heals", 0)
        last_heal_info = state.get("last_heal_info", "暂无切线事件")
        quarantine_nodes = state.get("quarantine_nodes", [])
        recent_logs = state.get("recent_logs", [])

        width = 82
        border_top    = f"{CYAN}╔{'═' * (width - 2)}╗{RESET}"
        border_mid    = f"{CYAN}╠{'═' * (width - 2)}╣{RESET}"
        border_bottom = f"{CYAN}╚{'═' * (width - 2)}╝{RESET}"
        divider       = f"{DIM}{'─' * width}{RESET}"

        lines = []
        lines.append(border_top)
        
        # 标题栏
        title_content = f"  🐕 {BOLD}CLASH-AI-WATCHDOG v2.0{RESET}           {status_str}   {dim(f'可用率: {health_rate}')}"
        lines.append(f"{CYAN}║{RESET}{title_content:<{width + 12}}{CYAN}║{RESET}")
        
        sub_content = f"  模式: {cyan(service)} 靶向守护     周期: {yellow(str(check_interval) + 's')}    代理: {cyan(mixed_proxy)}"
        lines.append(f"{CYAN}║{RESET}{sub_content:<{width + 18}}{CYAN}║{RESET}")
        lines.append(border_bottom)
        lines.append("")

        # 实时通路段
        lines.append(f"  {BOLD}【实时代理通路】{RESET}")
        node_disp = current_node[:36]
        lines.append(f"  当前活动节点 : {bold(node_disp):<40} 实时延迟: {current_latency} {latency_rating}")
        lines.append(f"  延迟微波走势 : {sparkline}  {dim(f'(近15次心跳均值: {avg_latency})')}")
        
        # 三路 AI 探测状态
        probe_items = []
        for name in ["Gemini", "Claude", "OpenAI"]:
            p = multi_probe.get(name.lower())
            if p:
                stat = green(f"{p}ms 🟢") if isinstance(p, int) and p < 2000 else red("异常 🔴")
            else:
                stat = dim("--")
            probe_items.append(f"[{name}: {stat}]")
        lines.append(f"  三路端点状态 : {'  '.join(probe_items)}")
        lines.append("")

        # 自愈与安全池
        lines.append(f"  {BOLD}【自愈与安全池】{RESET}")
        lines.append(f"  自愈核心防御 : {cyan('斩断僵尸连接 (DELETE /connections)')} · {green('严防香港/大陆 400 锁区')}")
        lines.append(f"  今日自愈累计 : {yellow(str(today_heals) + ' 次')}  {dim(f'({last_heal_info})')}")
        
        if quarantine_nodes:
            q_str = red(f"{len(quarantine_nodes)} 个节点冷却中: " + ", ".join(quarantine_nodes[:2]))
        else:
            q_str = green("无故障隔离节点 (全线健康)")
        lines.append(f"  故障隔离冷却 : {q_str}")
        lines.append("")

        # 最近日志
        lines.append(divider)
        lines.append(f"  {BOLD}【最近事件记录】{RESET}")
        if recent_logs:
            for log_entry in recent_logs[-3:]:
                lines.append(f"  {dim(log_entry)}")
        else:
            lines.append(f"  {dim('  暂无历史日志')}")
            lines.append(f"  {dim('  正在等待心跳探测...')}")
            lines.append(f"  {dim('  ...')}")

        # 底部快捷键
        lines.append(divider)
        hotkeys = f"  {BOLD}[快捷键]{RESET} {cyan('(V)')} 收起为极简  │  {green('(R)')} 立即换线  │  {yellow('(T)')} 链路自检  │  {cyan('(P)')} 暂停/继续  │  {red('(Q)')} 安全退出"
        lines.append(hotkeys)
        lines.append(divider)

        # 整体输出
        safe_write("\n".join(lines) + "\n")

def log(msg, level="INFO"):
    """基础日志输出（用于测试模式或退化场景）"""
    t = time.strftime("%H:%M:%S")
    if level == "SUCCESS":
        prefix = green("[SUCCESS]")
    elif level == "WARN":
        prefix = yellow("[WARN]   ")
    elif level == "ERROR":
        prefix = red("[ERROR]  ")
    else:
        prefix = cyan("[INFO]   ")
    safe_print(f"{dim(t)} {prefix} {msg}")
