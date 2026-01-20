import json
from google import genai
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.prompts import get_system_prompt
from services.google_ops import (
    fetch_calendar_context, create_schedule_event, 
    search_calendar_events, update_schedule_event, delete_schedule_event,
    add_task_tool, list_tasks_tool
)
from core.memory import load_history, save_history

logger = setup_logger("AgentCore")
client = genai.Client(api_key=settings.GEMINI_KEY)

# 直接使用 settings 里的模型 (由 Launcher 决定)
CURRENT_MODEL = settings.MODEL_ID

# --- 🔥 [修复核心] 严格类型定义 (Strict Type Hinting) ---
# Google SDK 需要明确知道参数是 str 还是 float，否则会报错

def create_event_tool_wrapper(summary: str, start_time: str = None, duration_hours: float = 1.0, reason: str = ""):
    """
    创建日程
    Args:
        summary: 日程标题
        start_time: 开始时间 (ISO格式, e.g. 2026-01-20T10:00)
        duration_hours: 持续时间 (小时)
        reason: 创建理由
    """
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

def run(user_text, user_id="DEFAULT_USER"):
    logger.info(f"🧠 Active Model: {CURRENT_MODEL}")
    
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

    # 将包装好的工具放入列表
    tool_list = [
        create_event_tool_wrapper, search_calendar_tool_wrapper,
        update_event_tool_wrapper, delete_event_tool_wrapper,
        add_task_tool_wrapper, list_tasks_tool_wrapper
    ]

    try:
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(tools=tool_list, temperature=0.3)
        )
        
        reply_text = ""
        if response.function_calls:
            tool_results = []
            for call in response.function_calls:
                name = call.name
                args = call.args
                # 路由
                if name == "create_event_tool_wrapper": 
                    # 显式转换类型以防万一
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
            reply_text = response.text if response.text else "⚠️ (No output)"

        save_history(user_id, "User", user_text)
        save_history(user_id, "Jarvis", reply_text)
        return reply_text

    except Exception as e:
        logger.error(f"Brain Failure ({CURRENT_MODEL}): {e}")
        return f"⚠️ Model Error: {str(e)}"