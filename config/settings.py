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

# 🔥 核心：接收 Launcher 注入的环境变量
# 默认值设为 gemini-2.5-flash (因为你测出来这个能用)
MODEL_ID = os.getenv("JARVIS_MODEL_OVERRIDE", "gemini-2.5-flash")

MEMORY_FILE = DATA_DIR / "memory.json"
STATE_FILE = DATA_DIR / "user_state.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

TIERS = {
    "CRITICAL": "Tier 0: Job/PSW Visa",
    "HIGH": "Tier 1: UCL Academia",
    "MAINTENANCE": "Tier 2: Gym/entrepreneur"
}