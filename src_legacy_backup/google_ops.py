import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 日志配置
logger = logging.getLogger(__name__)

# 权限范围：我们需要读写日历，读取邮件
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_google_service():
    """
    核心功能：
    1. 检查有没有 token.json (如果有，直接热启动)
    2. 如果没有，弹窗让你登录 Google，生成 token.json (冷启动)
    3. 返回 Calendar 和 Gmail 的操作句柄
    """
    creds = None
    # 1. 检查是否已经登录过
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 2. 如果没登录或 Token 过期，重新走一遍流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Token 刷新失败: {e}")
                creds = None
        
        if not creds:
            # 这里的 credentials.json 必须在你的项目根目录下
            if not os.path.exists('credentials.json'):
                print("❌ 错误：找不到 credentials.json，请把它拖到项目根目录！")
                return None, None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # 这一步会弹窗
            creds = flow.run_local_server(port=0)
            
        # 3. 保存登录状态，下次不用再登了
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # 构建服务
        calendar_service = build('calendar', 'v3', credentials=creds)
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("✅ Google 服务连接成功 (Calendar + Gmail)")
        return calendar_service, gmail_service
    except Exception as e:
        print(f"❌ 连接 Google API 失败: {e}")
        return None, None
    
# --- 在 src/google_ops.py 现有代码的末尾追加 ---

def create_schedule_event(summary, start_time, duration_hours=1, description="Jarvis 自动规划"):
    """
    [Hand]: 在日历上创建一个事件
    :param summary: 事件标题 (e.g. "深度工作：修改简历")
    :param start_time: ISO 格式时间字符串 (e.g. "2026-01-20T10:00:00")
    :param duration_hours: 持续几小时
    """
    calendar_service, _ = get_google_service()
    if not calendar_service:
        return "❌ 无法连接日历服务"

    # 计算结束时间
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    except:
        # 容错：简单的解析
        start_dt = datetime.now() # 仅作示例，实际会由 AI 传准
        
    end_dt = start_dt + timedelta(hours=duration_hours)

    event_body = {
        'summary': f"🤖 {summary}", # 加个机器人图标以示区别
        'description': description,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'Europe/London', # 既然你在英国，锁死伦敦时间
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'Europe/London',
        },
        # 设为 'private' 还是 'public'？默认默认即可
    }

    try:
        event = calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        return f"✅ 已锁定时间块：{summary} ({start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}) | 链接: {event.get('htmlLink')}"
    except Exception as e:
        return f"❌ 创建失败: {e}"

# 单独运行这个文件时的测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("正在唤醒 Google 登录...")
    get_google_service()

