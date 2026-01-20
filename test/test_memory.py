import sys
import os
import json

# --- 1. 环境这一步是为了让 test 能引用到 core 模块 ---
# 把项目根目录加入 Python 搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import save_history, load_history
from config import settings

def run_test():
    print(f"{'='*40}")
    print("🧪 UNIT TEST: Memory Persistence")
    print(f"{'='*40}")

    # 定义一个测试专用的 User ID，防止污染你的真实记忆
    TEST_USER_ID = "UNIT_TEST_DUMMY"
    
    # [Step 1] 清理旧环境 (Setup)
    print("\n[Setup] Cleaning up previous test data...")
    if settings.MEMORY_FILE.exists():
        with open(settings.MEMORY_FILE, 'r') as f:
            data = json.load(f)
        if TEST_USER_ID in data:
            del data[TEST_USER_ID]
            with open(settings.MEMORY_FILE, 'w') as f:
                json.dump(data, f)
    print("  ✅ Cleaned.")

    # [Step 2] 测试写入 (Action: Write)
    print("\n[Action] Writing conversation...")
    try:
        save_history(TEST_USER_ID, "User", "Test Message 1: Apple")
        save_history(TEST_USER_ID, "Jarvis", "Test Reply 1: Banana")
        print("  ✅ Write executed without error.")
    except Exception as e:
        print(f"  ❌ Write Failed: {e}")
        return

    # [Step 3] 测试读取 (Action: Read)
    print("\n[Action] Reading history back...")
    history_text = load_history(TEST_USER_ID)
    print(f"  --> Output Context:\n{'-'*20}\n{history_text.strip()}\n{'-'*20}")

    # [Step 4] 断言验证 (Assertion)
    print("\n[Assertion] Verifying data integrity...")
    
    # 验证关键信息是否存在
    condition_1 = "Test Message 1: Apple" in history_text
    condition_2 = "Test Reply 1: Banana" in history_text
    # 验证时间戳格式是否正确 (简单检查是否包含 2026)
    condition_3 = "2026" in history_text

    if condition_1 and condition_2 and condition_3:
        print("  ✅ PASS: Data matches exactly.")
    else:
        print("  ❌ FAIL: Data mismatch or lost.")
        print(f"     Expected 'Apple' & 'Banana', found: {history_text}")

if __name__ == "__main__":
    run_test()