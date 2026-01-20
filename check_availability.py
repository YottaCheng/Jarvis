import os
from google import genai
from dotenv import load_dotenv

# 加载 .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 错误：未找到 GEMINI_API_KEY")
    exit()

client = genai.Client(api_key=api_key)

# 🎯 目标：挖地三尺找出一个能用的 2.0/Lite
# Google 有时候会给特定版本号（比如 -001）单独的配额
CANDIDATES = [
    # --- 你的“全家桶”清单 ---
    "gemini-2.0-flash",                 # 标准版 (已知 429)
    "gemini-2.0-flash-001",             # 版本号锁定版
    "gemini-2.0-flash-lite",            # 轻量版 (重点关注！)
    "gemini-2.0-flash-lite-001",        # 轻量版-001
    "gemini-2.0-flash-lite-preview",    # 轻量预览
    "gemini-2.0-flash-lite-preview-02-05", # 2月5日特定版
    
    # --- 顺便再测一次 1.5 的特定版本 (死马当活马医) ---
    "gemini-1.5-flash-001",             # 1.5 的老版本
    "gemini-1.5-flash-002",             # 1.5 的新版本
    "gemini-1.5-flash-8b",              # 1.5 极速版 (8B参数)
    
    # --- 对照组 (已知存活) ---
    "gemini-2.5-flash"                  # 既然它活了，我们要确认它是不是真的稳
]

print(f"🕵️‍♂️ 深度审计 2.0/Lite 系列权限 (Region: UK)...\n")
print(f"{'MODEL ID':<35} | {'STATUS':<10} | {'RESPONSE'}")
print("-" * 75)

for model in CANDIDATES:
    try:
        # 发送极短请求
        response = client.models.generate_content(
            model=model,
            contents="ping",
        )
        # 截取前20个字符，防止刷屏
        reply = response.text.strip().replace('\n', ' ')[:20] if response.text else "EMPTY_TEXT"
        print(f"✅ {model:<35} | ALIVE      | {reply}...")
    
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Quota" in err_str:
            print(f"⚠️ {model:<35} | 429 LIMIT  | 配额 0 / 已满")
        elif "404" in err_str or "Not Found" in err_str:
            print(f"❌ {model:<35} | 404 NULL   | 咱们区没这个模型")
        elif "403" in err_str:
            print(f"🚫 {model:<35} | 403 BAN    | 权限被锁")
        else:
            # 打印未知错误的前30个字符
            print(f"❓ {model:<35} | ERROR      | {err_str[:30]}...")