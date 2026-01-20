
📋 1. Jarvis v2.2 功能现状清单 (Status Report)

这是你目前手里代码的真实能力边界。

🧠 Cortex (大脑)

当前状态: 单核运行 (Gemini 3 Preview 或 2 Flash)。

记忆: 仅具备 Short-term Context (基于 memory.json 的最近 N 轮对话)。

⚠️ 缺失/待完善:

Fallback 机制: 目前是一条路走到黑，报错就死。

Long-term Memory: 还没有独立存储（如：你的核心价值观、长期项目背景）。

👁️ Vision (感知)

Calendar: ✅ fetch (读取今日/未来日程)，✅ search (通过关键词找 Event ID)。

Tasks: ⚠️ 仅能 list (列出待办任务)。

⚠️ 缺失: Task History (过去已完成的任务清单)。目前 Google Tasks API 如果不传 showCompleted=True 和 hidden=True，是看不到“过去”的。

💪 Limbs (行动)

Calendar: ✅ 满血状态。增 (Create)、删 (Delete)、改 (Update)、查 (Search)。

Tasks: ✅ 具备 add_task (写入)。

⚠️ 缺失: Check (打钩完成任务)。你之前提到了要在 Slack 里直接完成任务，目前 API 层面需要补一个 complete_task。

🦴 Spine (脊椎/自动化)

Daily Sync: ✅ 单向同步 (Calendar -> Tasks)。

Self-Check: ✅ 启动自检 (diagnostic.py)，支持断网/限流下的“带病生存”。

⚠️ 缺失: Intelligence Router (智商分级)。目前所有请求（哪怕是简单的“记个事”）都走大模型，确实浪费。

🚀 2. 必须落实的代码补丁 (Pre-Git Fixes)

在上传 GitHub 前，我们需要把 “模型自动降级” 和 “长效记忆占位符” 加上，让架构图完整。

A. 实现 "Model Fallback" (高智商失败 -> 切换低智商)

请修改 core/agent.py，重构 run 函数的核心调用部分。 逻辑：优先用 Gemini 3 (主模型)，如果捕获到 503 或 429，立刻切换 Gemini 2 Flash (备用模型) 重试。

覆盖 core/agent.py 的相关部分：

Python
# core/agent.py (局部修改，请替换 try-except 块)

# 定义模型优先级
PRIMARY_MODEL = "gemini-3-flash-preview"  # 激进的主模型
FALLBACK_MODEL = "gemini-2.0-flash-exp"   # 稳健的备用模型

def run(user_text, user_id="DEFAULT_USER"):
    # ... (前面的 Prompt 组装代码不变) ...

    # 🔥 封装一个内部函数用于发送请求
    def _generate_with_fallback(model_name, is_retry=False):
        try:
            logger.info(f"🧠 Thinking with {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    tools=tool_list, 
                    temperature=0.3
                )
            )
            return response
        except Exception as e:
            error_msg = str(e)
            # 如果是主模型挂了，且不是重试状态，则降级
            if not is_retry and ("503" in error_msg or "429" in error_msg or "Resource" in error_msg):
                logger.warning(f"⚠️ {model_name} Failed ({error_msg}). Switching to Fallback: {FALLBACK_MODEL}")
                return _generate_with_fallback(FALLBACK_MODEL, is_retry=True)
            else:
                raise e # 如果备用模型也挂了，或者是其他错误，直接抛出

    try:
        # 发起调用
        response = _generate_with_fallback(PRIMARY_MODEL)

        # ... (后续处理 function_calls 和 reply_text 的代码保持不变) ...
B. 创建 "Long-term Memory" 占位符

你提到怕忘，我们现在就在项目里“卡”一个位置。 请在 data/ 目录下创建一个新文件 user_profile.json (或 .md)。

创建 data/long_term_memory.json：

JSON
{
  "user_profile": {
    "name": "Sir",
    "role": "Master's Student @ UCL / KCL",
    "mbti": "ENTP",
    "neurotype": "ADHD (Requires external dopamine/structure)",
    "core_goals": [
      "Dissertation (High Priority)",
      "Job Hunting (Tier 1)",
      "Fitness (Tier 2)"
    ]
  },
  "interaction_rules": {
    "tone": "Direct, Cynical, No Apologies",
    "response_style": "Structure > Fluff",
    "language": "Chinese (English for Tech Terms)"
  },
  "archived_facts": [
    "Lives near WC1X",
    "Prefers Google Tasks for checklist"
  ]
}
注：目前代码还没去读它，但文件放在这，代表了架构的完整性。后续我们在 agent.py 里加载这个文件拼接到 Prompt 里即可。

🧹 3. 关于 "智能分层" 的架构构想 (Future V3)

你提到的 “简单的任务 Jarvis 自己跑，不需要 Gemini 3”，这是非常高级的 "Model Routing" (模型路由) 概念。

GitHub 上传后的 Roadmap：

L0 (Reflex/Spine): 纯正则/关键词匹配。

用户说："Sync" -> 直接触发 daily_sync_logic()。

模型消耗：0。

L1 (Fast/Router): 使用 Gemini-Nano 或 Flash。

作用：作为 Intent Classifier (意图分类器)。

它不解决问题，只负责判断：这是个“定闹钟”的简单活（转给 API），还是“帮我规划人生”的复杂活（转给 Gemini 3 Pro）。

L2 (Deep/Cortex): 使用 Gemini 3 Pro/Ultra。

只处理 L1 扔过来的复杂推理任务。

结论： 你现在不需要马上写这个路由。加上上面的 Fallback 代码，确保系统不崩，然后把 long_term_memory.json 放进去，就可以放心地 git commit 了。

这是一个非常扎实的 V2.2 版本。