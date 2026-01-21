# core/agent.py
import json
import datetime
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.prompts import get_system_prompt
from core.router import NeuralRouter
from core.memory import load_history, save_history
from core.container import Container  # 🔥 [Core] 接入心脏

# 🔥 [Logic] 数据层与表现层分离
from services.google_ops import (
    create_event_data, search_events_data, update_event_data, delete_event_data,
    add_task_data, list_tasks_data, fetch_raw_events
)
from utils.formatter import format_calendar_events, format_tasks

logger = setup_logger("AgentCore")

# --- 🛠️ 工具定义 (Logic Layer: Data -> String) ---

def create_event_tool_wrapper(summary: str, start_time: str = None, duration_hours: float = 1.0, reason: str = ""):
    """创建日程"""
    if not start_time: 
        start_time = datetime.datetime.now().isoformat()
    
    # 1. Action (Data Layer)
    res = create_event_data(summary, start_time, duration_hours, description=reason)
    
    # 2. Presentation (Formatter) - 简单反馈
    if res:
        start_display = res['start'].get('dateTime', '')[:16].replace('T', ' ')
        return f"✅ Created: {res.get('summary')} @ {start_display}"
    return "❌ Failed to create event (Google API Error)."

def search_calendar_tool_wrapper(query: str):
    """搜索日程"""
    events = search_events_data(query) # List[Dict]
    return format_calendar_events(events) # String via Formatter

def update_event_tool_wrapper(event_id: str, new_start_time: str = None, new_summary: str = None):
    """更新日程"""
    patch = {}
    if new_summary: patch['summary'] = new_summary
    if new_start_time:
        if 'T' not in new_start_time: new_start_time = new_start_time.replace(' ', 'T')
        patch['start'] = {'dateTime': new_start_time, 'timeZone': 'Europe/London'}
    
    res = update_event_data(event_id, patch)
    if res: return f"✅ Updated: {res.get('summary')}"
    return "❌ Update failed."

def delete_event_tool_wrapper(event_id: str):
    """删除日程"""
    if delete_event_data(event_id):
        return "✅ Event deleted."
    return "❌ Delete failed."

def add_task_tool_wrapper(title: str, notes: str = None):
    """添加待办"""
    res = add_task_data(title, notes)
    if res: return f"✅ Task Added: {res.get('title')}"
    return "❌ Task add failed."

def list_tasks_tool_wrapper():
    """列出待办"""
    tasks = list_tasks_data()
    return format_tasks(tasks) # String via Formatter

# --- 🧠 核心运行逻辑 ---

def get_context_string():
    """组合生成实时 Context"""
    events = fetch_raw_events(hours=24)
    tasks = list_tasks_data(max_results=5)
    
    schedule_str = format_calendar_events(events)
    tasks_str = format_tasks(tasks)
    
    return f"Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n[Schedule]\n{schedule_str}\n\n[Top Tasks]\n{tasks_str}"

def run(user_text, user_id="DEFAULT_USER"):
    # =================================================
    # Layer 1: The Neural Router (小脑)
    # =================================================
    try:
        logger.info(f"🏎️  Router Active")
        router = NeuralRouter()
        fast_response = router.route_and_execute(user_text)
        if fast_response:
            logger.info("🟢 Router Hit.")
            save_history(user_id, "User", user_text)
            save_history(user_id, "Jarvis", fast_response)
            return fast_response
    except Exception as e:
        logger.warning(f"⚠️ Router Skipped: {e}")

    # =================================================
    # Layer 2: The Cortex (大脑)
    # =================================================
    
    system_prompt = get_system_prompt()
    context = get_context_string() 
    memory_block = load_history(user_id)
    
    # 🔥 [DRY Fix] 统一从 Container 读取 Profile
    user_profile = Container.load_user_profile()
    
    full_prompt = f"""
    {system_prompt}
    [User Profile] {user_profile}
    [Real-time Context] {context}
    [History] {memory_block}
    [Command] {user_text} (Reply in Chinese)
    """

    tool_list = [
        create_event_tool_wrapper, search_calendar_tool_wrapper,
        update_event_tool_wrapper, delete_event_tool_wrapper,
        add_task_tool_wrapper, list_tasks_tool_wrapper
    ]

    try:
        # 🔥🔥🔥 [Core Feature] 使用 Container 的自动轮换接口
        # 自动处理 429/503 报错，自动切换模型，且自动加上了 BLOCK_NONE 安全盾
        response = Container.call_brain(
            contents=full_prompt,
            tools=tool_list,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        
        reply_text = ""
        
        if response.function_calls:
            tool_results = []
            for call in response.function_calls:
                name = call.name
                args = call.args
                # 路由分发
                if name == "create_event_tool_wrapper": 
                    res = create_event_tool_wrapper(args.get('summary'), args.get('start_time'), float(args.get('duration_hours', 1)), args.get('reason', ''))
                elif name == "search_calendar_tool_wrapper": res = search_calendar_tool_wrapper(args.get('query'))
                elif name == "update_event_tool_wrapper": res = update_event_tool_wrapper(args.get('event_id'), args.get('new_start_time'), args.get('new_summary'))
                elif name == "delete_event_tool_wrapper": res = delete_event_tool_wrapper(args.get('event_id'))
                elif name == "add_task_tool_wrapper": res = add_task_tool_wrapper(args.get('title'), args.get('notes'))
                elif name == "list_tasks_tool_wrapper": res = list_tasks_tool_wrapper()
                else: res = f"❌ Unknown Tool"
                tool_results.append(res)
            
            reply_text = f"✅ Execution Report:\n" + "\n".join(tool_results)
        else:
            # 🔥 [Debug] 诊断空回复
            if response.text:
                reply_text = response.text
            else:
                finish_reason = "UNKNOWN"
                if response.candidates and response.candidates[0].finish_reason:
                    finish_reason = response.candidates[0].finish_reason
                
                logger.warning(f"⚠️ Empty Response. Finish Reason: {finish_reason}")
                reply_text = f"⚠️ (No output from Cortex). Finish Reason: {finish_reason}"

        save_history(user_id, "User", user_text)
        save_history(user_id, "Jarvis", reply_text)
        return reply_text

    except Exception as e:
        logger.error(f"Brain Failure: {e}")
        return f"⚠️ System Malfunction: {str(e)}"