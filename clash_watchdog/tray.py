# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 系统托盘应用模块 (System Tray)
支持后台无窗口静默运行、任务栏托盘状态灯、实时右键菜单与一键自愈控制
"""

import sys
import os
import threading
import time
import webbrowser

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    HAS_TRAY_DEPS = True
except ImportError:
    HAS_TRAY_DEPS = False

from .core import WatchdogEngine
from .tui import log

def create_badge_image(color_hex="#10B981", status_char="W"):
    """使用 Pillow 在内存中动态绘制高清晰度状态托盘图标 (64x64)"""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 绘制外圈高光圆角矩形/圆形底座
    draw.ellipse((4, 4, size - 4, size - 4), fill=color_hex)
    
    # 绘制内部微质感阴影内圆
    inner_margin = 12
    draw.ellipse((inner_margin, inner_margin, size - inner_margin, size - inner_margin), fill="#FFFFFF")

    # 在中心绘制简明标识
    draw.ellipse((inner_margin + 6, inner_margin + 6, size - inner_margin - 6, size - inner_margin - 6), fill=color_hex)
    return image

class TrayApp:
    def __init__(self, config_path="config.json"):
        if not HAS_TRAY_DEPS:
            raise RuntimeError("系统托盘功能需要 pystray 和 Pillow 支持，请运行: pip install pystray pillow")

        self.engine = WatchdogEngine(config_path=config_path)
        self.icon = None
        self.worker_thread = None
        self.running = False
        self.paused = False

        # 实时状态缓存
        self.last_status = "初始化中..."
        self.last_latency = "--"
        self.current_node = "未获取"
        self.current_state = "init" # init, healthy, warning, error, paused

        # 图标颜色映射
        self.color_map = {
            "healthy": "#10B981",  # 绿色
            "warning": "#F59E0B",  # 橙黄色 (自愈中)
            "error":   "#EF4444",  # 红色 (故障)
            "paused":  "#6B7280",  # 灰色 (暂停)
            "init":    "#3B82F6"   # 蓝色
        }

    def _update_state(self, state, status_text):
        self.current_state = state
        self.last_status = status_text
        if self.icon:
            self.icon.icon = create_badge_image(self.color_map.get(state, "#10B981"))
            self.icon.title = f"Clash-AI-Watchdog: {status_text}"
            self.icon.update_menu()

    def _watchdog_loop(self):
        """后台轮询工作线程"""
        if not self.engine.initialize():
            self._update_state("error", "连接 Clash 失败")
            return

        interval = self.engine.cfg.get("check_interval", 30)
        max_fails = self.engine.cfg.get("max_fail_count", 2)
        service = self.engine.cfg.get("target_service", "gemini")

        # 获取初始节点
        try:
            proxies = self.engine.clash.get_proxies()
            for g in ["GLOBAL", "节点选择", "PROXY"]:
                if g in proxies and "now" in proxies[g]:
                    self.current_node = proxies[g]["now"]
                    break
        except Exception:
            pass

        self._update_state("healthy", f"守护中 ({service.upper()})")
        consecutive_fails = 0

        while self.running:
            if self.paused:
                time.sleep(1)
                continue

            try:
                alive, result = self.engine.probe.check()
                if alive:
                    consecutive_fails = 0
                    self.last_latency = f"{result}ms"
                    self._update_state("healthy", f"正常 ({self.last_latency})")
                else:
                    consecutive_fails += 1
                    self.last_latency = "超时"
                    self._update_state("warning", f"探测异常 [{consecutive_fails}/{max_fails}]")

                    if consecutive_fails >= max_fails:
                        self._update_state("warning", "正在自动优选换线...")
                        if self.engine.heal():
                            consecutive_fails = 0
                            # 更新当前节点名
                            proxies = self.engine.clash.get_proxies()
                            for g in ["GLOBAL", "节点选择", "PROXY"]:
                                if g in proxies and "now" in proxies[g]:
                                    self.current_node = proxies[g]["now"]
                                    break
                            self._update_state("healthy", f"自愈完成 ({self.current_node})")
                            time.sleep(5)
                        else:
                            self._update_state("error", "换线失败，无可用节点")

                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self._update_state("error", f"异常: {e}")
                time.sleep(interval)

    # 菜单回调函数
    def action_force_heal(self):
        def _task():
            self._update_state("warning", "正在手动换线自愈...")
            if self.engine.heal():
                proxies = self.engine.clash.get_proxies()
                for g in ["GLOBAL", "节点选择", "PROXY"]:
                    if g in proxies and "now" in proxies[g]:
                        self.current_node = proxies[g]["now"]
                        break
                self._update_state("healthy", f"已切换至: {self.current_node}")
            else:
                self._update_state("error", "换线未成功")
        threading.Thread(target=_task, daemon=True).start()

    def action_diagnostics(self):
        def _task():
            self._update_state("warning", "网络自检中...")
            alive, result = self.engine.probe.check()
            if alive:
                self.engine.notifier.show_toast(
                    "网络诊断成功", 
                    f"目标服务通道畅通，延迟: {result}ms\n当前节点: {self.current_node}"
                )
                self._update_state("healthy", f"正常 ({result}ms)")
            else:
                self.engine.notifier.show_toast("网络诊断失败", f"链路不可达: {result}")
                self._update_state("error", f"测试失败: {result}")
        threading.Thread(target=_task, daemon=True).start()

    def action_toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._update_state("paused", "已暂停守护")
        else:
            self._update_state("healthy", "已恢复守护")

    def action_open_config(self):
        cfg_file = os.path.abspath(self.engine.cfg.get("config_path", "config.json"))
        if not os.path.exists(cfg_file):
            from .config import save_example_config
            save_example_config(cfg_file)
        if sys.platform == "win32":
            os.startfile(cfg_file)
        elif sys.platform == "darwin":
            os.system(f"open '{cfg_file}'")
        else:
            os.system(f"xdg-open '{cfg_file}'")

    def action_open_github(self):
        webbrowser.open("https://github.com/ajin558/clash-ai-watchdog")

    def action_quit(self):
        self.running = False
        if self.icon:
            self.icon.stop()

    def build_menu(self):
        """构建动态右键上下文菜单"""
        pause_label = "▶️ 恢复守护" if self.paused else "⏸️ 暂停守护"
        return pystray.Menu(
            pystray.MenuItem(f"状态: {self.last_status}", lambda: None, enabled=False),
            pystray.MenuItem(f"当前节点: {self.current_node[:25]}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚡ 立即强制自愈换线", lambda: self.action_force_heal()),
            pystray.MenuItem("🔍 执行一次网络自检", lambda: self.action_diagnostics()),
            pystray.MenuItem(pause_label, lambda: self.action_toggle_pause()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ 打开配置文件", lambda: self.action_open_config()),
            pystray.MenuItem("🌐 访问 GitHub 仓库", lambda: self.action_open_github()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 退出守护", lambda: self.action_quit())
        )

    def run(self):
        self.running = True
        # 启动后台守护工作线程
        self.worker_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.worker_thread.start()

        # 启动托盘图标主循环
        initial_image = create_badge_image(self.color_map["init"])
        self.icon = pystray.Icon(
            name="Clash-AI-Watchdog",
            icon=initial_image,
            title="Clash-AI-Watchdog: 启动中...",
            menu=self.build_menu
        )
        self.icon.run()

def main():
    app = TrayApp()
    app.run()

if __name__ == "__main__":
    main()
