Project Jarvis: Refactoring & Persistence Specification (v2.1)
Objective: 从“单文件脚本 (Script)”进化为“模块化系统 (System)”。 Core Value: Robustness (鲁棒性), Persistence (持久记忆), Modularity (模块化). Target Timeline: Today (13:00 - 15:30 @ Covent Garden).

🏗 Section 1: Directory Structure (工程蓝图)
现状: 所有逻辑堆在 main.py，牵一发而动全身。 目标: 职责分离 (Separation of Concerns)。

请严格按照以下目录结构创建文件夹和文件：

Plaintext
Jarvis/
├── .env                    # [Config] API Keys (GitIgnore)
├── main.py                 # [Entry] 只负责启动 Slack 监听和调度器 (Lines < 50)
├── config.py               # [Config] 全局常量 (Tier 定义, ID, Paths)
│
├── core/                   # --- 大脑区 (The Brain) ---
│   ├── __init__.py
│   ├── agent.py            # 核心思考逻辑 (agent_run)
│   ├── memory.py           # 记忆管理 (读写 memory.json)
│   └── prompts.py          # System Prompts & Personas
│
├── services/               # --- 手脚区 (The Hands) ---
│   ├── __init__.py
│   ├── google_ops.py       # Calendar/Gmail API (原 fetch_context/create_event)
│   └── slack_ops.py        # (Optional) 复杂的 Slack 消息格式处理
│
├── data/                   # --- 记忆区 (The Hippocampus) ---
│   └── memory.json         # 持久化存储 (自动生成，GitIgnore)
│
└── utils/                  # --- 工具区 (Utils) ---
    └── logger.py           # 统一日志配置
🧠 Section 2: Component Specifications (组件规范)
2.1 Core Module: Memory Persistence (core/memory.py)

优先级: P0 (Critical) 痛点解决: 重启电脑不失忆。 逻辑:

Storage: 不再使用 deque 变量，而是读写 data/memory.json。

Schema:

JSON
{
  "U0A9B5ETMFF": [
    {"role": "User", "content": "我要去 Covent Garden", "timestamp": "..."},
    {"role": "Jarvis", "content": "收到，已记录。", "timestamp": "..."}
  ]
}
Functions:

load_history(user_id): 启动时读取文件。

save_history(user_id, role, content): 每次对话后立即 json.dump 写入硬盘。

prune_history(limit=20): 防止 Token 爆炸，只保留最近 20 轮。

2.2 Core Module: Prompts (core/prompts.py)

优先级: P1 逻辑:

将 main.py 里那个巨大的 system_prompt 字符串移到这里。

定义 Tier 0/1/2 常量，方便修改。

Vibe Check: 在这里预埋 "Answer in Chinese" 和 "No Bolding" 的指令。

2.3 Services Module: Google Operations (services/google_ops.py)

优先级: P1 逻辑:

迁移原 get_google_service。

迁移原 fetch_context (升级版，含 UCL 课表扫描)。

迁移原 create_schedule_event。

新增: check_gmail_jobs() (为后续 Job Hunting 做预留)。

2.4 Entry Point: Main Controller (main.py)

逻辑:

极简主义: 只做 import 和启动。

流程:

app = App(token=...)

scheduler.start()

SocketModeHandler(app).start()

它不再包含任何业务逻辑，只负责把 Slack Event 转发给 core.agent.run()。

📅 Section 3: Execution Roadmap (执行步骤)
按此顺序执行，切勿跳跃。

Phase 1: Decoupling (外科手术 - 解耦)

Time: 13:00 - 14:00 Goal: 把代码拆分进文件夹，保证程序还能跑。

创建文件夹: 建立 core, services, data 目录。

迁移 Prompt: 创建 core/prompts.py，粘贴 System Prompt。

迁移 Google: 把 google_ops.py 移动到 services/，并确保 fetch_context 逻辑完整。

修正 Import: 在 main.py 里修改引用路径 (e.g., from services.google_ops import ...)。

Phase 2: Persistence (海马体植入 - 持久化)

Time: 14:00 - 15:00 Goal: 实现掉电不失忆。

编写 core/memory.py:

实现 JSON 读写逻辑。

实现 get_recent_chat(user_id) 返回格式化文本。

接入 Agent:

在 core/agent.py 中，调用 memory.save_history 替代原来的 deque.append。

Phase 3: Stress Test (压力测试)

Time: 15:00 - 15:30 Goal: 确保 Robustness。

重启测试: 关闭终端，重新运行。问它：“我刚才说要去哪？”，看它能否回答“Covent Garden”。

断网测试: 拔掉 Wi-Fi 运行，确保程序捕获 Exception 并打印错误日志，而不是直接 Crash。

🛡 Section 4: Operational Protocols (运行协议)
Robustness Rule: 所有的 API 调用 (Google/Gemini/Slack) 必须包裹在 try...except 中。禁止裸奔。

Privacy Rule: memory.json 必须加入 .gitignore，严禁上传 GitHub。

Feedback Rule: 既然现在是 Vibe Coding，每完成一个 Phase，去买一杯咖啡或奖励自己 10 分钟休息。