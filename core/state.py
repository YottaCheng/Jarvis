import json
import os
from datetime import datetime
from config import settings
from utils.logger import setup_logger

logger = setup_logger("StateManager")

class StateManager:
    def __init__(self):
        self.state_file = settings.DATA_DIR / "user_state.json"
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.state_file.exists():
            # 初始化默认结构
            default_state = {
                "system_status": {"version": "v2.4"},
                "user_physio": {"energy_level": "UNKNOWN", "last_interaction": ""},
                "strategic_mode": {"current_focus": "NORMAL"}
            }
            self._save(default_state)

    def _load(self):
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"State Load Error: {e}")
            return {}

    def _save(self, data):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"State Save Error: {e}")

    # --- 公开接口 ---

    def get_state(self):
        """获取全量状态"""
        return self._load()

    def update_energy(self, level: str):
        """更新你的电量 (HIGH/MED/LOW)"""
        data = self._load()
        data["user_physio"]["energy_level"] = level.upper()
        data["user_physio"]["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(data)
        logger.info(f"⚡️ Energy Level Updated: {level.upper()}")

    def set_mode(self, mode: str):
        """切换战略模式 (e.g. JOB_HUNTING, DISSERTATION)"""
        data = self._load()
        data["strategic_mode"]["current_focus"] = mode.upper()
        self._save(data)
        logger.info(f"🛡️ Strategic Mode Switched: {mode.upper()}")

    def increment_metric(self, metric_name: str):
        """增加计数器 (完成任务/处理邮件)"""
        data = self._load()
        if "metrics" not in data: data["metrics"] = {}
        
        current = data["metrics"].get(metric_name, 0)
        data["metrics"][metric_name] = current + 1
        self._save(data)