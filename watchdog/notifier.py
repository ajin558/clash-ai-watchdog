# -*- coding: utf-8 -*-
"""
多渠道通知告警模块 (Notifier)
支持蜂鸣警报、Windows 原生桌面弹窗、主流 Webhook（飞书、企业微信、钉钉、Telegram）
"""

import sys
import json
import urllib.request
import subprocess

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

class Notifier:
    def __init__(self, config=None):
        self.cfg = config or {}
        self.sound_enabled = self.cfg.get("sound", True)
        self.toast_enabled = self.cfg.get("desktop_toast", True)
        self.webhook_type = self.cfg.get("webhook_type", "").lower()
        self.webhook_url = self.cfg.get("webhook_url", "").strip()

    def beep(self, freq=1200, duration=300):
        if not self.sound_enabled:
            return
        if HAS_WINSOUND:
            try:
                winsound.Beep(freq, duration)
            except Exception:
                pass
        else:
            try:
                sys.stdout.write('\a')
                sys.stdout.flush()
            except Exception:
                pass

    def show_toast(self, title, message):
        """利用 Windows 原生 PowerShell 发送桌面气泡/通知，无需额外第三方库"""
        if not self.toast_enabled or sys.platform != "win32":
            return
        try:
            # 简洁的原生提示脚本
            ps_script = f'''
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
            $objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon
            $objNotifyIcon.Icon = [System.Drawing.SystemIcons]::Information
            $objNotifyIcon.BalloonTipIcon = "Info"
            $objNotifyIcon.BalloonTipTitle = "{title}"
            $objNotifyIcon.BalloonTipText = "{message}"
            $objNotifyIcon.Visible = $True
            $objNotifyIcon.ShowBalloonTip(5000)
            Start-Sleep -Milliseconds 100
            $objNotifyIcon.Dispose()
            '''
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def send_webhook(self, title, message):
        """发送 Webhook 消息"""
        if not self.webhook_url:
            return

        payload = {}
        if self.webhook_type == "feishu":
            payload = {
                "msg_type": "text",
                "content": {"text": f"【{title}】\n{message}"}
            }
        elif self.webhook_type in ("wecom", "dingtalk"):
            payload = {
                "msgtype": "text",
                "text": {"content": f"【{title}】\n{message}"}
            }
        elif self.webhook_type == "telegram":
            payload = {
                "text": f"*{title}*\n{message}",
                "parse_mode": "Markdown"
            }
        else:
            payload = {"title": title, "message": message}

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except Exception:
            pass

    def notify_healed(self, old_state, new_node, delay_ms, region):
        title = "Clash-AI-Watchdog 自愈成功"
        msg = f"检测到网络卡顿，已自动切换至 [{region}] 节点: {new_node} (延迟: {delay_ms}ms)，并清理了残留僵尸连接！"
        self.beep(1500, 400)
        self.show_toast(title, msg)
        self.send_webhook(title, msg)
