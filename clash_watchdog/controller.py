# -*- coding: utf-8 -*-
"""
代理控制器抽象接口基类 (Proxy Controller Abstraction)
统一定义获取节点、切换节点、测速、斩断僵尸连接等核心控制契约，
使上层自愈逻辑与具体的代理客户端实现（Clash, Mihomo, Sing-box 等）彻底解耦。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProxyController(ABC):
    """代理客户端控制器抽象基类"""

    @abstractmethod
    def discover(self) -> bool:
        """自动扫描并连接活动的代理客户端控制端口与代理端口"""
        pass

    @abstractmethod
    def get_proxies(self) -> Dict[str, Any]:
        """获取所有代理节点及策略组信息"""
        pass

    @abstractmethod
    def switch_proxy(self, group_name: str, node_name: str) -> bool:
        """为指定策略组切换选中的节点"""
        pass

    @abstractmethod
    def test_delay(self, node_name: str, test_url: str = "https://www.google.com/generate_204", timeout: int = 3000) -> int:
        """测试指定节点的基础延迟 (ms)"""
        pass

    @abstractmethod
    def close_all_connections(self) -> bool:
        """斩断所有活动的 TCP 链路，迫使客户端立刻重连"""
        pass
