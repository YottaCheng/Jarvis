import json
import os
from datetime import datetime
from config import settings
from utils.logger import setup_logger

logger = setup_logger("Memory")

def _init_memory_file():
    """初始化记忆文件"""
    if not settings.MEMORY_FILE.exists():
        with open(settings.MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def load_history(user_id, limit=10):
    """
    读取最近的 N 条对话
    返回格式: "User: ... \n Jarvis: ..."
    """
    _init_memory_file()
    try:
        with open(settings.MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        history = data.get(user_id, [])
        # 只取最近的 limit 轮
        recent = history[-limit:]
        
        text_block = ""
        for item in recent:
            timestamp = item.get("timestamp", "")[:16]
            text_block += f"[{timestamp}] {item['role']}: {item['content']}\n"
            
        return text_block if text_block else "(No previous conversation)"
    except Exception as e:
        logger.error(f"读取记忆失败: {e}")
        return "(Memory Error)"

def save_history(user_id, role, content):
    """写入一条新记忆"""
    _init_memory_file()
    try:
        # 1. 读
        with open(settings.MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 2. 改
        if user_id not in data:
            data[user_id] = []
            
        new_entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data[user_id].append(new_entry)
        
        # 3. 存 (防止无限膨胀，这里可以加个清理逻辑，暂时先全存)
        with open(settings.MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"写入记忆失败: {e}")