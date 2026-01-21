# services/spinal_cord.py
import time
import schedule
import datetime
from google.genai import types
from slack_bolt import App

# 基础设施
from config import settings
from utils.logger import setup_logger
from core.container import Container  # 🔥 接入心脏 (统一 Client)
from core.prompts import BUTLER_WAKEUP_PROMPT, SUPERVISOR_PROMPT  # 🔥 接入灵魂 (统一 Prompt)

# 纯数据操作 (V3.0 新接口)
from services.google_ops import fetch_raw_events, list_tasks_data, add_task_data

logger = setup_logger("SpinalCord")

# Slack Client (保持独立)
slack_client = App(token=settings.SLACK_BOT_TOKEN).client

# --- 全局内存状态 ---
TODAY_WAKE_TIME = None
# 🔥 [Relay Memory] 记录今天已经“监督过”的任务 ID，防止每 10 分钟重复骂一遍
SUPERVISED_EVENTS = set() 

# ==============================================================================
# 模块 A: 管家唤醒 (Butler Wake-up)
# ==============================================================================

def generate_butler_greeting(reason: str) -> str:
    """
    调用大脑生成一句英式管家的唤醒语
    """
    try:
        # 1. 获取用户画像
        profile = Container.load_user_profile()
        
        # 2. 填充 Prompt (从 core/prompts.py 获取)
        full_prompt = BUTLER_WAKEUP_PROMPT.format(
            reason=reason,
            profile=profile
        )
        
        # 3. 调用大脑 (自动抗 RPD 轮换)
        # 这里配置 max_tokens=60，因为只需要一句话
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
    执行唤醒动作
    """
    global TODAY_WAKE_TIME, SUPERVISED_EVENTS
    logger.info("⏰ Executing Wake-up Protocol...")
    
    # 1. 发送消息
    text = generate_butler_greeting(reason)
    try:
        slack_client.chat_postMessage(channel=settings.OWNER_ID, text=text)
        logger.info(f"✅ Wake-up dispatched: {text}")
    except Exception as e:
        logger.error(f"❌ Slack Error: {e}")
    
    # 2. 每日状态重置
    TODAY_WAKE_TIME = None
    SUPERVISED_EVENTS.clear() # 🔥 新的一天，清空监督历史
    logger.info("🧹 Memory Flushed: Supervised event history cleared for new day.")
    
    return schedule.CancelJob 

def plan_morning_routine():
    """
    [02:00 AM] 扫描未来 24 小时，设定唤醒闹钟
    """
    global TODAY_WAKE_TIME
    logger.info("🌙 02:00 AM Protocol: Analyzing Schedule...")
    
    events = fetch_raw_events(hours=24)
    first_event_time = None
    first_event_title = ""

    now = datetime.datetime.now()
    
    for event in events:
        start_str = event['start'].get('dateTime')
        if not start_str: continue 
        
        try:
            evt_time = datetime.datetime.fromisoformat(start_str)
            # 必须是今天，且在当前时间之后
            if evt_time.date() == now.date() and evt_time > now:
                title = event.get('summary', 'Unknown')
                # 排除非任务类日程
                if any(x in title.lower() for x in ['commute', 'lunch', 'break', 'sleep']):
                    continue
                first_event_time = evt_time
                first_event_title = title
                break 
        except:
            continue

    # 设定闹钟
    if first_event_time:
        # 策略：提前 60 分钟
        wake_dt = first_event_time - datetime.timedelta(minutes=60)
        wake_str = wake_dt.strftime("%H:%M")
        
        logger.info(f"📅 First Task: '{first_event_title}' @ {first_event_time.strftime('%H:%M')}")
        logger.info(f"⏰ Set Wake-up: {wake_str}")
        
        schedule.every().day.at(wake_str).do(
            execute_wake_up, 
            reason=f"首个日程 '{first_event_title}' 将在 {first_event_time.strftime('%H:%M')} 开始"
        )
        TODAY_WAKE_TIME = wake_str
    else:
        # 周末/无日程策略
        if now.weekday() >= 5: 
            logger.info("🛌 Weekend: No alarm set.")
        else:
            logger.info("📅 Weekday Backup: Set Wake-up 09:30.")
            schedule.every().day.at("09:30").do(
                execute_wake_up, 
                reason="虽然无明确日程，但今天是工作日"
            )

# ==============================================================================
# 模块 B: 每日同步 (Daily Sync)
# ==============================================================================

def daily_sync_logic():
    """
    [07:00 AM] 将日历同步到 Task 列表
    """
    logger.info("🔄 Spinal Cord: Starting Daily Sync...")
    
    events = fetch_raw_events(hours=18) 
    if not events: return

    # 1. 获取当前待办 (用于查重)
    current_tasks = list_tasks_data(max_results=50) 
    existing_titles = [t['title'] for t in current_tasks]
    
    count = 0
    for event in events:
        title = event.get('summary', 'Untitled')
        
        # 2. 过滤
        if any(x in title.lower() for x in ['commute', 'lunch', 'rest', 'sleep']):
            continue
            
        # 3. 查重
        if title in existing_titles:
            continue
            
        end_time = event['end'].get('dateTime', '')
        clean_time = end_time[:16].replace('T', ' ') if end_time else None
        
        # 4. 添加到 Google Tasks
        add_task_data(title, notes=f"[Auto-Sync] Due: {clean_time}")
        logger.info(f"   ➕ Synced: {title}")
        count += 1
        
    logger.info(f"✅ Sync Complete. Added {count} tasks.")

# ==============================================================================
# 模块 C: 接力监督 (The Relay Supervisor)
# ==============================================================================

def check_supervision_queue():
    """
    [每10分钟] 任务接力检查逻辑
    逻辑：扫描刚结束 1 小时的任务 -> 检查 Task 是否打钩 -> 未打钩则报警
    """
    logger.info("🕵️ Supervisor: Scanning for unfinished business...")
    
    # 1. 获取过去 24 小时的日程 (寻找刚结束的)
    # 注意：这里我们取稍微宽一点的范围，主要是为了拿到今天的日程
    events = fetch_raw_events(hours=24) 
    now = datetime.datetime.now()
    
    # 2. 获取当前所有“未完成”的 Tasks (作为黑名单)
    # list_tasks_data 默认只返回 pending 的任务
    pending_tasks = list_tasks_data(max_results=100)
    pending_titles = [t['title'] for t in pending_tasks]
    
    for event in events:
        e_id = event['id']
        title = event.get('summary', 'Untitled')
        
        # 2.1 内存查重：今天已经催过的，别再催了
        if e_id in SUPERVISED_EVENTS: continue
        
        # 2.2 过滤杂事
        if any(x in title.lower() for x in ['commute', 'lunch', 'break', 'sleep']): continue
        
        # 2.3 检查时间窗口
        end_str = event['end'].get('dateTime')
        if not end_str: continue 
        
        try:
            end_dt = datetime.datetime.fromisoformat(end_str)
            # 处理时区 (将带时区的时间转为本地 naive 时间进行比较，假设机器在同一时区)
            end_dt_naive = end_dt.replace(tzinfo=None) if end_dt.tzinfo else end_dt
            
            # 🔥 核心逻辑：Relay Buffer (1小时)
            # 只有在 (结束时间 + 60分钟) 到 (结束时间 + 120分钟) 之间才触发
            buffer_start = end_dt_naive + datetime.timedelta(minutes=60)
            buffer_end = end_dt_naive + datetime.timedelta(minutes=120)
            
            if buffer_start <= now <= buffer_end:
                # 2.4 状态核查：是否还在 Pending 列表里？
                if title in pending_titles:
                    logger.warning(f"🚨 Supervision Triggered: '{title}' finished >1h ago but STILL PENDING.")
                    
                    # 2.5 生成毒舌催促 (使用 SUPERVISOR_PROMPT)
                    prompt = SUPERVISOR_PROMPT.format(task_title=title)
                    response = Container.call_brain(
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.9, max_output_tokens=50)
                    )
                    msg = response.text.strip()
                    
                    # 2.6 发送警告
                    slack_client.chat_postMessage(channel=settings.OWNER_ID, text=msg)
                    
                    # 2.7 写入内存，标记已处理
                    SUPERVISED_EVENTS.add(e_id)
                    
        except Exception as e:
            logger.error(f"Supervision Check Failed for {title}: {e}")
            continue

# ==============================================================================
# 模块 D: 脊椎主循环 (Main Loop)
# ==============================================================================

def spinal_loop():
    logger.info("🦴 Spinal Cord Attached. Butler Mode Online.")
    
    # 1. 晨间规划 (02:00)
    schedule.every().day.at("02:00").do(plan_morning_routine)
    
    # 2. 每日同步 (07:00)
    schedule.every().day.at("07:00").do(daily_sync_logic)
    
    # 3. 🔥 接力监督 (每 10 分钟轮询一次)
    # 这比“预约队列”更稳健，因为它不怕重启，只要在时间窗口内就能抓到
    schedule.every(10).minutes.do(check_supervision_queue)
    
    # [Debug] 仅开发时使用：启动时立刻跑一次监督逻辑
    # check_supervision_queue()

    while True:
        schedule.run_pending()
        time.sleep(60)