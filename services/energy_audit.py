# services/energy_audit.py
import json
import datetime
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.container import Container
from core.state import StateManager
from core.memory import load_history
# 引入 Prompt
from core.prompts import ENERGY_AUDIT_TACTICAL, ENERGY_AUDIT_STRATEGIC
# 引入数据操作
from services.google_ops import list_tasks_data, fetch_raw_events
from slack_bolt import App

logger = setup_logger("EnergyAudit")
slack_client = App(token=settings.SLACK_BOT_TOKEN).client
state_manager = StateManager()

def is_user_busy():
    """
    [Availability Check] 检查当前时间是否有日历事项
    用于防止在用户开会/忙碌时触发审计打扰
    """
    try:
        # 获取当前正在进行的事件 (hours=3 代表检索范围)
        events = fetch_raw_events(hours=3)
        now = datetime.datetime.now().astimezone() # 带时区
        
        for event in events:
            start_str = event['start'].get('dateTime')
            end_str = event['end'].get('dateTime')
            if not start_str or not end_str: continue # 跳过全天事件
            
            start_dt = datetime.datetime.fromisoformat(start_str)
            end_dt = datetime.datetime.fromisoformat(end_str)
            
            # 如果当前时间处于某个事件的中间
            if start_dt <= now <= end_dt:
                logger.info(f"🔕 User is busy with: '{event.get('summary')}'")
                return True
        return False
    except Exception as e:
        logger.error(f"Busy Check Error: {e}")
        return False

def perform_energy_audit():
    """
    [Core] 智能精力审计系统
    - 战术模式 (Tactical): 早/午，使用 Gemini 3 Flash，只在空闲时触发。
    - 战略模式 (Strategic): 晚间，使用 Gemini 3 Pro，深度复盘。
    """
    # 1. 忙碌检查 (Smart Availability)
    # 如果用户正在忙，直接跳过本次审计
    if is_user_busy():
        logger.info("⏳ Audit Skipped: User is currently busy (Calendar Event).")
        return

    now_hour = datetime.datetime.now().hour
    
    # 2. 决定模式
    # 08:00 - 18:00 -> 战术模式
    if 8 <= now_hour < 18:
        mode = "TACTICAL"
        # 战术分析使用 Gemini 3 Flash (更敏锐)
        model_id = settings.AUDIT_MODELS.get("FLASH", "models/gemini-3-flash-preview")
        limit_history = 15 # 看最近 15 条
        prompt_template = ENERGY_AUDIT_TACTICAL
        logger.info(f"🔋 Energy Audit: TACTICAL Mode (Model: {model_id})")
    else:
        # 18:00 后 -> 战略模式
        mode = "STRATEGIC"
        # 战略分析使用 Gemini 3 Pro (核武器)
        model_id = settings.AUDIT_MODELS.get("PRO", "models/gemini-3-pro-preview")
        limit_history = 50 # 看全天
        prompt_template = ENERGY_AUDIT_STRATEGIC
        logger.info(f"🔋 Energy Audit: STRATEGIC Mode (Model: {model_id})")

    # 3. 收集数据上下文
    recent_chat = load_history(settings.OWNER_ID, limit=limit_history)
    tasks = list_tasks_data(max_results=50)
    task_count = len(tasks)
    # 提取任务标题摘要
    tasks_summary = str([t['title'] for t in tasks])

    # 4. 组装 Prompt
    full_prompt = prompt_template.format(
        chat_history=recent_chat,
        task_count=task_count,
        tasks_summary=tasks_summary,
        tiers_config=settings.TIERS
    )

    try:
        # 5. 调用审计模型 (指定特定模型，绕过自动轮换)
        client = Container.get_client()
        
        # 🔥 [CRITICAL FIX] 注入安全盾，防止因"内容敏感"返回 None
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")
        ]

        response = client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json", # 强制 JSON
                safety_settings=safety_settings        # 🔥 加上防弹衣
            )
        )
        
        # 6. 解析结果
        if not response.text:
            raise ValueError("Empty response from Audit Model (Safety Filter still active?)")
            
        result = json.loads(response.text)
        new_energy = result.get("current_energy", "UNKNOWN")
        reason = result.get("reason", "")
        advice = result.get("suggested_action", "")
        balance = result.get("balance_check", "")
        
        logger.info(f"🧐 Audit Result ({mode}): Energy={new_energy} | {reason}")

        # 7. 更新状态机
        state_manager.update_energy(new_energy)
        
        # 8. 交互逻辑 (Notification Policy)
        # 只有在以下情况才打扰用户：
        # A. 晚间战略复盘 (STRATEGIC) -> 必须汇报
        # B. 状态极低 (LOW) -> 必须给予关怀
        
        should_notify = False
        if mode == "STRATEGIC": should_notify = True
        elif new_energy == "LOW": should_notify = True
        
        if should_notify and advice:
            msg = f"🔋 **Energy Audit ({mode})**\n"
            msg += f"State: `{new_energy}`\n"
            msg += f"Analysis: {reason}\n"
            if balance: msg += f"⚠️ Balance: {balance}\n"
            msg += f"💡 Jarvis: \"{advice}\""
            
            slack_client.chat_postMessage(channel=settings.OWNER_ID, text=msg)

    except Exception as e:
        logger.error(f"Audit Failed: {e}")