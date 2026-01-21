# main.py
import sys
import os
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# --- 🚀 启动阶段 1: 神经选择 (暂时注释) ---
"""
print("💻 Booting Interface...")
try:
    from launcher import get_user_selection
    selected_model = get_user_selection()
    if not selected_model:
        sys.exit(0)
    os.environ["JARVIS_MODEL_OVERRIDE"] = selected_model
except ImportError:
    pass
except Exception:
    pass
"""

# --- 🚀 启动阶段 2: 核心加载 ---
print("DEBUG: Loading Core Systems...")
from config import settings 
from core import agent
from services.spinal_cord import spinal_loop 
from utils.logger import setup_logger
# 🔥 必须加这一句，这是新的统一入口
from utils.diagnostic import run_diagnostics 

logger = setup_logger("Bootstrapper")

def system_startup_check():
    """
    系统自检流程
    """
    print("DEBUG: 正在进行系统自检...")
    logger.info("🛡️  Initiating Pre-flight Self-Diagnostic...")
    
    # 🔥 改用这个新函数，它在 diagnostic.py 里把所有检查项（包括 Formatter）都跑一遍
    if run_diagnostics():
        logger.info("✅ All Systems Nominal.")
        return True
    else:
        logger.critical("❌ Startup Aborted: Diagnostics Failed.")
        return False

if not (settings.SLACK_BOT_TOKEN and settings.GEMINI_KEY):
    print("❌ 错误：.env 密钥缺失")
    sys.exit(1)

# 执行自检
if not system_startup_check():
    sys.exit(1)

app = App(token=settings.SLACK_BOT_TOKEN)

@app.message("")
def handle_message(message, say):
    if message.get('bot_id'): return
    say("Thinking...")
    # 这里调用的是已经适配好 formatter 的 agent
    reply = agent.run(message['text'], message['user'])
    say(reply)

if __name__ == "__main__":
    logger.info(f"⚡️ Jarvis Online | Brain: {settings.MODEL_ID}")
    
    # 初始化状态机
    from core.state import StateManager
    state_engine = StateManager()
    
    # 🔥 [测试] 启动时重置一下状态
    state_engine.update_energy("UNKNOWN") 
    print(f"DEBUG: Current Focus Mode -> {state_engine.get_state()['strategic_mode']['current_focus']}")
    
    # 启动脊椎 (定时任务)
    spinal_thread = threading.Thread(target=spinal_loop, daemon=True)
    spinal_thread.start()
    """
    logger.info("⚡️ Boot-up Energy Check...")
    
    from services.energy_audit import perform_energy_audit
    threading.Thread(target=perform_energy_audit, daemon=True).start()
    """
    
    try:
        SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()
    except KeyboardInterrupt:
        print("🛑 系统关闭")