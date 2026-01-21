# utils/formatter.py
import datetime

def format_calendar_events(events: list) -> str:
    """
    将日程原始数据 (List of Dicts) 转换为 LLM/人类可读的字符串
    """
    if not events:
        return "📅 (No events found)"
    
    summary = []
    for e in events:
        # 1. 安全获取时间 (兼容全天事件 date 和普通事件 dateTime)
        start = e['start'].get('dateTime', e['start'].get('date'))
        
        # 2. 格式化时间: 2026-01-20T10:00:00 -> 01-20 10:00
        # 如果是全天事件(2026-01-20)，就保持原样
        clean_start = start[5:16].replace('T', ' ') if len(start) >= 16 else start
        
        title = e.get('summary', 'Untitled')
        e_id = e.get('id', 'N/A')
        
        # 3. 拼装: - [01-20 10:00] Meeting (ID: xxx)
        summary.append(f"- [{clean_start}] {title} (ID: {e_id})")
    
    return "\n".join(summary)

def format_tasks(tasks: list) -> str:
    """
    将 Task 原始列表转换为清单字符串
    """
    if not tasks:
        return "🎉 (No pending tasks)"
    
    lines = ["📋 **Pending Tasks**:"]
    for t in tasks:
        # 状态检查
        status = "✅" if t.get('status') == 'completed' else "☐"
        title = t.get('title', 'Untitled')
        
        # 截止日期 (如果有)
        due = ""
        if t.get('due'):
            # Task 的 due 通常是 '2026-01-20T00:00:00.000Z'
            due = f" [Due: {t.get('due')[:10]}]"
            
        lines.append(f"{status} {title}{due}")
    
    return "\n".join(lines)