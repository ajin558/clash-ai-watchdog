# -*- coding: utf-8 -*-
"""
智能节点筛选与多线程并发测速选优模块 (Selector)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import REGION_KEYWORDS

class NodeSelector:
    def __init__(self, clash_client, preferred_regions=None, blacklisted_keywords=None):
        self.client = clash_client
        self.preferred_regions = preferred_regions or ["US"]
        self.blacklisted_keywords = [kw.lower() for kw in (blacklisted_keywords or [])]

    def _is_blacklisted(self, name):
        lower = name.lower()
        return any(b in lower for b in self.blacklisted_keywords)

    def _filter_nodes_by_region(self, all_proxies, region_code):
        """按区域代号（如 US/SG/JP）提取有效真实节点"""
        keywords = REGION_KEYWORDS.get(region_code.upper(), [region_code.lower()])
        filtered = []
        
        for name, info in all_proxies.items():
            node_type = info.get('type', '')
            # 过滤掉虚拟策略组
            if node_type in ('Selector', 'URLTest', 'Fallback', 'Direct', 'Reject', 'LoadBalance', 'Relay'):
                continue
            if self._is_blacklisted(name):
                continue

            lower = name.lower()
            if any(k in lower for k in keywords):
                filtered.append(name)
                
        return filtered

    def select_best_node(self, all_proxies, test_url="https://www.google.com/generate_204", timeout=3000):
        """
        按优先级区域多线程并发测速，返回: (best_node_name, delay_ms, region_used)
        若第一区域全部不可达，自动 Fallback 探测下一区域
        """
        for region in self.preferred_regions:
            candidates = self._filter_nodes_by_region(all_proxies, region)
            if not candidates:
                continue

            valid_results = []
            with ThreadPoolExecutor(max_workers=min(12, len(candidates))) as executor:
                futures = {
                    executor.submit(self.client.test_delay, node, test_url, timeout): node 
                    for node in candidates
                }
                for future in as_completed(futures):
                    node = futures[future]
                    try:
                        delay = future.result()
                        if 0 < delay < 5000:
                            valid_results.append((delay, node))
                    except Exception:
                        pass

            if valid_results:
                valid_results.sort(key=lambda x: x[0])
                best_delay, best_node = valid_results[0]
                return best_node, best_delay, region

        return None, None, None
