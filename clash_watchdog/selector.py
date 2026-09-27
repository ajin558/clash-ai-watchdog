# -*- coding: utf-8 -*-
"""
智能节点筛选与多线程并发测速选优模块 (Selector)
增强特性：
1. 专线/家宽/IEPL 优先加权：优先挑选抗封锁能力强的专线节点，同级下按延迟排序；
2. 直连/锁区硬拉黑：彻底屏蔽无法抵抗 GFW SNI 阻断的伪低延迟“直连”节点；
3. 多候选提取支持：输出 Top N 候选列表，供自愈引擎进行切线后真实 TLS 瀑布验真；
4. 故障节点隔离冷却池 (Quarantine Pool, 默认10分钟)，彻底杜绝故障节点来回震荡切线。
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import REGION_KEYWORDS, GEO_BLOCKED_KEYWORDS, PRIORITY_KEYWORDS

class NodeSelector:
    def __init__(self, clash_client, preferred_regions=None, blacklisted_keywords=None, priority_keywords=None, quarantine_duration=600):
        self.client = clash_client
        self.preferred_regions = preferred_regions or ["TW", "JP", "SG", "KR", "US", "DE", "UK"]
        
        # 合并通用黑名单与锁区黑名单 (HK/香港/CN/RU/直连/direct 等)
        bl = list(blacklisted_keywords or []) + GEO_BLOCKED_KEYWORDS + ["直连", "direct"]
        # 去重且转小写
        self.blacklisted_keywords = list(set(kw.lower() for kw in bl))
        
        # 专线优先加权关键词 (IEPL, 家宽, 进阶, 专线等)
        pri = list(priority_keywords or PRIORITY_KEYWORDS)
        self.priority_keywords = list(set(kw.lower() for kw in pri))
        
        # 故障节点隔离冷却池: { node_name: expire_timestamp }
        self.quarantine_pool = {}
        self.quarantine_duration = quarantine_duration

    def quarantine_node(self, node_name, reason="连接超时或API报错"):
        """将故障节点加入隔离冷却池"""
        expire_at = time.time() + self.quarantine_duration
        self.quarantine_pool[node_name] = expire_at

    def get_quarantined_nodes(self):
        """清理已过期节点并返回当前活跃隔离节点列表"""
        now = time.time()
        self.quarantine_pool = {k: v for k, v in self.quarantine_pool.items() if v > now}
        return list(self.quarantine_pool.keys())

    def _is_blacklisted(self, name):
        lower = name.lower()
        return any(b in lower for b in self.blacklisted_keywords)

    def _is_priority(self, name):
        """判断节点是否为优质专线/家宽/IEPL"""
        lower = name.lower()
        return any(p in lower for p in self.priority_keywords)

    def _filter_nodes_by_region(self, all_proxies, region_code, check_quarantine=True):
        """按区域代号提取有效真实节点，自动剔除黑名单与隔离期节点"""
        region_code_upper = region_code.upper()
        active_quarantine = set(self.get_quarantined_nodes()) if check_quarantine else set()

        is_all = region_code_upper in ("AUTO", "ALL", "GLOBAL")
        keywords = [] if is_all else REGION_KEYWORDS.get(region_code_upper, [region_code.lower()])

        filtered = []
        for name, info in all_proxies.items():
            node_type = info.get('type', '')
            if node_type in ('Selector', 'URLTest', 'Fallback', 'Direct', 'Reject', 'LoadBalance', 'Relay'):
                continue
            if self._is_blacklisted(name):
                continue
            if check_quarantine and name in active_quarantine:
                continue

            if is_all:
                filtered.append(name)
            else:
                lower = name.lower()
                if any(k in lower for k in keywords):
                    filtered.append(name)
                    
        return filtered

    def get_top_candidates(self, all_proxies, test_url="https://generativelanguage.googleapis.com", timeout=3000, limit=5):
        """
        按优先级区域多线程并发测速，返回 Top N 优质候选节点列表:
        [(node_name, delay_ms, region), ...]
        专线/家宽节点排在普通节点之前，供自愈引擎进行瀑布流真机 TLS 验真
        """
        # 第一阶段：严格剔除隔离池故障节点
        candidates = self._benchmark_candidates(all_proxies, test_url, timeout, check_quarantine=True, limit=limit)
        if candidates:
            return candidates

        # 第二阶段（全线告急兜底）：若所有可用节点都在隔离池，从隔离池降级借用
        if self.quarantine_pool:
            fallback = self._benchmark_candidates(all_proxies, test_url, timeout, check_quarantine=False, limit=limit)
            if fallback:
                return fallback

        return []

    def select_best_node(self, all_proxies, test_url="https://generativelanguage.googleapis.com", timeout=3000):
        """
        返回单个最优推荐节点: (best_node_name, delay_ms, region_used)
        """
        candidates = self.get_top_candidates(all_proxies, test_url=test_url, timeout=timeout, limit=1)
        if candidates:
            return candidates[0]
        return None, None, None

    def _benchmark_candidates(self, all_proxies, test_url, timeout, check_quarantine=True, limit=5):
        """执行区域多线程测试并按专线优先+延迟升序收集优质候选"""
        collected = []
        for region in self.preferred_regions:
            candidates = self._filter_nodes_by_region(all_proxies, region, check_quarantine=check_quarantine)
            if not candidates:
                continue

            valid_results = []
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
                            is_pri = self._is_priority(node)
                            valid_results.append((node, delay, region, is_pri))
                    except Exception:
                        pass

            if valid_results:
                # 排序规则：专线/家宽 (is_pri=True) 优先排在前面；同一级别内按延迟升序
                valid_results.sort(key=lambda x: (0 if x[3] else 1, x[1]))
                for node, delay, reg, _ in valid_results:
                    collected.append((node, delay, reg))
                    if len(collected) >= limit:
                        return collected

        return collected
