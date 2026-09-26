# -*- coding: utf-8 -*-
"""
智能节点筛选与多线程并发测速选优模块 (Selector)
支持分级区域优先测速与全网合规节点自动选优
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import REGION_KEYWORDS, GEO_BLOCKED_KEYWORDS

class NodeSelector:
    def __init__(self, clash_client, preferred_regions=None, blacklisted_keywords=None):
        self.client = clash_client
        self.preferred_regions = preferred_regions or ["TW", "JP", "SG", "KR", "US", "DE", "UK"]
        # 合并通用黑名单与锁区黑名单
        bl = list(blacklisted_keywords or []) + GEO_BLOCKED_KEYWORDS
        self.blacklisted_keywords = [kw.lower() for kw in bl]

    def _is_blacklisted(self, name):
        lower = name.lower()
        return any(b in lower for b in self.blacklisted_keywords)

    def _filter_nodes_by_region(self, all_proxies, region_code):
        """按区域代号（如 TW/JP/SG/US）提取有效真实节点"""
        region_code_upper = region_code.upper()
        
        # 全网自动模式：选择所有非黑名单节点
        if region_code_upper in ("AUTO", "ALL", "GLOBAL"):
            filtered = []
            for name, info in all_proxies.items():
                node_type = info.get('type', '')
                if node_type in ('Selector', 'URLTest', 'Fallback', 'Direct', 'Reject', 'LoadBalance', 'Relay'):
                    continue
                if not self._is_blacklisted(name):
                    filtered.append(name)
            return filtered

        keywords = REGION_KEYWORDS.get(region_code_upper, [region_code.lower()])
        filtered = []
        
        for name, info in all_proxies.items():
            node_type = info.get('type', '')
            if node_type in ('Selector', 'URLTest', 'Fallback', 'Direct', 'Reject', 'LoadBalance', 'Relay'):
                continue
            if self._is_blacklisted(name):
                continue

            lower = name.lower()
            if any(k in lower for k in keywords):
                filtered.append(name)
                
        return filtered

    def select_best_node(self, all_proxies, test_url="https://generativelanguage.googleapis.com", timeout=3000):
        """
        按优先级区域多线程并发测速，返回: (best_node_name, delay_ms, region_used)
        若第一优先级区域节点不可达，自动 Fallback 探测下一区域
        """
        for region in self.preferred_regions:
            candidates = self._filter_nodes_by_region(all_proxies, region)
            if not candidates:
                continue

            valid_results = []
            # 并发测速，最大15并发
            with ThreadPoolExecutor(max_workers=min(15, len(candidates))) as executor:
                futures = {
                    executor.submit(self.client.test_delay, node, test_url, timeout): node 
                    for node in candidates
                }
                for future in as_completed(futures):
                    node = futures[future]
                    try:
                        delay = future.result()
                        # 过滤掉超时 (>5000) 和死节点 (0)
                        if 0 < delay < 5000:
                            valid_results.append((delay, node))
                    except Exception:
                        pass

            if valid_results:
                valid_results.sort(key=lambda x: x[0])
                best_delay, best_node = valid_results[0]
                return best_node, best_delay, region

        return None, None, None
