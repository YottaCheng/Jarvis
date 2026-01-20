import sys
import os
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
# 注意：配置和日志要晚一点引入，等环境变量设置好
"""
# --- 🚀 启动阶段 1: 神经选择 ---
print("💻 Booting Interface...")
try:
    from launcher import get_user_selection
    selected_model = get_user_selection()
    
    if not selected_model:
        print("❌ 启动取消 (User Abort)")
        sys.exit(0)
        
    # 🔥 注入环境变量
    os.environ["JARVIS_MODEL_OVERRIDE"] = selected_model
    print(f"🚀 Neural Pathway Locked: {selected_model}")
    
except ImportError:
    print("⚠️ Launcher not found, using default settings.")
except Exception as e:
    print(f"⚠️ UI Error: {e}, passing...")
"""
# --- 🚀 启动阶段 2: 核心加载 ---
print("DEBUG: Loading Core Systems...")
from config import settings # 现在 import，能读到刚才注入的变量
from core import agent
from services.spinal_cord import spinal_loop 
from utils.logger import setup_logger
from utils.diagnostic import check_structure, check_memory_io, check_google_api, check_brain

logger = setup_logger("Bootstrapper")

def system_startup_check():
    print("DEBUG: 正在进行系统自检...")
    logger.info("🛡️  Initiating Pre-flight Self-Diagnostic...")
    checks = [
        ("FileSystem", check_structure),
        ("Memory I/O", check_memory_io),
        ("Google API", check_google_api),
        ("Gemini Brain", check_brain)
    ]
    for name, check_func in checks:
        logger.info(f"   Running check: {name}...")
        try:
            if not check_func():
                logger.critical(f"❌ Startup Aborted: {name} Check Failed.")
                return False
        except Exception as e:
            logger.critical(f"❌ Critical Error during {name} check: {e}")
            return False
    logger.info("✅ All Systems Nominal.")
    return True

if not (settings.SLACK_BOT_TOKEN and settings.GEMINI_KEY):
    print("❌ 错误：.env 密钥缺失")
    sys.exit(1)

# 如果想跳过自检快速启动，注释下面两行
if not system_startup_check():
    sys.exit(1)

app = App(token=settings.SLACK_BOT_TOKEN)

@app.message("")
def handle_message(message, say):
    if message.get('bot_id'): return
    say("Thinking...")
    reply = agent.run(message['text'], message['user'])
    say(reply)

if __name__ == "__main__":
    logger.info(f"⚡️ Jarvis Online | Brain: {settings.MODEL_ID}")
    from core.state import StateManager
    state_engine = StateManager()

    # 🔥 [测试] 启动时重置一下状态
    state_engine.update_energy("UNKNOWN") 
    print(f"DEBUG: Current Focus Mode -> {state_engine.get_state()['strategic_mode']['current_focus']}")
    
    spinal_thread = threading.Thread(target=spinal_loop, daemon=True)
    spinal_thread.start()
    
    try:
        SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()
    except KeyboardInterrupt:
        print("🛑 系统关闭")