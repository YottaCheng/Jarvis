import os.path
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import settings

logger = logging.getLogger("GoogleOps")

# 🔥 权限大一统：日历、邮件、Tasks
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/tasks' 
]

# --- 核心鉴权层 (Private) ---

def _get_credentials():
    """
    [Core] 统一获取凭证。
    无论是日历还是 Tasks，都用这个函数拿钥匙。
    """
    creds = None
    token_path = settings.TOKEN_FILE
    creds_path = settings.CREDENTIALS_FILE

    # 1. 尝试热启动
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # 2. 尝试冷启动或刷新
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Token 刷新失败: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(creds_path):
                logger.error("❌ 找不到 credentials.json")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            # 固定端口 0，避免端口冲突
            creds = flow.run_local_server(port=0)
            
        # 3. 保存新 Token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def get_service(api_name, api_version):
    """通用服务构建器"""
    creds = _get_credentials()
    if not creds: return None
    try:
        return build(api_name, api_version, credentials=creds)
    except Exception as e:
        logger.error(f"构建 {api_name} 服务失败: {e}")
        return None

# 为了兼容旧代码，保留这个入口，但底层复用新逻辑
def get_google_service():
    """(Legacy) 返回 Calendar 和 Gmail 服务"""
    return get_service('calendar', 'v3'), get_service('gmail', 'v1')

# --- 📅 Calendar 模块 (CRUD) ---

def fetch_calendar_context():
    """[Read] 读取所有日历事件"""
    service = get_service('calendar', 'v3')
    if not service: return "❌ Calendar Offline"
    
    now = datetime.datetime.now().isoformat() + 'Z'
    summary = f"Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\nSchedule:\n"
    
    try:
        # 获取日历列表
        calendars = service.calendarList().list().execute().get('items', [])
        for cal in calendars:
            # 过滤杂项
            if "holiday" in cal.get('id') or "addressbook" in cal.get('id'): continue
            
            events = service.events().list(
                calendarId=cal['id'], timeMin=now, maxResults=5, singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
            
            if events:
                cal_name = cal.get('summary', 'Unknown')
                for e in events:
                    start = e['start'].get('dateTime', e['start'].get('date'))
                    clean_start = start.replace('T', ' ')[:16]
                    summary += f"- [{cal_name}] {clean_start} | {e.get('summary')}\n"
    except Exception as e:
        return f"Calendar Error: {e}"
    return summary

def create_schedule_event(summary, start_time, duration_hours=1, description="Jarvis 自动规划"):
    """[Create] 创建日程"""
    service = get_service('calendar', 'v3')
    if not service: return "❌ Calendar Offline"

    try:
        # 智能解析时间，允许传 '2026-01-20T10:00' 或 '2026-01-20 10:00'
        if 'T' not in start_time: start_time = start_time.replace(' ', 'T')
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = start_dt + datetime.timedelta(hours=duration_hours)
    except:
        start_dt = datetime.datetime.now()
        end_dt = start_dt + datetime.timedelta(hours=1)

    event_body = {
        'summary': f"🤖 {summary}",
        'description': description,
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/London'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/London'},
    }

    try:
        service.events().insert(calendarId='primary', body=event_body).execute()
        return f"✅ 已创建: {summary} @ {start_dt.strftime('%H:%M')}"
    except Exception as e:
        return f"❌ 创建失败: {e}"

def search_calendar_events(query, max_results=5):
    """[Search] 搜索日程 (返回 ID 用于修改/删除)"""
    service = get_service('calendar', 'v3')
    if not service: return "❌ Calendar Offline"
    
    now = datetime.datetime.now().isoformat() + 'Z'
    try:
        events_result = service.events().list(
            calendarId='primary', q=query, timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        if not events: return f"🔍 未找到关键词 '{query}' 的日程。"
        
        report = f"🔍 Found {len(events)} events for '{query}':\n"
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date'))
            report += f"- ID: {e['id']} | Time: {start[:16]} | Title: {e['summary']}\n"
        return report
    except Exception as e:
        return f"❌ 搜索失败: {e}"

def update_schedule_event(event_id, new_start_time=None, new_summary=None):
    """[Update] 修改日程"""
    service = get_service('calendar', 'v3')
    if not service: return "❌ Calendar Offline"
    
    patch_body = {}
    if new_summary: patch_body['summary'] = new_summary
    
    if new_start_time:
        try:
            if 'T' not in new_start_time: new_start_time = new_start_time.replace(' ', 'T')
            start_dt = datetime.datetime.fromisoformat(new_start_time)
            end_dt = start_dt + datetime.timedelta(hours=1) # 默认顺延1小时
            patch_body['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/London'}
            patch_body['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/London'}
        except Exception as e:
            return f"❌ 时间格式错误: {e}"

    try:
        updated = service.events().patch(calendarId='primary', eventId=event_id, body=patch_body).execute()
        return f"✅ 日程已更新: {updated.get('summary')} @ {updated['start'].get('dateTime')[:16]}"
    except Exception as e:
        return f"❌ 更新失败 (ID错误?): {e}"

def delete_schedule_event(event_id):
    """[Delete] 删除日程"""
    service = get_service('calendar', 'v3')
    if not service: return "❌ Calendar Offline"
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return f"✅ 日程 (ID: {event_id}) 已物理删除。"
    except Exception as e:
        return f"❌ 删除失败: {e}"

# --- ✅ Google Tasks 模块 (To-Do) ---

def add_task_tool(title, notes=None):
    """[Create] 添加待办"""
    service = get_service('tasks', 'v1')
    if not service: return "❌ Tasks Offline"
    
    body = {'title': title, 'notes': notes}
    try:
        # @default 表示默认列表
        task = service.tasks().insert(tasklist='@default', body=body).execute()
        return f"✅ 待办已添加: {task['title']}"
    except Exception as e:
        return f"❌ Task 添加失败: {e}"

def list_tasks_tool(max_results=10):
    """[Read] 读取待办"""
    service = get_service('tasks', 'v1')
    if not service: return "❌ Tasks Offline"
    
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=False, maxResults=max_results).execute()
        items = results.get('items', [])
        if not items: return "🎉 No pending tasks!"
        
        report = "📋 **Pending Tasks**:\n"
        for item in items:
            report += f"☐ {item['title']}\n"
        return report
    except Exception as e:
        return f"❌ Task 读取失败: {e}"
    
def fetch_raw_events(hours=24):
    """
    [Spinal Cord Only] 获取未来 N 小时的原始事件数据 (List of Dicts)
    不经过文本处理，供 Python 脚本直接逻辑判断。
    """
    service = get_service('calendar', 'v3')
    if not service: return []
    
    now = datetime.datetime.now().isoformat() + 'Z'
    end = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=end,
            singleEvents=True, orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"Raw Events Fetch Failed: {e}")
        return []