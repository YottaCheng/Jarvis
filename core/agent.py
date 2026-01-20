# core/agent.py
import json
from google import genai
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.prompts import get_system_prompt
from core.router import NeuralRouter  # <--- 🔥 新增：引入路由模块
from services.google_ops import (
    fetch_calendar_context, create_schedule_event, 
    search_calendar_events, update_schedule_event, delete_schedule_event,
    add_task_tool, list_tasks_tool
)
from core.memory import load_history, save_history

logger = setup_logger("AgentCore")
client = genai.Client(api_key=settings.GEMINI_KEY)

# 主大脑模型 (Gemini 2.5)
CORTEX_MODEL = settings.MODEL_ID

# --- 🛠️ 工具定义 (保持原样，严格类型检查) ---

def create_event_tool_wrapper(summary: str, start_time: str = None, duration_hours: float = 1.0, reason: str = ""):
    """创建日程"""
    if not start_time: 
        import datetime
        start_time = datetime.datetime.now().isoformat()
    return create_schedule_event(summary, start_time, duration_hours, description=reason)

def search_calendar_tool_wrapper(query: str):
    """搜索日程"""
    return search_calendar_events(query)

def update_event_tool_wrapper(event_id: str, new_start_time: str = None, new_summary: str = None):
    """更新日程"""
    return update_schedule_event(event_id, new_start_time, new_summary)

def delete_event_tool_wrapper(event_id: str):
    """删除日程"""
    return delete_schedule_event(event_id)

def add_task_tool_wrapper(title: str, notes: str = None):
    """添加待办"""
    return add_task_tool(title, notes)

def list_tasks_tool_wrapper():
    """列出待办"""
    return list_tasks_tool()

def load_user_profile():
    profile_path = settings.DATA_DIR / "user_profile.json"
    if profile_path.exists():
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f), indent=2, ensure_ascii=False)
        except Exception: return ""
    return ""

# --- 🧠 核心运行逻辑 (双脑协同) ---

def run(user_text, user_id="DEFAULT_USER"):
    # =================================================
    # Layer 1: The Neural Router (小脑 / 潜意识)
    # =================================================
    try:
        logger.info(f"🏎️  Router Layer Active: {settings.ROUTER_MODEL} (Checking Intent...)")
        
        router = NeuralRouter()
        # 这里的 fast_response 如果有值，说明是闲聊；如果是 None，说明需要大脑
        fast_response = router.route_and_execute(user_text)
        
        if fast_response:
            logger.info("🟢 Router Hit: Fast Path executed.")
            # 记录小脑的回复
            save_history(user_id, "User", user_text)
            save_history(user_id, "Jarvis", fast_response)
            return fast_response

    except Exception as e:
        logger.warning(f"⚠️ Router Skipped (Error: {e}). Fallback to Cortex.")

    # =================================================
    # Layer 2: The Cortex (大脑 / 深度思考)
    # =================================================
    logger.info(f"🧠 Cortex Layer Active: {CORTEX_MODEL} (Deep Reasoning...)")
    
    system_prompt = get_system_prompt()
    context = fetch_calendar_context()
    memory_block = load_history(user_id)
    user_profile = load_user_profile()
    
    full_prompt = f"""
    {system_prompt}
    [User Profile] {user_profile}
    [Context] {context}
    [History] {memory_block}
    [Command] {user_text} (Reply in Chinese)
    """

    tool_list = [
        create_event_tool_wrapper, search_calendar_tool_wrapper,
        update_event_tool_wrapper, delete_event_tool_wrapper,
        add_task_tool_wrapper, list_tasks_tool_wrapper
    ]

    try:
        # 调用 Gemini 2.5
        response = client.models.generate_content(
            model=CORTEX_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(tools=tool_list, temperature=0.3)
        )
        
        reply_text = ""
        
        # 处理工具调用
        if response.function_calls:
            tool_results = []
            for call in response.function_calls:
                name = call.name
                args = call.args
                # 路由
                if name == "create_event_tool_wrapper": 
                    res = create_event_tool_wrapper(
                        summary=str(args.get('summary')),
                        start_time=args.get('start_time'),
                        duration_hours=float(args.get('duration_hours', 1.0)),
                        reason=str(args.get('reason', ''))
                    )
                elif name == "search_calendar_tool_wrapper": res = search_calendar_tool_wrapper(args.get('query'))
                elif name == "update_event_tool_wrapper": res = update_event_tool_wrapper(args.get('event_id'), args.get('new_start_time'), args.get('new_summary'))
                elif name == "delete_event_tool_wrapper": res = delete_event_tool_wrapper(args.get('event_id'))
                elif name == "add_task_tool_wrapper": res = add_task_tool_wrapper(args.get('title'), args.get('notes'))
                elif name == "list_tasks_tool_wrapper": res = list_tasks_tool_wrapper()
                else: res = f"❌ Unknown Tool"
                tool_results.append(res)
            
            reply_text = f"✅ 执行报告:\n" + "\n".join(tool_results)
        else:
            reply_text = response.text if response.text else "⚠️ (No output from Cortex)"

        # 记录大脑的回复
        save_history(user_id, "User", user_text)
        save_history(user_id, "Jarvis", reply_text)
        return reply_text

    except Exception as e:
        logger.error(f"Brain Failure ({CORTEX_MODEL}): {e}")
        return f"⚠️ System Malfunction: {str(e)}"