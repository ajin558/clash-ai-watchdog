# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 核心引擎与主调度器 (Core Engine v2.0)
功能特性：
1. 内核级单实例互斥锁 (防多开冲突)
2. 零闪烁终端交互式动态仪表盘 (VT100 ANSI 光标复位)
3. 毫秒级单键热键响应 (R 立即换线, T 自检, P 暂停, Q 退出)
4. 故障隔离冷却池 (Quarantine Pool) 与抗震荡防抖
5. 异步探活线程，UI 始终流畅无卡顿
"""

import sys
import time
import threading
from collections import deque
from .config import load_config
from .clash_client import ClashClient
from .probe import Probe
from .selector import NodeSelector
from .notifier import Notifier
from .system import SingleInstance, enable_vt100_support
from .tui import (
    DashboardRenderer, generate_sparkline, check_keypress,
    green, yellow, red, cyan, bold, dim, log
)

class WatchdogEngine:
    def __init__(self, config_path="config.json", overrides=None):
        self.cfg = load_config(config_path)
        if overrides:
            self.cfg.update(overrides)

        self.mutex = SingleInstance("ClashAIWatchdog_Instance")
        self.clash = ClashClient(
            api_base=self.cfg.get("clash_api_base", "auto"),
            secret=self.cfg.get("clash_secret", ""),
            mixed_proxy=self.cfg.get("mixed_proxy", "auto")
        )
        self.notifier = Notifier(self.cfg.get("notifications", {}))
        self.probe = None
        self.selector = None

        # 运行态指标与状态追踪
        self.ui_mode = self.cfg.get("ui_mode", "zen")
        self.running = False
        self.paused = False
        self.current_node = "正在获取..."
        self.current_latency = "--"
        self.current_latency_val = 0
        self.latency_rating = ""
        self.latencies = deque(maxlen=30)
        self.recent_logs = deque(maxlen=5)
        self.today_heals = 0
        self.last_heal_info = "暂无换线记录"
        self.total_checks = 0
        self.success_checks = 0
        self.multi_probe = {}
        self.consecutive_fails = 0
        self.is_healing = False

    def add_log(self, text, level="INFO"):
        t = time.strftime("%H:%M:%S")
        entry = f"[{t}] [{level:4s}] {text}"
        self.recent_logs.append(entry)

    def initialize(self):
        """探测并绑定 Clash 客户端与网络组件"""
        self.add_log("正在连接本地 Clash / Mihomo 控制端...", "INFO")
        if not self.clash.discover():
            self.add_log("未发现运行中的 Clash 控制端，请确认开启 External Controller", "ERROR")
            return False

        self.add_log(f"成功连接 Clash 控制端 ({self.clash.api_base})", "INFO")

        self.probe = Probe(
            service=self.cfg.get("target_service", "gemini"),
            custom_url=self.cfg.get("custom_target_url", ""),
            mixed_proxy=self.clash.mixed_proxy,
            timeout=self.cfg.get("check_timeout", 8)
        )

        self.selector = NodeSelector(
            clash_client=self.clash,
            preferred_regions=self.cfg.get("preferred_regions", ["TW", "JP", "SG", "KR", "US", "DE", "UK"]),
            blacklisted_keywords=self.cfg.get("blacklisted_keywords", []),
            priority_keywords=self.cfg.get("priority_keywords", None),
            quarantine_duration=self.cfg.get("quarantine_seconds", 600)
        )

        # 获取当前选中的节点名称
        self._refresh_current_node()
        return True

    def _refresh_current_node(self):
        try:
            proxies = self.clash.get_proxies()
            target_groups = self.cfg.get("target_groups", ["GLOBAL", "节点选择", "PROXY", "Auto", "代理"])
            for g in target_groups:
                if g in proxies and "now" in proxies[g]:
                    self.current_node = proxies[g]["now"]
                    return self.current_node
        except Exception:
            pass
        return self.current_node

    def heal(self, trigger_reason="心跳探测超时"):
        """执行换线自愈流程 (瀑布流真机 TLS 验真)"""
        if self.is_healing:
            return False

        self.is_healing = True
        self.add_log(f"触发自愈换线 (原因: {trigger_reason})", "WARN")
        self.notifier.beep(800, 200)

        # 将当前故障节点加入隔离冷却池（10分钟冷却）
        failed_node = self.current_node
        if failed_node and failed_node != "正在获取...":
            self.selector.quarantine_node(failed_node, reason=trigger_reason)
            self.add_log(f"已将故障节点 [{failed_node[:18]}] 放入 10 分钟隔离池", "WARN")

        proxies = self.clash.get_proxies()
        if not proxies:
            self.add_log("获取 Clash 节点列表失败，自愈中止", "ERROR")
            self.is_healing = False
            return False

        # 获取 Top 5 优质候选节点（专线加权优先，已排除直连与故障隔离节点）
        candidates = self.selector.get_top_candidates(
            proxies,
            test_url=self.probe.target_url,
            limit=5
        )

        if not candidates:
            self.add_log("全网无可用合规候选节点，自愈未完成", "ERROR")
            self.is_healing = False
            return False

        target_groups = self.cfg.get("target_groups", ["GLOBAL", "节点选择", "PROXY", "Auto", "代理"])
        valid_target_groups = [g for g in target_groups if g in proxies]
        if not valid_target_groups:
            self.add_log("未找到可切换的托管策略组", "WARN")
            self.is_healing = False
            return False

        # 核心：瀑布流真机 TLS 验真机制 (Waterfall True-Verification)
        healed_node = None
        healed_delay = 0
        healed_region = ""

        for candidate_name, candidate_delay, candidate_region in candidates:
            # 1. 切换所有相关策略组到候选节点
            switched = False
            for group in valid_target_groups:
                if self.clash.switch_proxy(group, candidate_name):
                    switched = True

            if not switched:
                continue

            # 2. 斩断所有活动 TCP 链路，使死连接瞬间得到 RST/Close 信号
            self.clash.close_all_connections()
            time.sleep(0.3)  # 给 Clash 内核 300ms 刷新连接表与路由

            # 3. 极速真机 TLS 握手核验 (2.5秒超时)
            # 通过本地代理端口向目标 AI 服务做真实握手，彻底杜绝“假绿节点”与 GFW SNI 阻断
            alive, verify_res = self.probe.quick_tls_check(timeout=2.5)
            if alive:
                healed_node = candidate_name
                healed_delay = verify_res if isinstance(verify_res, int) else candidate_delay
                healed_region = candidate_region
                break
            else:
                # 握手失败（被墙掐断或超时），直接判定为虚假节点，放入隔离池并顺延尝试下一个
                self.selector.quarantine_node(candidate_name, reason=f"TLS握手阻断: {verify_res}")
                self.add_log(f"候选 [{candidate_name[:14]}] 真实TLS阻断，顺延切换下一个...", "WARN")

        if healed_node:
            self.current_node = healed_node
            self.today_heals += 1
            self.consecutive_fails = 0
            t_now = time.strftime("%H:%M")
            self.last_heal_info = f"{t_now} 成功切至 [{healed_region}] {healed_node[:14]} (真实延迟: {healed_delay}ms)"
            self.add_log(f"自愈成功 -> [{healed_region}] {healed_node[:16]} ({healed_delay}ms, 真实通畅)", "INFO")
            self.notifier.notify_healed(None, healed_node, healed_delay, healed_region)
            self.is_healing = False
            return True
        else:
            self.add_log("瀑布流候选节点均未通过真机 TLS 验证，请检查机场订阅有效性", "ERROR")
            self.is_healing = False
            return False

    def run_diagnostics(self):
        """执行单次完整自检与测速诊断 (支持独立 CLI --test 模式与运行时热键触发)"""
        if not self.probe:
            if not self.initialize():
                log("初始化连接 Clash 失败，请检查客户端是否开启 External Controller", "ERROR")
                return False

        log("--- 开始全面网络与节点自检 ---", "INFO")
        alive, result = self.probe.check()
        if alive:
            self.current_latency = f"{result}ms"
            self.current_latency_val = result
            log(f"主端点 ({self.probe.service.upper()}) 响应正常: {result}ms", "SUCCESS")
        else:
            self.current_latency = "失败"
            log(f"主端点检测异常: {result}", "WARN")

        # 测三路 AI 端点
        log("并发探测三路主要 AI 接口 (Gemini / Claude / OpenAI)...", "INFO")
        self.multi_probe = self.probe.check_all_services()
        for svc, ms in self.multi_probe.items():
            if ms:
                log(f"  [{svc.upper():6s}] 通畅: {ms}ms", "SUCCESS")
            else:
                log(f"  [{svc.upper():6s}] 不可达 / 握手超时", "WARN")

        # 节点测速评估
        proxies = self.clash.get_proxies()
        best_node, delay, region = self.selector.select_best_node(
            proxies,
            test_url=self.probe.target_url
        )
        if best_node:
            log(f"当前最推荐合规节点 -> [{region}] {best_node} (延迟: {delay}ms)", "SUCCESS")
        else:
            log("未能筛选出可用合规节点，请检查区域配置或黑名单", "WARN")

        self._refresh_current_node()
        log(f"当前活动策略节点: {self.current_node}", "INFO")
        log("--- 自检完成 ---", "INFO")
        return True

    def start(self):
        """启动交互式动态仪表盘主循环"""
        # 1. 检查单实例互斥锁
        if not self.mutex.acquire():
            print("\n" + yellow("=================================================================="))
            print(yellow("  [提示] 检测到已有 Clash-AI-Watchdog 守护进程在后台运行中！"))
            print(yellow("  为防止多实例争抢冲突，本次启动已安全退出。"))
            print(yellow("==================================================================\n"))
            return

        enable_vt100_support()

        if not self.initialize():
            self.mutex.release()
            return

        renderer = DashboardRenderer()
        self.running = True

        interval = self.cfg.get("check_interval", 30)
        max_fails = self.cfg.get("max_fail_count", 2)
        service = self.cfg.get("target_service", "gemini")

        last_check_time = 0
        last_multi_probe_time = 0
        last_render_time = 0
        needs_render = True

        try:
            while self.running:
                now = time.time()

                # --- 1. 热键检测 ---
                key = check_keypress()
                if key:
                    needs_render = True
                    if key == 'Q':
                        self.add_log("用户按下 Q 键，正在安全退出...", "INFO")
                        break
                    elif key == 'V':
                        self.ui_mode = "zen" if self.ui_mode == "dashboard" else "dashboard"
                        renderer._first_render = True
                        os.system('cls' if os.name == 'nt' else 'clear')
                    elif key == 'R':
                        self.add_log("用户按下 R 键，立即触发手动换线...", "INFO")
                        threading.Thread(target=self.heal, args=("手动触发换线",), daemon=True).start()
                    elif key == 'T':
                        self.add_log("用户按下 T 键，立即触发链路自检...", "INFO")
                        threading.Thread(target=self.run_diagnostics, daemon=True).start()
                    elif key == 'P':
                        self.paused = not self.paused
                        status_msg = "已暂停守护" if self.paused else "已恢复守护"
                        self.add_log(f"用户按下 P 键，{status_msg}", "INFO")

                # --- 2. 探活心跳检测 ---
                if not self.paused and (now - last_check_time >= interval):
                    last_check_time = now
                    
                    def _async_probe():
                        self.total_checks += 1
                        alive, res = self.probe.check()
                        if alive:
                            self.consecutive_fails = 0
                            self.success_checks += 1
                            self.current_latency = f"{res}ms"
                            self.current_latency_val = res
                            self.latencies.append(res)
                            if res < 200:
                                self.latency_rating = green("[极佳]")
                            elif res < 500:
                                self.latency_rating = yellow("[良好]")
                            else:
                                self.latency_rating = red("[稍高]")
                            self.add_log(f"心跳正常 | {service.upper()} 响应: {res}ms", "INFO")
                        else:
                            self.consecutive_fails += 1
                            self.current_latency = red("超时")
                            self.current_latency_val = 0
                            self.latencies.append(0)
                            self.latency_rating = red("[异常]")
                            self.add_log(f"心跳异常 [{self.consecutive_fails}/{max_fails}] | {res}", "WARN")

                            if self.consecutive_fails >= max_fails:
                                self.heal(trigger_reason=f"连续 {max_fails} 次探测失败")
                                self.consecutive_fails = 0

                    threading.Thread(target=_async_probe, daemon=True).start()

                # --- 3. 周期性三路端点探测 (每 60 秒) ---
                if not self.paused and (now - last_multi_probe_time >= 60):
                    last_multi_probe_time = now
                    def _async_multi():
                        self.multi_probe = self.probe.check_all_services()
                        self._refresh_current_node()
                    threading.Thread(target=_async_multi, daemon=True).start()

                # --- 4. 构建渲染状态 (按需/每秒刷新一次，0 CPU 占用) ---
                if needs_render or (now - last_render_time >= 1.0):
                    last_render_time = now
                    needs_render = False

                    if self.paused:
                        badge = yellow("[⏸️ 已暂停]")
                    elif self.is_healing:
                        badge = yellow("[⚡ 自愈切线中]")
                    elif self.consecutive_fails > 0:
                        badge = red(f"[⚠️ 异常 {self.consecutive_fails}/{max_fails}]")
                    else:
                        badge = green("[🟢 监控中]")

                    # 计算均值
                    valid_lat = [v for v in self.latencies if v > 0]
                    avg_str = f"{int(sum(valid_lat) / len(valid_lat))}ms" if valid_lat else "--"

                    # 计算可用率
                    rate_str = f"{(self.success_checks / max(1, self.total_checks)) * 100:.1f}%" if self.total_checks > 0 else "100.0%"

                    state = {
                        "status_badge": badge,
                        "health_rate": rate_str,
                        "check_interval": interval,
                        "mixed_proxy": self.clash.mixed_proxy or "7897",
                        "service": service,
                        "current_node": self.current_node,
                        "current_latency": self.current_latency,
                        "latency_rating": self.latency_rating,
                        "sparkline": generate_sparkline(self.latencies, max_len=15),
                        "avg_latency": avg_str,
                        "multi_probe": self.multi_probe,
                        "today_heals": self.today_heals,
                        "last_heal_info": self.last_heal_info,
                        "quarantine_nodes": self.selector.get_quarantined_nodes() if self.selector else [],
                        "recent_logs": list(self.recent_logs)
                    }

                    # 渲染仪表盘 (分发极简 Zen 模式与全量 Dashboard 模式)
                    if self.ui_mode == "zen":
                        renderer.render_zen(state)
                    else:
                        renderer.render(state)

                # 循环休眠 (100ms 兼顾极低 CPU 占用与单键即时响应)
                time.sleep(0.1)

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            renderer.restore_cursor()
            self.mutex.release()
            print("\n[INFO] Clash-AI-Watchdog 已安全退出。再见！\n")
