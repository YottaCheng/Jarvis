import time
import datetime
import logging
from config import settings
from services.google_ops import fetch_raw_events, add_task_tool, list_tasks_tool
from utils.logger import setup_logger

logger = setup_logger("SpinalCord")

# --- 1. 纯自动化同步 (Calendar -> Tasks) ---
def daily_sync_logic():
    """
    脊椎反射：每天早上把 Calendar 里的硬骨头同步到 Tasks
    无需 Gemini 介入。
    """
    logger.info("🔄 Spinal Cord: Starting Daily Sync...")
    
    # 1. 获取今日日程 (看未来 18 小时)
    events = fetch_raw_events(hours=18) 
    if not events:
        logger.info("   No events found today.")
        return

    # 2. 获取当前待办 (防止重复添加)
    # 🔥 [增强] 获取前 50 条任务，确保查重准确
    current_tasks_str = list_tasks_tool(max_results=50) 
    
    sync_count = 0
    for event in events:
        title = event.get('summary', 'Untitled')
        
        # 过滤器：忽略琐事
        if any(x in title.lower() for x in ['commute', 'lunch', 'rest']):
            continue
            
        # 查重：严格比对
        if title in current_tasks_str:
            # 🔥 [Debug] 显式打印跳过信息，让你放心
            logger.info(f"   ♻️  Skipping duplicate: {title}")
            continue
            
        # 如果不存在，则添加
        end_time = event['end'].get('dateTime', '')
        clean_time = end_time[:16].replace('T', ' ') if end_time else "End of Day"
        
        add_task_tool(title, notes=f"[Auto-Sync] Due: {clean_time}")
        sync_count += 1
        logger.info(f"   ➕ Synced: {title}")
    
    if sync_count > 0:
        logger.info(f"✅ Sync Complete. Added {sync_count} tasks.")
    else:
        logger.info("✅ Sync Complete. No new tasks needed.")

# --- 2. 自适应扫描 (Adaptive Scanning) ---
def calculate_next_heartbeat(mode="NORMAL"):
    now = datetime.datetime.now()
    
    if mode == "EMERGENCY":
        logger.info("🔥 Mode: EMERGENCY. Next scan in 1 hour.")
        return now + datetime.timedelta(hours=1)
    
    if mode == "NORMAL":
        if now.hour < 20:
            target = now.replace(hour=20, minute=0, second=0)
            logger.info(f"🍃 Mode: NORMAL. Sleeping until evening check ({target.strftime('%H:%M')}).")
            return target
        else:
            target = (now + datetime.timedelta(days=1)).replace(hour=7, minute=0, second=0)
            logger.info(f"🌙 Day ending. Sleeping until tomorrow morning ({target.strftime('%H:%M')}).")
            return target
            
    return now + datetime.timedelta(hours=1)

def spinal_loop():
    """
    脊椎主循环 (独立线程)
    """
    # 🔥 启动时强制同步一次，方便调试
    logger.info("🔧 Debug Mode: Force running Daily Sync on startup...")
    daily_sync_logic()
    
    while True:
        try:
            current_mode = "NORMAL" 
            next_wake = calculate_next_heartbeat(current_mode)
            sleep_seconds = (next_wake - datetime.datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
                
            if datetime.datetime.now().hour == 7:
                daily_sync_logic()
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Spinal Cord Crash: {e}")
            time.sleep(60)