# -*- coding: utf-8 -*-
"""
AI API 连通性探测器 (Probe)
专注探测 Gemini / Claude / OpenAI 及自定义服务的实际链路通畅度与响应耗时
具备智能识别 Google 区域封锁 (Location Not Supported) 防护能力
支持三路端点并发多路探活
"""

import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
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

    def _probe_single_url(self, url, timeout=None):
        """探测单个 URL 的连通性与耗时"""
        proxy_handler = urllib.request.ProxyHandler({
            'http': self.mixed_proxy,
            'https': self.mixed_proxy
        })
        opener = urllib.request.build_opener(proxy_handler)
        
        effective_timeout = timeout if timeout is not None else self.timeout
        start_time = time.time()
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'ClashAIWatchdog/2.0.0 (HealthCheck)'}
            )
            with opener.open(req, timeout=effective_timeout) as resp:
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

    def quick_tls_check(self, timeout=2.5):
        """
        切线极速真机验真 (Waterfall True-Verification)
        在 2.5 秒内通过代理端口向目标 AI 服务发起真实 TLS 握手。
        若遇到 GFW SNI 重置阻断 (如 SSL: UNEXPECTED_EOF_WHILE_READING) 或超时，瞬间判定为不可用假节点。
        返回: (is_alive: bool, latency_ms_or_err: int | str)
        """
        return self._probe_single_url(self.target_url, timeout=timeout)

    def check(self):
        """
        通过 Clash 代理测试当前主监控目标通道
        返回: (is_alive: bool, latency_ms_or_error: int | str)
        """
        return self._probe_single_url(self.target_url)

    def check_all_services(self):
        """
        并发探测 Gemini, Claude, OpenAI 三路主要 AI 接口
        返回: dict { 'gemini': ms | None, 'claude': ms | None, 'openai': ms | None }
        """
        results = {}
        targets = {
            "gemini": SERVICE_TARGETS.get("gemini"),
            "claude": SERVICE_TARGETS.get("claude"),
            "openai": SERVICE_TARGETS.get("openai")
        }

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._probe_single_url, url): name 
                for name, url in targets.items()
            }
            for fut in futures:
                name = futures[fut]
                try:
                    alive, res = fut.result()
                    results[name] = res if alive else None
                except Exception:
                    results[name] = None

        return results
