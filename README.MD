Jarvis V3.1: Bio-Inspired Task Executive Agent
Project Overview

Jarvis V3.1 是一款基于 Stateful Agent（有状态智能体） 架构设计的私人助理。不同于传统的指令式 AI，本项目引入了基于人类生理状态（Energy Level）的决策引擎，实现了从“工具助理”向“主动管家”的跨越。

🏗 核心架构说明 (System Architecture)

系统采用解耦的四层架构，确保了逻辑的鲁棒性与可扩展性：

1. 神经中枢层 (Core Intelligence)

Neural Router (小脑)：基于 Gemini 2.5/3 Flash。引入短期对话上下文（Contextual Memory），精准识别用户意图。负责处理即时查询与闲聊，并决定是否将指令上交给大脑。

Cortex Agent (大脑)：系统最高决策机构。具备完整的 Tool-calling 能力，支持对 Google Calendar 与 Tasks 的深度操作。

Priority Dispatcher (分发逻辑)：核心 Prompt 注入了 Tier Logic。系统会根据当前 Energy Level 动态过滤任务，低电量模式下将强制拦截非关键路径（Tier 1/2）的任务。

2. 自主反射层 (Autonomous Services)

Energy Audit System (精力审计)：

Tactical Mode (早/午)：调用 Gemini 3 Flash，通过自然语言处理分析用户语气、任务进度及情绪波动。

Strategic Mode (晚间)：调用 Gemini 3 Pro，进行全天候行为审计与优先级平衡复盘。

Ratchet Supervision (棘轮监督)：无状态定时轮询机制。每 10 分钟扫描任务状态，对逾期未完成的 Tier 0/1 任务触发强制性督办。

Spinal Cord (脊椎)：负责系统级定时任务，包括清晨的动态唤醒规划与跨平台数据同步。

3. 基础设施层 (Infrastructure)

Resilient Container：单例 Client 容器，内置 Multi-Tier RPD Rotation（多级模型轮换） 机制，确保在 API 触发限流或 503 错误时自动降级切换。

Data Sanitation Layer：统一的 google_ops 纯数据接口与 formatter 表现层分离，确保 LLM 接收的是结构化、高信噪比的原始信息。

🛠 功能模块清单 (Functional Features)

功能	描述	技术栈
动态电量感应	自动从对话语气中推断疲劳度并调整系统语气与建议强度	Gemini 3 Flash + StateManager
接力监督系统	任务结束后 1 小时自动核查，未闭环则触发 Slack 预警	Python Schedule + Google API
上下文感知路由	具备 3 轮以上的短期记忆，支持代词指代与连续逻辑推理	Context-Aware Prompting
抗压模型轮换	自动在 Gemini 3、2.5 Flash 及 Pro 系列间根据可用性切换	Singleton Container
动态闹钟策略	根据当日首项关键日程，自动计算并设定最优唤醒时间	Spinal Cord Loop
📂 文件结构 (File Map)

Plaintext
Jarvis/
├── config/
│   └── settings.py          # 模型梯队与全局配置
├── core/
│   ├── container.py         # 核心容器（抗RPD逻辑）
│   ├── router.py            # 意图路由器
│   ├── agent.py             # 决策大脑
│   ├── prompts.py           # 提示词库（Logic Center）
│   └── state.py             # 状态机引擎
├── services/
│   ├── google_ops.py        # 纯数据读写层
│   ├── spinal_cord.py       # 定时任务引擎
│   └── energy_audit.py      # 精力审计模块
├── utils/
│   ├── formatter.py         # 数据排版器
│   └── diagnostic.py        # 系统自检工具
└── main.py                  # 系统主入口
🚀 部署状态 (Deployment)

Current Version: v3.1-stable

Platform: Local Terminal / MacOS Environment

Next Milestone: Docker Containerization & Cloud Deployment