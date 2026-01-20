import os
import sys
import logging
import datetime
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from google import genai
from google.genai import types
from apscheduler.schedulers.background import BackgroundScheduler

# 引入工具库
from google_ops import get_google_service, create_schedule_event

# --- 1. 初始化配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 你的 ID (已锁定)
MY_USER_ID = "U0A9B5ETMFF"

if not (BOT_TOKEN and APP_TOKEN and GEMINI_KEY):
    sys.exit("❌ 密钥缺失！请检查 .env")

app = App(token=BOT_TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

MODEL_ID = "gemini-3-flash-preview"

# --- 2. 工具定义 ---
def create_event_tool(summary: str, start_time: str, duration_hours: float, reason: str):
    """[工具] 在日历上安排任务。"""
    logger.info(f"🤖 执行工具: {summary}")
    return create_schedule_event(summary, start_time, duration_hours, description=reason)

# --- 3. 大脑逻辑 (修复了视力和视觉污染) ---

def fetch_context():
    """
    [升级版眼睛]：扫描所有日历 (包括 UCL 课表)
    """
    calendar_service, _ = get_google_service()
    if not calendar_service: return "❌ 日历连接失败"
    
    now = datetime.datetime.now().isoformat() + 'Z' # UTC时间
    summary = f"Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    summary += "Existing Schedule (Scanning all calendars):\n"
    
    # 1. 获取所有日历列表 (解决看不到 UCL 课表的问题)
    try:
        calendars = calendar_service.calendarList().list().execute().get('items', [])
        
        for cal in calendars:
            # 跳过不需要的日历 (比如节日、生日)
            if "holiday" in cal.get('id') or "addressbook" in cal.get('id'): 
                continue
            
            cal_name = cal.get('summary', 'Unknown')
            
            # 2. 遍历每个日历的事件
            events = calendar_service.events().list(
                calendarId=cal['id'], 
                timeMin=now, 
                maxResults=8, # 每个日历取近期 8 个，避免 Token 爆炸
                singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
            
            if events:
                summary += f"\n[Calendar: {cal_name}]\n"
                for e in events:
                    start = e['start'].get('dateTime', e['start'].get('date'))
                    # 格式化一下时间，去掉秒，让 AI 读得更舒服
                    clean_start = start.replace('T', ' ')[:16] 
                    event_title = e.get('summary', 'No Title')
                    summary += f"- {clean_start} | {event_title}\n"
                    
    except Exception as e:
        logger.error(f"日历扫描出错: {e}")
        return f"Error scanning calendars: {e}"

    return summary

def agent_run(user_text, system_override=None):
    """
    核心思考链路：Zero-Clutter Protocol
    """
    base_prompt = """
    [Role]
    You are Jarvis. A pragmatic, high-intellect AI executive assistant.
    Master: KCL (CS) + UCL (Crime Science). Ambitious, ADHD.
    
    [Protocol - The "Zero-Clutter" Rule]
    1. **NO Visual Clutter**: Do NOT use markdown bolding (the ** symbols). Output CLEAN text only.
    2. **NO Preaching**: Never recite priority definitions. Just execute.
    3. **Tone**: ENTP style. Sharp, concise, professional.
    
    [Logic: Priority Stack]
    - CRITICAL: Job/PSW Visa. (Always prioritize)
    - HIGH: UCL Academia/Dissertation.
    - MAINTENANCE: Gym/Botox/Energy.
    
    [Output]
    - Direct Action Report.
    - Language: STRICTLY CHINESE (English ONLY for specific CS/Academic terms).
    """
    
    system_prompt = system_override if system_override else base_prompt
    context = fetch_context() # 这里会调用升级版的 context
    
    # 强制中文补丁 + 禁止加粗补丁
    final_user_text = f"{user_text} (Reply in Chinese. DO NOT use bolding **)"

    full_prompt = f"""
    {system_prompt}
    
    [Context Data]
    {context}

    [User Command]
    "{final_user_text}"
    """

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                tools=[create_event_tool],
                temperature=0.3
            )
        )

        if response.function_calls:
            tool_results = []
            for call in response.function_calls:
                if call.name == "create_event_tool":
                    args = call.args
                    result_msg = create_event_tool(
                        args['summary'], args['start_time'], args['duration_hours'], args['reason']
                    )
                    tool_results.append(result_msg)
            return f"✅ 执行报告:\n" + "\n".join(tool_results)
        
        else:
            # 双重保险：手动把可能的 ** 替换掉，防止 AI 不听话
            clean_text = response.text.replace("**", "")
            return clean_text

    except Exception as e:
        return f"⚠️ 系统故障: {str(e)}"

# --- 4. 主动推送模块 ---

def daily_briefing():
    """早报推送"""
    logger.info(f"⏰ 推送早报 -> {MY_USER_ID}")
    briefing = agent_run("简要浏览今日安排，指出 Tier 0 关键缺口。极简。")
    try:
        app.client.chat_postMessage(channel=MY_USER_ID, text=f"🌅 Morning Brief:\n{briefing}")
    except Exception as e:
        logger.error(f"❌ 推送失败: {e}")

# 初始化调度器 (每天 08:00)
scheduler = BackgroundScheduler()
scheduler.add_job(daily_briefing, 'cron', hour=8, minute=0)
scheduler.start()

# --- 5. 交互路由 ---

@app.message("")
def handle_all(message, say):
    if message.get('bot_id'): return
    say("Thinking...") 
    reply = agent_run(message['text'])
    say(reply)

if __name__ == "__main__":
    logger.info(f"⚡️ Jarvis v3.0 Online | Model: {MODEL_ID}")
    try:
        SocketModeHandler(app, APP_TOKEN).start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()