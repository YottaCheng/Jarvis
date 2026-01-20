import os
from dotenv import load_dotenv
from google import genai

# 加载环境变量
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_KEY:
    print("❌ 没找到 Key，请检查 .env")
    exit()

print("🕵️‍♂️ 正在潜入 Google 服务器拉取模型清单...")

client = genai.Client(api_key=GEMINI_KEY)

try:
    # 遍历所有可用模型
    # 我们只关心包含 "gemini" 的模型
    print(f"{'API 模型 ID (请复制这个)':<40} | {'显示名称'}")
    print("-" * 60)
    
    for m in client.models.list():
        # 这里的 .name 就是我们要填进 main.py 的真实 ID
        if "gemini" in m.name:
            print(f"{m.name:<40} | {m.display_name}")

except Exception as e:
    print(f"❌ 拉取失败: {e}")