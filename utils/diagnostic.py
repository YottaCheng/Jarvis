import sys
import os
from config import settings
from google import genai

def check_structure():
    """检查目录结构和关键文件"""
    print("\n[1/5] 🏗  Checking Infrastructure...")
    
    required_dirs = [settings.DATA_DIR, settings.BASE_DIR / "core", settings.BASE_DIR / "services"]
    for d in required_dirs:
        if d.exists():
            print(f"  ✅ Directory found: {d.name}")
        else:
            print(f"  ❌ MISSING Directory: {d.name}")
            return False

    required_files = [settings.CREDENTIALS_FILE, settings.BASE_DIR / ".env"]
    for f in required_files:
        if f.exists():
            print(f"  ✅ File found: {f.name}")
        else:
            print(f"  ❌ MISSING File: {f.name}")
            return False
            
    if settings.TOKEN_FILE.exists():
        print(f"  ✅ File found: token.json")
    else:
        print(f"  ⚠️  Notice: token.json missing (Will be generated during auth)")
        
    return True

def check_memory_io():
    """检查记忆文件读写权限"""
    print(f"\n[2/5] 💾 Checking Memory I/O...")
    try:
        test_file = settings.DATA_DIR / "io_test.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        with open(test_file, 'r') as f:
            content = f.read()
        os.remove(test_file)
        
        if content == "test":
            print("  ✅ Read/Write Permission: OK")
            return True
    except Exception as e:
        print(f"  ❌ Storage Error: {e}")
        return False
    return False

def check_google_api():
    """检查 Google API 连接 (Calendar)"""
    print(f"\n[3/5] 📅 Checking Google Services...")
    try:
        from services.google_ops import get_service
        service = get_service('calendar', 'v3')
        if not service:
            print("  ❌ Google Service Build Failed")
            return False
        
        # 尝试列出日历作为 Ping
        service.calendarList().list(maxResults=1).execute()
        print("  ✅ Calendar API Connection: OK")
        return True
    except Exception as e:
        print(f"  ⚠️  Google API Warning: {e}")
        # API 偶尔连不上不应该阻止启动，可能是 token 过期，启动后可以重连
        return True 

def check_brain():
    """
    检查 Gemini 连接
    🔥 降级策略：如果大脑限流 (429)，允许系统启动，只运行脊椎功能。
    """
    print(f"\n[4/5] 🧠 Checking Gemini Brain...")
    try:
        client = genai.Client(api_key=settings.GEMINI_KEY)
        response = client.models.generate_content(
            model=settings.MODEL_ID,
            contents="Ping",
        )
        if response.text:
            print("  ✅ Gemini Response: Pong")
            return True
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            print(f"  ⚠️  Brain Rate Limited (429): Quota exceeded for {settings.MODEL_ID}")
            print("  👉 System will launch in [Spinal Cord Only] mode.")
            return True # <--- 关键修改：即使报错也放行
        else:
            print(f"  ❌ Gemini Error: {error_str}")
            # 如果是 Key 错误等硬伤，还是得拦截
            if "API_KEY" in error_str:
                return False
            return True # 其他网络错误暂且放行
    return False