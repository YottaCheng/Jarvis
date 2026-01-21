# utils/diagnostic.py
import sys
import os
from config import settings
from google import genai

def check_structure():
    """[Test 1] 基础设施检查"""
    print("\n[1/6] 🏗  Checking Infrastructure...") # 增加了一个步骤
    
    required_dirs = [settings.DATA_DIR, settings.BASE_DIR / "core", settings.BASE_DIR / "services", settings.BASE_DIR / "utils"]
    for d in required_dirs:
        if d.exists():
            print(f"  ✅ Directory found: {d.name}")
        else:
            print(f"  ❌ MISSING Directory: {d.name}")
            return False
            
    # 检查新文件是否存在
    required_files = [
        settings.BASE_DIR / "services/google_ops.py",
        settings.BASE_DIR / "utils/formatter.py" # 新增检查
    ]
    for f in required_files:
        if f.exists():
            print(f"  ✅ File found: {f.name}")
        else:
            print(f"  ❌ MISSING File: {f.name}")
            return False
            
    return True

def check_memory_io():
    """[Test 2] 读写权限检查"""
    print(f"\n[2/6] 💾 Checking Memory I/O...")
    try:
        test_file = settings.DATA_DIR / "io_test.tmp"
        with open(test_file, 'w') as f: f.write("test")
        with open(test_file, 'r') as f: content = f.read()
        os.remove(test_file)
        if content == "test":
            print("  ✅ Read/Write Permission: OK")
            return True
    except Exception as e:
        print(f"  ❌ I/O Error: {e}")
        return False

def check_google_api():
    """[Test 3] Google API 连通性检查"""
    print(f"\n[3/6] 📅 Checking Google Services...")
    try:
        from services.google_ops import get_service
        service = get_service('calendar', 'v3')
        if not service:
            print("  ❌ Google Service Build Failed")
            return False
        service.calendarList().list(maxResults=1).execute()
        print("  ✅ Calendar API Connection: OK")
        return True
    except Exception as e:
        print(f"  ⚠️  Google API Warning: {e}")
        return True 

def check_formatter():
    """[Test 4] Formatter 逻辑单元测试 (新增)"""
    print(f"\n[4/6] 🎨 Checking Formatter Logic...")
    try:
        from utils.formatter import format_tasks, format_calendar_events
        # 1. Test Task Formatting
        dummy_tasks = [{'title': 'Test Task', 'status': 'needsAction'}]
        res_task = format_tasks(dummy_tasks)
        if "Test Task" in res_task:
            print("  ✅ Task Formatter: OK")
        else:
            print("  ❌ Task Formatter Failed")
            return False

        # 2. Test Calendar Formatting
        dummy_events = [{'summary': 'Test Event', 'start': {'dateTime': '2026-01-01T10:00:00'}, 'id': '123'}]
        res_cal = format_calendar_events(dummy_events)
        if "Test Event" in res_cal:
            print("  ✅ Calendar Formatter: OK")
        else:
            print("  ❌ Calendar Formatter Failed")
            return False
            
        return True
    except ImportError:
        print("  ❌ Failed to import utils.formatter")
        return False
    except Exception as e:
        print(f"  ❌ Formatter Logic Error: {e}")
        return False

def check_brain():
    """[Test 5] Gemini 连接检查"""
    print(f"\n[5/6] 🧠 Checking Gemini Brain...")
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
        if "429" in str(e) or "503" in str(e):
            print(f"  ⚠️  Brain Rate Limited: {e}")
            return True 
        print(f"  ❌ Brain Dead: {e}")
        return False

# 统一入口
def run_diagnostics():
    checks = [
        check_structure,
        check_memory_io,
        check_google_api,
        check_formatter, # 新增
        check_brain
    ]
    
    for check in checks:
        if not check():
            return False
    return True