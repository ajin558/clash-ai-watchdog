# -*- coding: utf-8 -*-
"""
Clash / Mihomo 统一 RESTful API 客户端
支持自动端口探测、多版本兼容（Clash Premium, Mihomo/Clash Meta, Clash OpenSource）
"""

import json
import socket
import urllib.request
import urllib.parse
import urllib.error

from .controller import BaseProxyController

COMMON_API_PORTS = [9097, 9090, 7890, 7897, 33331]
COMMON_PROXY_PORTS = [7897, 7890, 10808, 1080]

class ClashClient(BaseProxyController):
    def __init__(self, api_base="auto", secret="", mixed_proxy="auto"):
        self.secret = secret
        self.api_base = None
        self.mixed_proxy = None
        
        if api_base != "auto" and api_base:
            self.api_base = api_base.rstrip('/')
        if mixed_proxy != "auto" and mixed_proxy:
            self.mixed_proxy = mixed_proxy.rstrip('/')

    def _request(self, path, method="GET", data=None, timeout=5):
        """执行带鉴权的 HTTP 请求"""
        if not self.api_base:
            raise RuntimeError("Clash API 地址尚未初始化！")
            
        url = f"{self.api_base}{path}"
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Content-Type', 'application/json')
        if self.secret:
            req.add_header('Authorization', f'Bearer {self.secret}')
            
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            if content:
                try:
                    return json.loads(content.decode('utf-8'))
                except Exception:
                    return content.decode('utf-8', errors='ignore')
            return None

    def discover(self):
        """自动扫描并连接本地活动的 Clash / Mihomo 控制端与代理端口"""
        if self.api_base:
            # 验证现有地址
            try:
                ver = self._request("/version", timeout=2)
                return True
            except Exception:
                pass

        # 遍历常见端口探测
        for port in COMMON_API_PORTS:
            url = f"http://127.0.0.1:{port}"
            try:
                # 快速 TCP 端口嗅探
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.4)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:
                    continue

                self.api_base = url
                data = self._request("/version", timeout=2)
                if data and ("version" in data or "meta" in data):
                    break
            except Exception:
                self.api_base = None
                continue

        if not self.api_base:
            return False

        # 尝试通过 /configs 获取 mixed-port，并嗅探验证
        if not self.mixed_proxy:
            port_found = None
            try:
                cfg = self._request("/configs", timeout=3)
                if isinstance(cfg, dict):
                    configured_port = cfg.get("mixed-port") or cfg.get("port")
                    if configured_port and configured_port > 0:
                        port_found = configured_port
            except Exception:
                pass

            candidates = [port_found] if port_found else []
            candidates.extend([p for p in COMMON_PROXY_PORTS if p not in candidates])

            valid_proxy_port = 7897
            for p in candidates:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                res = sock.connect_ex(('127.0.0.1', p))
                sock.close()
                if res == 0:
                    valid_proxy_port = p
                    break
            self.mixed_proxy = f"http://127.0.0.1:{valid_proxy_port}"

        return True

    def get_version(self):
        return self._request("/version", timeout=3)

    def get_configs(self):
        return self._request("/configs", timeout=3)

    def get_proxies(self):
        data = self._request("/proxies", timeout=5)
        return data.get("proxies", {}) if isinstance(data, dict) else {}

    def test_delay(self, node_name, test_url="https://www.google.com/generate_204", timeout=3000):
        """测试指定节点对特定 URL 的响应延迟"""
        enc_name = urllib.parse.quote(node_name)
        enc_url = urllib.parse.quote(test_url, safe='')
        path = f"/proxies/{enc_name}/delay?timeout={timeout}&url={enc_url}"
        try:
            data = self._request(path, timeout=(timeout / 1000.0) + 1.5)
            if isinstance(data, dict) and "delay" in data:
                return data["delay"]
        except Exception:
            pass
        return 99999

    def switch_proxy(self, group_name, node_name):
        """切换策略组选中的节点"""
        enc_group = urllib.parse.quote(group_name)
        path = f"/proxies/{enc_group}"
        try:
            self._request(path, method="PUT", data={"name": node_name}, timeout=4)
            return True
        except Exception:
            return False

    def close_all_connections(self):
        """
        核心杀招：调用 DELETE /connections 强行中断所有活动 TCP 链路
        使挂起的半开死连接瞬间获得 RST/Close 信号，促使客户端即刻重连
        """
        try:
            self._request("/connections", method="DELETE", timeout=5)
            return True
        except Exception:
            return False
