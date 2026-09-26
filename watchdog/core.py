# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 核心引擎与主调度器 (Core Engine)
"""

import time
from .config import load_config
from .clash_client import ClashClient
from .probe import Probe
from .selector import NodeSelector
from .notifier import Notifier
from .tui import print_banner, log, green, yellow, red, cyan

class WatchdogEngine:
    def __init__(self, config_path="config.json", overrides=None):
        self.cfg = load_config(config_path)
        if overrides:
            self.cfg.update(overrides)

        self.clash = ClashClient(
            api_base=self.cfg.get("clash_api_base", "auto"),
            secret=self.cfg.get("clash_secret", ""),
            mixed_proxy=self.cfg.get("mixed_proxy", "auto")
        )
        self.notifier = Notifier(self.cfg.get("notifications", {}))
        self.probe = None
        self.selector = None

    def initialize(self):
        """探测并绑定 Clash 客户端与网络组件"""
        log("正在探测并连接本地 Clash / Mihomo 核心...", "INFO")
        if not self.clash.discover():
            log("未发现运行中的 Clash 控制端口！请确认 Clash 已开启 External Controller。", "ERROR")
            return False

        log(f"成功连接 Clash 控制端: {self.clash.api_base}", "SUCCESS")
        log(f"使用本地代理通道: {self.clash.mixed_proxy}", "INFO")

        self.probe = Probe(
            service=self.cfg.get("target_service", "gemini"),
            custom_url=self.cfg.get("custom_target_url", ""),
            mixed_proxy=self.clash.mixed_proxy,
            timeout=self.cfg.get("check_timeout", 8)
        )

        self.selector = NodeSelector(
            clash_client=self.clash,
            preferred_regions=self.cfg.get("preferred_regions", ["US"]),
            blacklisted_keywords=self.cfg.get("blacklisted_keywords", [])
        )
        return True

    def run_diagnostics(self):
        """测试模式：执行单次完整自检与测速诊断"""
        if not self.initialize():
            return False

        log("--- 开始单次诊断测试 ---", "INFO")
        alive, result = self.probe.check()
        if alive:
            log(f"当前监控目标 ({self.probe.service}) 连通正常，耗时: {result}ms", "SUCCESS")
        else:
            log(f"当前网络测试异常: {result}", "WARN")

        proxies = self.clash.get_proxies()
        log(f"获取到订阅内共 {len(proxies)} 个对象", "INFO")

        best_node, delay, region = self.selector.select_best_node(
            proxies,
            test_url=self.probe.target_url
        )
        if best_node:
            log(f"多线程优选结果 -> [{region}] {best_node} (延迟: {delay}ms)", "SUCCESS")
        else:
            log("未筛选到可用节点，请检查区域配置或黑名单关键词", "WARN")

        log("--- 诊断测试完成 ---", "INFO")
        return True

    def heal(self):
        """执行换线自愈流程"""
        log("触发自愈流程，开始多线程优选最佳节点...", "WARN")
        self.notifier.beep(800, 200)

        proxies = self.clash.get_proxies()
        if not proxies:
            log("无法获取 Clash 节点列表，自愈中止", "ERROR")
            return False

        best_node, best_delay, region = self.selector.select_best_node(
            proxies,
            test_url=self.probe.target_url
        )

        if not best_node:
            log("未能找到任何可用的优选节点！", "ERROR")
            return False

        log(f"优选目标锁定: [{region}] {best_node} (延迟: {best_delay}ms)", "INFO")

        target_groups = self.cfg.get("target_groups", ["GLOBAL", "节点选择"])
        switched = 0
        for group in target_groups:
            if group in proxies:
                if self.clash.switch_proxy(group, best_node):
                    log(f"策略组 [{group}] 已成功切换至新节点", "SUCCESS")
                    switched += 1

        if switched > 0:
            # 关键：斩断僵死连接
            self.clash.close_all_connections()
            log("已强制重置所有残留活动连接！AI Agent 将立即用新 IP 重连", "SUCCESS")
            self.notifier.notify_healed(None, best_node, best_delay, region)
            return True
        else:
            log("未找到可切换的策略组，请检查 target_groups 配置", "WARN")
            return False

    def start(self):
        """启动守护主循环"""
        if not self.initialize():
            return

        interval = self.cfg.get("check_interval", 30)
        max_fails = self.cfg.get("max_fail_count", 2)
        service = self.cfg.get("target_service", "gemini")
        regions = self.cfg.get("preferred_regions", ["US"])

        print_banner(service, interval, self.clash.mixed_proxy, self.clash.api_base, regions)

        consecutive_fails = 0

        while True:
            try:
                alive, result = self.probe.check()
                if alive:
                    consecutive_fails = 0
                    log(f"心跳正常 | {service.upper()} 响应: {result}ms", "SUCCESS")
                else:
                    consecutive_fails += 1
                    log(f"心跳异常 [{consecutive_fails}/{max_fails}] | 错误: {result}", "WARN")

                    if consecutive_fails >= max_fails:
                        if self.heal():
                            consecutive_fails = 0
                            time.sleep(5)

                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n[INFO] 接收到退出信号，Clash-AI-Watchdog 已安全退出。")
                break
            except Exception as e:
                log(f"主调度异常: {e}", "ERROR")
                time.sleep(interval)
