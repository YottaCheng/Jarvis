# services/spinal_cord.py
import time
import schedule
import datetime
import logging
from google.genai import types
from slack_bolt import App

# 基础设施
from config import settings
from utils.logger import setup_logger
from core.container import Container
from core.prompts import BUTLER_WAKEUP_PROMPT, SUPERVISOR_PROMPT

# 纯数据操作 (V3.0 新接口)
from services.google_ops import fetch_raw_events, list_tasks_data, add_task_data

logger = setup_logger("SpinalCord")

# Slack Client
slack_client = App(token=settings.SLACK_BOT_TOKEN).client

# --- 全局内存状态 ---
TODAY_WAKE_TIME = None
SUPERVISED_EVENTS = set() 

# ==============================================================================
# [Module A] 唤醒执行模块 (The Mouth)
# 负责：早上闹钟响了之后，真正“说话”发消息的部分
# ==============================================================================

def generate_butler_greeting(reason: str) -> str:
    """调用大脑生成一句英式管家的唤醒语"""
    try:
        profile = Container.load_user_profile()
        full_prompt = BUTLER_WAKEUP_PROMPT.format(reason=reason, profile=profile)
        response = Container.call_brain(
            contents=full_prompt,
            config=types.GenerateContentConfig(temperature=0.8, max_output_tokens=60)
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Greeting Gen Failed: {e}")
        return f"Don Yotta，系统报错了，但您必须起床。原因：{reason}。"

def execute_wake_up(reason=""):
    """
    [执行动作] 发送早安简报：问候 + 真实 UCL 课表 + 核心待办
    注意：这个函数是被 schedule 调用的
    """
    global TODAY_WAKE_TIME, SUPERVISED_EVENTS
    logger.info("⏰ Executing Wake-up Protocol...")
    
    # 1. 获取真实数据
    events = fetch_raw_events(hours=18)
    tasks = list_tasks_data(max_results=5)
    
    # 2. 生成问候语
    greeting = generate_butler_greeting(reason)
    if not greeting or len(greeting) < 2: 
        greeting = "早安，Don Yotta。数据已加载。"
    
    # 3. 构建消息
    msg_blocks = [f"🌞 *{greeting}*"]
    
    if events:
        msg_blocks.append("\n📅 *今日作战地图 (UCL + Personal):*")
        for e in events:
            start_str = e['start'].get('dateTime', '')
            time_str = start_str[11:16] if 'T' in start_str else "全天"
            summary = e.get('summary', 'Unknown')
            source = e.get('source_calendar', 'Personal')
            icon = "🎓" if source == 'UCL' else "🔹"
            msg_blocks.append(f"{icon} `{time_str}` {summary}")
    else:
        msg_blocks.append("\n📅 *今日无特定日程 (旷野模式)*")

    if tasks:
        msg_blocks.append("\n📝 *核心任务 (Top 3):*")
        active_tasks = [t for t in tasks if t['status'] != 'completed']
        for t in active_tasks[:3]:
            msg_blocks.append(f"⭕️ {t['title']}")
    
    final_text = "\n".join(msg_blocks)

    # 4. 发送
    try:
        slack_client.chat_postMessage(channel=settings.OWNER_ID, text=final_text)
        logger.info("✅ Wake-up dispatched with Full Schedule.")
    except Exception as e:
        logger.error(f"❌ Slack Error: {e}")
    
    # 5. 重置每日状态
    TODAY_WAKE_TIME = None
    SUPERVISED_EVENTS.clear()
    logger.info("🧹 Memory Flushed: Supervised event history cleared for new day.")
    
    return schedule.CancelJob

# ==============================================================================
# [Module B] 智能规划模块 (The Brain)
# 负责：每天凌晨 2 点醒来，决定“今天几点起”
# ==============================================================================

def plan_morning_routine():
    """
    [智能逻辑] 02:00 AM 运行：
    1. 周末 -> 不设闹钟
    2. 工作日 -> 寻找最早日程，提前 1 小时叫醒
    """
    global TODAY_WAKE_TIME
    
    # 1. 清除旧闹钟
    schedule.clear('daily_wakeup')
    logger.info("🧹 Cleared previous wake-up schedules.")

    # 2. 周末判定 (5=Sat, 6=Sun)
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        logger.info("🛌 Weekend detected. Sleeping in mode activated (No Alarm).")
        return

    # 3. 获取日程并计算时间
    events = fetch_raw_events(hours=20)
    
    # 默认保底：如果没有课，就 8:30 起
    wake_time = "08:30"
    reason_str = "常规唤醒"

    if events:
        first_event = events[0]
        start_iso = first_event['start'].get('dateTime', '')
        
        if 'T' in start_iso:
            event_time_str = start_iso.split('T')[1][:5] # 09:00
            event_hour = int(event_time_str.split(':')[0])
            event_min = int(event_time_str.split(':')[1])
            
            # --- 核心算法：提前 1 小时 ---
            wake_hour = event_hour - 1
            wake_time = f"{wake_hour:02d}:{event_min:02d}"
            reason_str = f"为了备战 {first_event.get('summary', 'Task')}"
            
            logger.info(f"📅 First event at {event_time_str}, setting alarm for {wake_time}")

    # 4. 设定今天的闹钟 (Tag 标记用于清除)
    # 注意：这里只负责“定闹钟”，不负责“叫”。叫由 execute_wake_up 负责。
    schedule.every().day.at(wake_time).do(execute_wake_up, reason=reason_str).tag('daily_wakeup')
    
    TODAY_WAKE_TIME = wake_time
    logger.info(f"⏰ Smart Alarm set for {wake_time} ({reason_str})")

# ==============================================================================
# [Module C] 每日同步模块
# 负责：早上 7 点把 UCL 课表写进 Google Tasks
# ==============================================================================

def daily_sync_logic():
    logger.info("🔄 Spinal Cord: Starting Daily Sync...")
    events = fetch_raw_events(hours=18) 
    if not events: return

    current_tasks = list_tasks_data(max_results=50) 
    existing_titles = [t['title'] for t in current_tasks]
    
    count = 0
    for event in events:
        title = event.get('summary', 'Untitled')
        if any(x in title.lower() for x in ['commute', 'lunch', 'rest', 'sleep']): continue
        if title in existing_titles: continue
            
        end_time = event['end'].get('dateTime', '')
        clean_time = end_time[:16].replace('T', ' ') if end_time else None
        
        add_task_data(title, notes=f"[Auto-Sync] Due: {clean_time}")
        count += 1
        
    logger.info(f"✅ Sync Complete. Added {count} tasks.")

# ==============================================================================
# [Module D] 棘轮监督模块 (The Ratchet)
# 负责：每 10 分钟检查一次，有没有超时未完成的任务
# ==============================================================================

def check_supervision_queue():
    logger.info("🕵️ Supervisor: Scanning for unfinished business...")
    
    # 找过去 24h 的日程 和 当前未完成的任务
    events = fetch_raw_events(hours=24) 
    pending_tasks = list_tasks_data(max_results=100)
    pending_titles = [t['title'] for t in pending_tasks]
    
    now = datetime.datetime.now()
    
    for event in events:
        e_id = event['id']
        title = event.get('summary', 'Untitled')
        
        if e_id in SUPERVISED_EVENTS: continue # 骂过就不骂了
        if any(x in title.lower() for x in ['commute', 'lunch', 'break', 'sleep']): continue
        
        end_str = event['end'].get('dateTime')
        if not end_str: continue 
        
        try:
            end_dt = datetime.datetime.fromisoformat(end_str)
            end_dt_naive = end_dt.replace(tzinfo=None) if end_dt.tzinfo else end_dt
            
            # --- 棘轮触发区：任务结束 1 小时后 ---
            buffer_start = end_dt_naive + datetime.timedelta(minutes=60)
            buffer_end = end_dt_naive + datetime.timedelta(minutes=120)
            
            if buffer_start <= now <= buffer_end:
                if title in pending_titles:
                    # 触发毒舌警告
                    logger.warning(f"🚨 Ratchet Triggered: {title}")
                    prompt = SUPERVISOR_PROMPT.format(task_title=title)
                    response = Container.call_brain(
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.9, max_output_tokens=50)
                    )
                    slack_client.chat_postMessage(channel=settings.OWNER_ID, text=response.text.strip())
                    SUPERVISED_EVENTS.add(e_id)
                    
        except Exception:
            continue

# ==============================================================================
# [Main Loop] 脊椎主循环 (程序入口)
# 负责：Main.py 调用的就是这个函数
# ==============================================================================

def spinal_loop():
    logger.info("🦴 Spinal Cord Attached. Butler Mode Online.")
    
    # 1. 晨间规划 (每天 02:00 定闹钟)
    schedule.every().day.at("02:00").do(plan_morning_routine)
    
    # 2. 每日同步 (每天 07:00 同步任务)
    schedule.every().day.at("07:00").do(daily_sync_logic)
    
    # 3. 棘轮监督 (每 10 分钟巡逻一次)
    schedule.every(10).minutes.do(check_supervision_queue)
    
    # --- [Debug] 第一次启动时，强制跑一次唤醒，让你看看效果 ---
    # 确认 Slack 收到消息后，下次记得把这行注释掉
    logger.info("🚀 Debug Mode: Triggering immediate wake-up test...")
    execute_wake_up(reason="系统重启测试") 

    while True:
        schedule.run_pending()
        time.sleep(60)