# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- 🔑 密钥配置 ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

OWNER_ID = "U0A9B5ETMFF"

# --- 📁 文件路径 ---
MEMORY_FILE = DATA_DIR / "memory.json"
STATE_FILE = DATA_DIR / "user_state.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

# --- 🧠 模型战略配置 (Strategic Model Config) ---

# 1. [Router / 小脑] 
# 负责闲聊、意图识别。保持使用 Gemma 3 27B
ROUTER_MODEL = "models/gemma-3-27b-it"

# 2. [Cortex Tiers / 日常跑腿梯队] 
# 用于 Agent 的日常工具调用、回复 Slack。
# 逻辑：自动轮换，抗 RPD 限制。
MODEL_TIERS = [
    "models/gemini-2.5-flash",                  # 主力：最稳
    "models/gemini-2.5-flash-lite",             # 替补：极快
    "models/gemini-2.5-flash-preview-09-2025",  # 备用 1
    "models/gemini-2.5-flash-lite-preview-09-2025", # 备用 2
    "models/gemini-pro-latest"                  # 兜底：旧版 Pro
]

# 3. [Audit / 核武器] 
# 仅用于晚间深度审计、周报分析。绝不放入自动轮换队列。
AUDIT_MODELS = {
    "PRO": "models/gemini-3-pro-preview",       # 深度推理
    "FLASH": "models/gemini-3-flash-preview"    # 快速审计
}

# 默认 MODEL_ID (兼容旧代码引用，指向主力模型)
MODEL_ID = MODEL_TIERS[0]

# --- 🏆 优先级定义 ---
TIERS = {
    "CRITICAL": "Tier 0: Job/PSW Visa",
    "HIGH": "Tier 1: UCL Academia",
    "MAINTENANCE": "Tier 2: Gym/entrepreneur"
}