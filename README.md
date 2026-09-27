# 🐕 Clash-AI-Watchdog

> **专为 AI Agent / LLM 开发者打造的智能代理健康守护与自动换线自愈引擎**  
> *Zero Token Consumption · Zero External Dependencies · Instant Zombie Connection Teardown*

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](pyproject.toml)
[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20required-green.svg)](requirements.txt)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

[English](#english-documentation) | [中文说明](#中文说明)

---

<a name="中文说明"></a>
## 💡 为什么需要 Clash-AI-Watchdog？

在使用 **Antigravity**、**Cursor**、**Claude Code**、**OpenCode**、**Aider** 等自主 AI Agent 跑长时间任务（如通宵批量写代码、大规模数据分析、自动化小说生成）时，你是否经常遇到这种绝望场景：

- 💤 **任务无声假死**：控制台一直卡在“正在思考”或“正在等待响应”，一卡就是 10~20 分钟；
- 🔄 **Clash 节点漂移**：代理客户端的 `url-test`（自动选路）在网络轻微抖动时频繁切节点，导致原有的长连接断开；
- 💀 **TCP 僵尸半开连接（Half-Open Socket）**：客户端底层的 HTTP/2 或 gRPC 连接池并不知道网络已断，依然在傻等回复。即使你手动在 Clash 里换了节点，旧连接依然处于挂死状态！
- 🚫 **Google 锁区 400 灾难**：盲目选了延迟最低的香港或大陆节点，导致 API 报错 `User location is not supported` 任务崩溃！

**Clash-AI-Watchdog** 就是为了彻底终结这些痛点而生。

---

## ✨ v2.0.0 旗舰版核心特性

- ⚡ **瀑布流真机 TLS 验真 (Waterfall True-Verification)**：自愈切线后 1 秒内通过代理端口向 AI 目标发送真实握手，彻底终结“假绿节点”与 GFW SNI 阻断导致的切线假死循环！
- 🌿 **Zen 极简润物无声模式**：默认双行常驻紧凑状态灯，零多余刷屏，按 `(V)` 键一键在极简守护与全量仪表盘之间自由切换；
- 🚀 **专线/家宽/IEPL 优先加权 & 直连硬拉黑**：源头屏蔽抗封锁能力为 0 的直连节点，专线与家宽优先保驾护航；
- 🖥️ **沉浸式交互 TUI 看板**：原生 ANSI 零闪烁覆盖渲染，集成延迟微波形走势（Sparkline ` ▂▃▅`），极客感十足；
- ⌨️ **单键毫秒级即时操控**：无需按回车，在终端直接按 `(V)` 切换极简/面板、`(R)` 立即换线、`(T)` 链路自检、`(P)` 暂停/继续、`(Q)` 安全退出；
- 🔒 **内核级单实例互斥锁 (Zero-leak Mutex)**：基于 Win32 `CreateMutexW`，由操作系统监管，误多开自动秒退防冲突，绝无死锁残留文件；
- 🛡️ **故障节点隔离冷却池 (Quarantine Pool)**：故障节点自动进入 10 分钟隔离池，配合迟滞评分，根除在不稳定节点间秒级来回震荡；
- 🌐 **三路 AI 端点并发探活**：原生支持 Gemini、Claude、OpenAI 三大核心通道并发健康监测；
- 🔌 **架构解耦 (Proxy Controller Abstraction)**：抽离 `BaseProxyController`，为未来扩展 Sing-box、v2rayN 奠定架构基石。

---

## 🖥️ 终端交互式动态仪表盘 (Interactive TUI)

双击 `run.bat` 或在终端运行 `python main.py`，即刻进入交互式仪表盘：

```text
╔══════════════════════════════════════════════════════════════════════════════════════╗
║  🐕 CLASH-AI-WATCHDOG v2.0            [🟢 监控中]  [可用率: 100.0%]                  ║
║  模式: GEMINI 靶向守护     周期: 30s    代理: http://127.0.0.1:7897                  ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

  【实时代理通路】
  当前活动节点 : 🇹🇼|台湾家宽-IEPL 02        实时延迟: 191ms [极佳]
  延迟微波走势 :  ▂ ▃  ▂ ▂  ▂  ▂ ▂  ▂ ▃ ▂ ▂  (近15次心跳均值: 185ms)
  三路端点状态 : [Gemini: 191ms 🟢]  [Claude: 215ms 🟢]  [OpenAI: 238ms 🟢]

  【自愈与安全池】
  自愈核心防御 : 斩断僵尸连接 (DELETE /connections) · 严防香港/大陆 400 锁区
  今日自愈累计 : 2 次 (22:15 切至 [TW] 台湾家宽 (耗时: 191ms))
  故障隔离冷却 : 无故障隔离节点 (全线健康)

────────────────────────────────────────────────────────────────────────────────────────
  【最近事件记录】
  [23:05:12] [INFO] 心跳探测通过 | Gemini 191ms | Claude 215ms
  [23:05:42] [INFO] 心跳探测通过 | Gemini 188ms | Claude 210ms
────────────────────────────────────────────────────────────────────────────────────────
  [快捷键] (R) 立即换线  │  (T) 链路自检  │  (P) 暂停/继续  │  (Q) 安全退出
────────────────────────────────────────────────────────────────────────────────────────
```

---

## 🚀 快速上手 (Quick Start)

### 1. 环境准备
- 操作系统：Windows / macOS / Linux
- Python 3.7+（仅使用内置标准库，**无需 pip install 任何依赖！**）
- 运行中的 Clash 客户端（**Clash Verge**, **Clash Verge Rev**, **Mihomo Party**, **Clash Nyanpasu**, **Clash for Windows** 等均可，确保启用了 External Controller 控制端）。

### 2. 下载与运行

#### Windows 用户：
```bash
# 1. 克隆本项目
git clone https://github.com/ajin558/clash-ai-watchdog.git
cd clash-ai-watchdog

# 2. 方式 A（交互控制看板）：双击 run.bat 或运行 python main.py
# 方式 B（静默托盘模式）：双击 run_tray.bat
```

#### macOS / Linux 用户：
```bash
git clone https://github.com/ajin558/clash-ai-watchdog.git
cd clash-ai-watchdog
chmod +x run.sh
./run.sh
```

---

## 🖥️ 两种运行模式与控制

| 模式 | 启动方式 | 退出方式 | 特点 |
| :--- | :--- | :--- | :--- |
| **交互控制台模式 (TUI)** | 双击 `run.bat` 或 `python main.py` | 键盘按 `Q` | **推荐**！零闪烁彩色动态仪表盘，Sparkline 走势，单键 `(R)/(T)/(P)/(Q)` 毫秒级操控 |
| **系统托盘模式 (Tray)** | 双击 `run_tray.bat` 或 `python main.py --tray` | 托盘图标右键退出，或双击 `stop.bat` | **无黑窗口打扰**，常驻在任务栏右下角状态指示灯。<br/>支持右键菜单**一键强制换线**、**网络自检**、**暂停守护** |

---

## 🛠️ 常用命令行参数

```bash
# 启动交互动态仪表盘 (默认推荐)
python main.py

# 以系统托盘模式运行（静默后台无窗口）
python main.py --tray

# 执行单次网络诊断与节点测速评估（不进入循环常驻）
python main.py --test

# 查看版本
python main.py -v

# 指定监控目标服务（默认 gemini，可选 claude, openai, google_204）
python main.py --service claude

# 指定首选区域列表（按顺序探测切换）
python main.py --region TW,JP,SG,US

# 指定心跳频率（默认 30 秒）
python main.py --interval 20
```

---

## ⚙️ 配置文件说明 (`config.json`)

运行 `python main.py --gen-config` 即可生成如下默认配置：

```json
{
    "clash_api_base": "auto",            // Clash API 地址，设为 "auto" 将自动扫描发现
    "clash_secret": "",                  // Clash Controller 密钥（若有）
    "mixed_proxy": "auto",               // 本地代理端口，"auto" 自动从 Clash 配置获取

    "target_service": "gemini",          // 探测目标: gemini / claude / openai / google_204
    "check_interval": 30,                // 心跳探测间隔（秒）
    "check_timeout": 8,                  // 探测超时阈值（秒）
    "max_fail_count": 2,                 // 连续失败几次后触发切线自愈

    "preferred_regions": ["TW", "JP", "SG", "KR", "US", "DE", "UK"], // 优先切换地区（涵盖 Gemini/Antigravity 官方支持区）
    "blacklisted_keywords": [            // 垃圾节点与未支持地区过滤词（默认硬封禁 HK/香港、CN、MO、RU，杜绝 400 地区封锁）
        "官网", "到期", "剩余", "流量", "重置", "expire", "notice",
        "HK", "Hong Kong", "HongKong", "香港", "CN", "China", "中国", "RU", "Russia", "俄罗斯"
    ],
    "target_groups": [                   // 托管切换的策略组
        "GLOBAL", "节点选择", "PROXY", "Auto"
    ],
    "notifications": {
        "sound": true,                   // 切换时系统蜂鸣提示
        "desktop_toast": true,           // 桌面气泡弹窗提示 (原生支持免第三方库)
        "webhook_type": "",              // 可选: feishu / dingtalk / wecom / telegram
        "webhook_url": ""                // 报警通知 Webhook 地址
    }
}
```

---

<a name="english-documentation"></a>
## English Documentation

### Overview
**Clash-AI-Watchdog** is an intelligent proxy supervisor and auto-healing watchdog built specifically for autonomous AI Agents (such as Antigravity, Cursor, Claude Code, OpenAI API tools). 

When running long-duration or overnight tasks, network jitter or proxy IP changes often cause **TCP Half-Open socket deadlocks**—leaving your agent hanging indefinitely for 15+ minutes. Clash-AI-Watchdog continuously probes target AI endpoints, dynamically selects the lowest-latency regional node via multi-threaded benchmarking, and **forcibly terminates zombie connections (`DELETE /connections`)**, allowing agents to seamlessly reconnect within milliseconds.

### Highlights
- 🔋 **Zero Token Cost**: Zero LLM completions; strictly low-level network connectivity checks.
- 📦 **Zero Required Dependencies**: Built entirely with Python 3.7+ standard library.
- ⚡ **Instant Zombie Socket Reset**: Drops stale TCP pools, forcing AI agent sockets to reconnect immediately without restarting your editor.
- 🔍 **Auto Port Discovery**: Automatically detects active Clash / Mihomo ports (9097, 9090, 7890, etc.).
- 🌐 **Multi-AI Presets**: Native health check targets for Gemini, Claude, and OpenAI.
- 🛡️ **Smart Geo-Fencing & Wide Region Pool**: Out-of-the-box support for 200+ Gemini-supported regions (TW, JP, SG, KR, US, DE, UK). Automatically hard-blacklists unsupported regions (HK, CN, RU) to avoid catastrophic `User location is not supported` HTTP 400 errors.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
