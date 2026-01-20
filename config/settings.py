# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

OWNER_ID = "U0A9B5ETMFF"

# 🔥 [Cortex / 大脑]
# 处理复杂任务 (工具调用、长逻辑)，继续使用你刚才测试通过的 Gemini 2.5
MODEL_ID = os.getenv("JARVIS_MODEL_OVERRIDE", "models/gemini-2.5-flash")

# 🔥 [Router / 小脑] 
# 处理闲聊、意图识别。使用你刚确认的 Gemma 3 27B
ROUTER_MODEL = "models/gemma-3-27b-it"

MEMORY_FILE = DATA_DIR / "memory.json"
STATE_FILE = DATA_DIR / "user_state.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

TIERS = {
    "CRITICAL": "Tier 0: Job/PSW Visa",
    "HIGH": "Tier 1: UCL Academia",
    "MAINTENANCE": "Tier 2: Gym/entrepreneur"
}