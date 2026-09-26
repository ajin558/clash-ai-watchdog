# -*- coding: utf-8 -*-
"""
Clash-AI-Watchdog 配置管理模块 (v1.2.0 全球合规节点扩容版)
"""

import os
import json

# 严禁使用的锁区/不支持关键词（无论延迟多低绝对不可选，防止 Google 锁区报错）
GEO_BLOCKED_KEYWORDS = [
    "香港", "hk", "hongkong", "🇭🇰",
    "中国", "china", "回国", "国内", "🇨🇳",
    "澳门", "macau", "mo", "🇲🇴",
    "俄罗斯", "russia", "ru", "🇷🇺"
]

# 官方 100% 支持的合规地区关键词库
REGION_KEYWORDS = {
    "TW": ["台湾", "tw", "taiwan", "🇹🇼"],
    "JP": ["日本", "jp", "japan", "东京", "大阪", "🇯🇵"],
    "SG": ["新加坡", "sg", "singapore", "狮城", "🇸🇬"],
    "KR": ["韩国", "kr", "korea", "首尔", "🇰🇷"],
    "US": ["美国", "us", "usa", "united states", "🇺🇸"],
    "DE": ["德国", "de", "germany", "法兰克福", "🇩🇪"],
    "UK": ["英国", "uk", "united kingdom", "伦敦", "🇬🇧"],
    "CA": ["加拿大", "ca", "canada", "🇨🇦"],
    "AU": ["澳大利亚", "au", "australia", "悉尼", "🇦🇺"]
}

DEFAULT_CONFIG = {
    # Clash 控制端配置（设为 "auto" 将自动扫描发现端口）
    "clash_api_base": "auto",
    "clash_secret": "",
    "mixed_proxy": "auto",

    # 监控目标：可选 "gemini", "claude", "openai", "google_204", "custom"
    "target_service": "gemini",
    "custom_target_url": "",

    # 探测与自愈阈值
    "check_interval": 30,          # 探测心跳周期（秒）
    "check_timeout": 8,            # 探测超时门限（秒）
    "max_fail_count": 2,           # 连续失败触发自愈阈值
    "cooldown_seconds": 15,        # 切线后冷却防抖时间（秒）

    # 优选节点区域优先列表：优先亚洲低延迟合规区，美欧保底
    "preferred_regions": ["TW", "JP", "SG", "KR", "US", "DE", "UK"],

    # 排除的垃圾节点关键词
    "blacklisted_keywords": [
        "官网", "到期", "剩余", "流量", "重置", "通知", "发布",
        "expire", "traffic", "reset", "info", "notice"
    ] + GEO_BLOCKED_KEYWORDS,

    # 需要接管切换的 Clash 策略组名称
    "target_groups": ["GLOBAL", "节点选择", "PROXY", "Auto", "代理"],

    # 提醒通知配置
    "notifications": {
        "sound": True,
        "desktop_toast": True,
        "webhook_type": "",        # 可选: "feishu", "dingtalk", "wecom", "telegram"
        "webhook_url": ""
    }
}

SERVICE_TARGETS = {
    "gemini": "https://generativelanguage.googleapis.com",
    "claude": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1/models",
    "google_204": "https://www.google.com/generate_204"
}

def load_config(config_path="config.json"):
    """加载配置并与默认配置做深合并"""
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                for k, v in user_cfg.items():
                    if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        except Exception as e:
            print(f"[警告] 读取配置文件 {config_path} 失败: {e}，将采用默认配置。")
    return cfg

def save_example_config(file_path="config.example.json"):
    """导出示例配置文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
