# -*- coding: utf-8 -*-
"""
AI API 连通性探测器 (Probe)
专注探测 Gemini / Claude / OpenAI 及自定义服务的实际链路通畅度与响应耗时
具备智能识别 Google 区域封锁 (Location Not Supported) 防护能力
"""

import time
import urllib.request
import urllib.error
from .config import SERVICE_TARGETS

class Probe:
    def __init__(self, service="gemini", custom_url="", mixed_proxy="http://127.0.0.1:7897", timeout=8):
        self.service = service
        self.custom_url = custom_url
        self.mixed_proxy = mixed_proxy
        self.timeout = timeout

    @property
    def target_url(self):
        if self.service == "custom" and self.custom_url:
            return self.custom_url
        return SERVICE_TARGETS.get(self.service, SERVICE_TARGETS["gemini"])

    def check(self):
        """
        通过 Clash 代理测试与目标 API 的网络通路
        返回: (is_alive: bool, latency_ms_or_error: int | str)
        """
        proxy_handler = urllib.request.ProxyHandler({
            'http': self.mixed_proxy,
            'https': self.mixed_proxy
        })
        opener = urllib.request.build_opener(proxy_handler)
        
        start_time = time.time()
        try:
            req = urllib.request.Request(
                self.target_url,
                headers={'User-Agent': 'ClashAIWatchdog/1.2.0 (HealthCheck)'}
            )
            with opener.open(req, timeout=self.timeout) as resp:
                elapsed = int((time.time() - start_time) * 1000)
                return True, elapsed
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode('utf-8', errors='ignore')
            except Exception:
                pass

            # 核心防护：精准识别 Google / AI 服务商的地域封锁拦截
            lower_body = err_body.lower()
            if "location is not supported" in lower_body or "not supported in your country" in lower_body:
                return False, "地域受限: Google API 返回 User location is not supported"

            # 其余 HTTP 状态（如无鉴权的 401/404）说明底层 TCP/TLS 链路及反代完全正常
            elapsed = int((time.time() - start_time) * 1000)
            return True, elapsed
        except Exception as e:
            return False, str(e)
