# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog v2.0 单元测试集
覆盖：控制器抽象继承、直连硬拉黑、专线优先加权、瀑布流候选提取、故障隔离冷却池
"""

import unittest
from clash_watchdog.controller import BaseProxyController
from clash_watchdog.clash_client import ClashClient
from clash_watchdog.config import DEFAULT_CONFIG, PRIORITY_KEYWORDS
from clash_watchdog.selector import NodeSelector

class MockClashClient(BaseProxyController):
    def __init__(self, delay_map=None):
        self.delay_map = delay_map or {}
        self.switched = []
        self.closed_connections = 0

    def discover(self):
        return True

    def get_proxies(self):
        return {}

    def switch_proxy(self, group_name, node_name):
        self.switched.append((group_name, node_name))
        return True

    def test_delay(self, node_name, test_url="https://www.google.com/generate_204", timeout=3000):
        return self.delay_map.get(node_name, 200)

    def close_all_connections(self):
        self.closed_connections += 1
        return True

class TestV2Features(unittest.TestCase):
    def test_controller_inheritance(self):
        """测试 ClashClient 继承自 BaseProxyController"""
        client = ClashClient()
        self.assertIsInstance(client, BaseProxyController)

    def test_config_blacklists_and_priority(self):
        """测试默认配置包含直连黑名单与专线加权关键词"""
        bl = DEFAULT_CONFIG["blacklisted_keywords"]
        self.assertIn("直连", bl)
        self.assertIn("direct", bl)
        
        pri = DEFAULT_CONFIG["priority_keywords"]
        self.assertIn("iepl", pri)
        self.assertIn("家宽", pri)
        self.assertIn("专线", pri)

    def test_selector_filters_direct_and_boosts_priority(self):
        """测试选择器坚决剔除直连节点，并对 IEPL/家宽 节点优先排序"""
        mock_proxies = {
            "🇹🇼|台湾直连 01": {"type": "Shadowsocks"},
            "🇹🇼|台湾普通 01": {"type": "Shadowsocks"},
            "🇹🇼|台湾家宽-IEPL 02": {"type": "Shadowsocks"},
            "🇸🇬|新加坡-IEPL 01": {"type": "Shadowsocks"},
            "🇭🇰|香港专线 01": {"type": "Shadowsocks"}, # 锁区应当被过滤
        }

        # 模拟 Clash delay：假低延迟的直连 120ms，普通 150ms，专线 210ms
        delay_map = {
            "🇹🇼|台湾直连 01": 120,
            "🇹🇼|台湾普通 01": 150,
            "🇹🇼|台湾家宽-IEPL 02": 210,
            "🇸🇬|新加坡-IEPL 01": 220,
            "🇭🇰|香港专线 01": 100,
        }

        client = MockClashClient(delay_map)
        selector = NodeSelector(
            clash_client=client,
            preferred_regions=["TW", "SG"],
            blacklisted_keywords=DEFAULT_CONFIG["blacklisted_keywords"],
            priority_keywords=DEFAULT_CONFIG["priority_keywords"]
        )

        candidates = selector.get_top_candidates(mock_proxies, limit=5)
        candidate_names = [c[0] for c in candidates]

        # 1. 绝对不包含直连节点
        self.assertNotIn("🇹🇼|台湾直连 01", candidate_names)
        # 2. 绝对不包含香港锁区节点
        self.assertNotIn("🇭🇰|香港专线 01", candidate_names)
        # 3. 专线/家宽节点虽然延迟(210ms)高于普通节点(150ms)，但必须排在普通节点前面！
        self.assertEqual(candidate_names[0], "🇹🇼|台湾家宽-IEPL 02")
        self.assertEqual(candidate_names[1], "🇹🇼|台湾普通 01")

    def test_quarantine_pool_cooldown(self):
        """测试故障节点进入隔离冷却池后被跳过"""
        mock_proxies = {
            "🇹🇼|台湾家宽-IEPL 01": {"type": "Shadowsocks"},
            "🇹🇼|台湾家宽-IEPL 02": {"type": "Shadowsocks"},
        }
        delay_map = {
            "🇹🇼|台湾家宽-IEPL 01": 190,
            "🇹🇼|台湾家宽-IEPL 02": 200,
        }
        client = MockClashClient(delay_map)
        selector = NodeSelector(client, preferred_regions=["TW"])

        # 隔离 01 节点
        selector.quarantine_node("🇹🇼|台湾家宽-IEPL 01", "模拟阻断")
        self.assertIn("🇹🇼|台湾家宽-IEPL 01", selector.get_quarantined_nodes())

        # 优选时应当自动选中 02
        candidates = selector.get_top_candidates(mock_proxies, limit=5)
        self.assertEqual(candidates[0][0], "🇹🇼|台湾家宽-IEPL 02")

if __name__ == "__main__":
    unittest.main()
