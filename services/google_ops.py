# services/google_ops.py
import os.path
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import settings

logger = logging.getLogger("GoogleOps")

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/tasks' 
]

# --- 核心鉴权 ---
def _get_credentials():
    creds = None
    token_path = settings.TOKEN_FILE
    creds_path = settings.CREDENTIALS_FILE
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
        if not creds:
            if not os.path.exists(creds_path): return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_service(api_name, api_version):
    creds = _get_credentials()
    if not creds: return None
    try:
        return build(api_name, api_version, credentials=creds)
    except Exception as e:
        logger.error(f"Service Build Error ({api_name}): {e}")
        return None

# --- 📅 Calendar (Pure Data) ---

def fetch_raw_events(hours=24):
    """[Read] 获取未来 N 小时的原始事件数据 (List of Dicts)"""
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
        logger.error(f"Fetch Events Failed: {e}")
        return []

def search_events_data(query, max_results=5):
    """[Search] 搜索并返回原始数据"""
    service = get_service('calendar', 'v3')
    if not service: return []
    
    try:
        events_result = service.events().list(
            calendarId='primary', q=query, 
            timeMin=(datetime.datetime.now()).isoformat() + 'Z',
            maxResults=max_results, singleEvents=True
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"Search Failed: {e}")
        return []

def create_event_data(summary, start_time, duration_hours=1, description="Jarvis Auto"):
    """[Create] 创建事件并返回该事件对象"""
    service = get_service('calendar', 'v3')
    if not service: return None

    # 简单的时间预处理
    if 'T' not in start_time: start_time = start_time.replace(' ', 'T')
    try:
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = start_dt + datetime.timedelta(hours=duration_hours)
        
        body = {
            'summary': f"🤖 {summary}",
            'description': description,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/London'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/London'},
        }
        return service.events().insert(calendarId='primary', body=body).execute()
    except Exception as e:
        logger.error(f"Create Event Failed: {e}")
        return None

def update_event_data(event_id, patch_body):
    """[Update] 更新事件"""
    service = get_service('calendar', 'v3')
    if not service: return None
    try:
        return service.events().patch(calendarId='primary', eventId=event_id, body=patch_body).execute()
    except Exception as e:
        logger.error(f"Update Event Failed: {e}")
        return None

def delete_event_data(event_id):
    """[Delete] 删除事件"""
    service = get_service('calendar', 'v3')
    if not service: return False
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except: return False

# --- ✅ Tasks (Pure Data) ---

def list_tasks_data(max_results=20):
    """[Read] 返回 Task 原始列表"""
    service = get_service('tasks', 'v1')
    if not service: return []
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=False, maxResults=max_results).execute()
        return results.get('items', [])
    except Exception as e:
        logger.error(f"List Tasks Failed: {e}")
        return []

def add_task_data(title, notes=None):
    """[Create] 创建 Task 并返回对象"""
    service = get_service('tasks', 'v1')
    if not service: return None
    try:
        return service.tasks().insert(tasklist='@default', body={'title': title, 'notes': notes}).execute()
    except Exception: return None